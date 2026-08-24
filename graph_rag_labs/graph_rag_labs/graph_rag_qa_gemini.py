from __future__ import annotations

import argparse
import json
import os
from typing import Any

from multi_hop_retrieval import MultiHopRetriever, parse_relation_types


def _require_gemini_sdk():
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency google-generativeai. Install it with: pip install google-generativeai"
        ) from exc
    return genai


def _build_context_text(
    retrieval_result: dict[str, Any],
    max_direct_chunks: int,
    max_hop_chunks: int,
) -> str:
    direct_chunks = retrieval_result.get("direct_chunks", [])[:max_direct_chunks]
    hop_chunks = retrieval_result.get("hop_chunks", [])[:max_hop_chunks]
    hop_documents = retrieval_result.get("hop_documents", [])

    sections: list[str] = []

    sections.append("[DIRECT_CHUNKS]")
    if not direct_chunks:
        sections.append("- No direct chunks retrieved.")
    else:
        for idx, chunk in enumerate(direct_chunks, start=1):
            sections.append(
                "\\n".join(
                    [
                        f"- Direct {idx}",
                        f"  document_id: {chunk.get('document_id', '')}",
                        f"  document_title: {chunk.get('document_title', '')}",
                        f"  chunk_id: {chunk.get('chunk_id', '')}",
                        f"  chunk_type: {chunk.get('chunk_type', '')}",
                        f"  chunk_title: {chunk.get('chunk_title', '')}",
                        f"  score: {chunk.get('score', 0.0):.6f}",
                        f"  text: {chunk.get('text', '')}",
                    ]
                )
            )

    sections.append("\n[HOP_DOCUMENTS]")
    if not hop_documents:
        sections.append("- No expanded documents.")
    else:
        for idx, doc in enumerate(hop_documents, start=1):
            sections.append(
                "\\n".join(
                    [
                        f"- HopDoc {idx}",
                        f"  document_id: {doc.get('document_id', '')}",
                        f"  document_title: {doc.get('document_title', '')}",
                        f"  min_hop: {doc.get('min_hop', '')}",
                    ]
                )
            )

    sections.append("\n[HOP_CHUNKS]")
    if not hop_chunks:
        sections.append("- No hop chunks retrieved.")
    else:
        for idx, chunk in enumerate(hop_chunks, start=1):
            sections.append(
                "\\n".join(
                    [
                        f"- HopChunk {idx}",
                        f"  document_id: {chunk.get('document_id', '')}",
                        f"  document_title: {chunk.get('document_title', '')}",
                        f"  chunk_id: {chunk.get('chunk_id', '')}",
                        f"  chunk_type: {chunk.get('chunk_type', '')}",
                        f"  chunk_title: {chunk.get('chunk_title', '')}",
                        f"  text: {chunk.get('text', '')}",
                    ]
                )
            )

    return "\n".join(sections)


def _build_system_prompt(
    response_style: str = "Ngắn gọn",
    include_citations: bool = True,
    max_answer_chars: int = 800,
) -> str:
    style_rule = {
        "Ngắn gọn": "Trả lời ngắn gọn, chỉ nêu ý chính và kết luận rõ ràng.",
        "Chi tiết": "Trả lời đầy đủ, có giải thích ngắn gọn từng bước và logic pháp lý.",
        "Theo định dạng luật": "Trả lời theo kiểu pháp lý: mô tả vụ việc, căn cứ pháp lý, kết luận ngắn gọn.",
    }.get(response_style, "Trả lời ngắn gọn, rõ ràng và thực dụng.")

    citation_rule = (
        "- Bao gồm phần 'Bang chung' với các trích dẫn nguồn dưới dạng '- document_id / chunk_id: trích dẫn ngắn'."
        if include_citations
        else "- Không cần liệt kê nguồn trong phần trả lời; chỉ trả lời trực tiếp và rõ ràng."
    )

    return f"""
You are a legal QA assistant for Vietnamese regulatory documents.

Answer policy:
1) Use only facts from the provided context.
2) If context is insufficient, explicitly say: "Khong tim thay thong tin trong ngu canh duoc cung cap."
3) Do not invent document numbers, article content, or legal relations.
4) When possible, cite source evidence as document_id + chunk_id.
5) Keep the final answer in Vietnamese.

Response style:
- {style_rule}
- Target length: about {max_answer_chars} characters.
- Use concise language and avoid repetition.
{citation_rule}

Graph schema (Neo4j):
- Node :Document {{id, title, source, metadata}}
- Node :Chunk {{id, type, title, text, embedding, embedding_dim}}
- Edge (:Chunk)-[:PART_OF]->(:Document)
- Edge (:Chunk)-[:PARENT_OF]->(:Chunk)
- Edge (:Chunk)-[:NEXT]->(:Chunk)
- Edge (:Document)-[:RELATIONSHIP {{type, description}}]->(:Document)

Vietnamese legal text structure notes:
- Hierarchy often follows Chuong -> Muc -> Dieu -> Khoan.
- A question may require combining direct chunk evidence and multi-hop related documents.

Output format:
- Include 2 sections:
  A) "Tra loi"
  B) "Bang chung" as bullet lines: "- document_id / chunk_id: trich dan ngan"
- Keep the answer focused on the question and avoid long generic introductions.
""".strip()


def ask_gemini(
    api_key: str,
    model_name: str,
    system_prompt: str,
    user_question: str,
    context_text: str,
    temperature: float,
    response_style: str = "Ngắn gọn",
    include_citations: bool = True,
    max_answer_chars: int = 800,
) -> str:
    genai = _require_gemini_sdk()
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(model_name=model_name)

    prompt = (
        "Question:\n"
        f"{user_question}\n\n"
        "Retrieved context:\n"
        f"{context_text}\n"
    )

    response = model.generate_content(
        [
            {"role": "user", "parts": [system_prompt]},
            {"role": "user", "parts": [prompt]},
        ],
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max(256, min(max_answer_chars * 2, 4096)),
        },
    )

    return response.text or ""


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Graph RAG QA with multi-hop Neo4j context + Gemini.")
    parser.add_argument("--question", required=True, help="Question to answer.")
    parser.add_argument("--k", type=int, default=5, help="Top-k direct chunks.")
    parser.add_argument("--hops", type=int, default=1, help="Max multi-hop depth.")
    parser.add_argument(
        "--relation-types",
        default="CAN_CU,THAY_THE,HOP_NHAT",
        help="Comma-separated RELATIONSHIP.type filters.",
    )
    parser.add_argument("--max-hop-documents", type=int, default=20)
    parser.add_argument("--hop-chunk-limit", type=int, default=2)
    parser.add_argument("--max-direct-chunks", type=int, default=6)
    parser.add_argument("--max-hop-chunks", type=int, default=10)
    parser.add_argument("--model", default="gemini-flash-latest")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument(
        "--answer-style",
        choices=["Ngắn gọn", "Chi tiết", "Theo định dạng luật"],
        default="Ngắn gọn",
        help="Controls the final answer style.",
    )
    parser.add_argument(
        "--include-citations",
        action="store_true",
        default=True,
        help="Include source evidence in the final answer.",
    )
    parser.add_argument(
        "--max-answer-chars",
        type=int,
        default=800,
        help="Target max length for final answer in characters.",
    )
    parser.add_argument(
        "--save-debug-json",
        default="",
        help="Optional output file path to save retrieval result JSON.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable.")

    relation_types = parse_relation_types(args.relation_types)

    retriever = MultiHopRetriever()
    try:
        retrieval_result = retriever.search_context(
            question=args.question,
            top_k=args.k,
            hops=args.hops,
            relation_types=relation_types,
            max_hop_documents=args.max_hop_documents,
            hop_chunk_limit=args.hop_chunk_limit,
        )
    finally:
        retriever.close()

    if args.save_debug_json:
        with open(args.save_debug_json, "w", encoding="utf-8") as file_obj:
            json.dump(retrieval_result, file_obj, ensure_ascii=False, indent=2)

    system_prompt = _build_system_prompt(
        response_style=args.answer_style,
        include_citations=args.include_citations,
        max_answer_chars=args.max_answer_chars,
    )
    context_text = _build_context_text(
        retrieval_result=retrieval_result,
        max_direct_chunks=args.max_direct_chunks,
        max_hop_chunks=args.max_hop_chunks,
    )

    answer = ask_gemini(
        api_key=api_key,
        model_name=args.model,
        system_prompt=system_prompt,
        user_question=args.question,
        context_text=context_text,
        temperature=args.temperature,
        response_style=args.answer_style,
        include_citations=args.include_citations,
        max_answer_chars=args.max_answer_chars,
    )

    print("=== QUESTION ===")
    print(args.question)
    print("\n=== RETRIEVAL PARAMS ===")
    print(
        json.dumps(
            retrieval_result.get("params", {}),
            ensure_ascii=False,
            indent=2,
        )
    )
    print("\n=== ANSWER ===")
    print(answer)


if __name__ == "__main__":
    main()
