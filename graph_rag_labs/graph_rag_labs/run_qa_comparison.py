from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


QUESTIONS: list[tuple[str, str]] = [
    (
        "Q1",
        "Nghi dinh 46/2023/ND-CP thay the cho nghi dinh nao, va nghi dinh bi thay the do co noi dung gi noi bat ve kinh doanh bao hiem?",
    ),
    (
        "Q2",
        "Van ban hop nhat so 52/VBHN-NHNN duoc hop nhat tu van ban nao, va quy dinh ve ho so, thu tuc cap giay phep lan dau cua ngan hang thuong mai gom nhung tai lieu gi?",
    ),
    (
        "Q3",
        "Thong tu so 01/2025/TT-NHNN quy dinh ve cap giay phep quy tin dung nhan dan duoc sua doi, bo sung boi van ban nao, va nhung noi dung sua doi bo sung chinh la gi?",
    ),
    (
        "Q4",
        "Thong tu so 41/2016/TT-NHNN ve ty le an toan von cua ngan hang can cu vao luat nao, va luat do quy dinh chuc nang nhiem vu cua co quan nao?",
    ),
    (
        "Q5",
        "Hoat dong giao nhan, van chuyen tien mat va tai san quy cua Ngan hang Nha nuoc duoc dieu chinh boi Thong tu nao, va Thong tu do co duoc sua doi bo sung boi van ban nao khong?",
    ),
]


@dataclass
class RunResult:
    question_id: str
    question: str
    hops: int
    answer: str
    direct_chunk_count: int
    hop_document_count: int
    hop_chunk_count: int


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
    for chunk in direct_chunks:
        sections.append(
            "\\n".join(
                [
                    f"document_id: {chunk.get('document_id', '')}",
                    f"chunk_id: {chunk.get('chunk_id', '')}",
                    f"text: {chunk.get('text', '')}",
                ]
            )
        )

    sections.append("\n[HOP_DOCUMENTS]")
    for doc in hop_documents:
        sections.append(
            "\\n".join(
                [
                    f"document_id: {doc.get('document_id', '')}",
                    f"min_hop: {doc.get('min_hop', '')}",
                ]
            )
        )

    sections.append("\n[HOP_CHUNKS]")
    for chunk in hop_chunks:
        sections.append(
            "\\n".join(
                [
                    f"document_id: {chunk.get('document_id', '')}",
                    f"chunk_id: {chunk.get('chunk_id', '')}",
                    f"text: {chunk.get('text', '')}",
                ]
            )
        )
    return "\n".join(sections)


def _build_system_prompt() -> str:
    return """
You are a legal QA assistant for Vietnamese regulatory documents.

Answer policy:
1) Use only facts from the provided context.
2) If context is insufficient, explicitly say: "Khong tim thay thong tin trong ngu canh duoc cung cap."
3) Do not invent document numbers, article content, or legal relations.
4) When possible, cite source evidence as document_id + chunk_id.
""".strip()


def ask_gemini(
    api_key: str,
    model_name: str,
    system_prompt: str,
    user_question: str,
    context_text: str,
    temperature: float,
) -> str:
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency google-generativeai. Install it with: pip install google-generativeai"
        ) from exc

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
        generation_config={"temperature": temperature},
    )
    return response.text or ""


def truncate_text(text: str, max_len: int = 240) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def infer_quality_note(answer: str, hop_chunk_count: int) -> str:
    normalized = answer.lower()
    if "khong tim thay thong tin" in normalized:
        return "Thieu bang chung trong ngu canh"
    if hop_chunk_count == 0:
        return "Chi dua vao ngu canh truc tiep"
    return "Co kha nang tong hop da nguon"


def run_single_question(
    retriever: Any,
    question_id: str,
    question: str,
    hops: int,
    relation_types: list[str],
    top_k: int,
    max_hop_documents: int,
    hop_chunk_limit: int,
    max_direct_chunks: int,
    max_hop_chunks: int,
    api_key: str,
    model_name: str,
    temperature: float,
) -> RunResult:
    retrieval_result = retriever.search_context(
        question=question,
        top_k=top_k,
        hops=hops,
        relation_types=relation_types,
        max_hop_documents=max_hop_documents,
        hop_chunk_limit=hop_chunk_limit,
    )

    context_text = _build_context_text(
        retrieval_result=retrieval_result,
        max_direct_chunks=max_direct_chunks,
        max_hop_chunks=max_hop_chunks,
    )

    answer = ask_gemini(
        api_key=api_key,
        model_name=model_name,
        system_prompt=_build_system_prompt(),
        user_question=question,
        context_text=context_text,
        temperature=temperature,
    )

    return RunResult(
        question_id=question_id,
        question=question,
        hops=hops,
        answer=answer.strip(),
        direct_chunk_count=len(retrieval_result.get("direct_chunks", [])),
        hop_document_count=len(retrieval_result.get("hop_documents", [])),
        hop_chunk_count=len(retrieval_result.get("hop_chunks", [])),
    )


def build_markdown_report(results: list[RunResult], relation_types: list[str], top_k: int) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    by_question: dict[str, list[RunResult]] = {}
    for item in results:
        by_question.setdefault(item.question_id, []).append(item)

    lines: list[str] = []
    lines.append("# QA Comparison Report (Multi-hop Graph RAG)")
    lines.append("")
    lines.append(f"- Generated at: {timestamp}")
    lines.append(f"- Top-k: {top_k}")
    lines.append(f"- Relation filters: {', '.join(relation_types) if relation_types else 'ALL'}")
    lines.append("- Hop settings compared: 0, 1, 2")
    lines.append("")

    for qid, question in QUESTIONS:
        lines.append(f"## {qid}")
        lines.append("")
        lines.append(f"**Question**: {question}")
        lines.append("")
        lines.append("| Hops | Direct chunks | Hop documents | Hop chunks | Quick assessment | Answer summary |")
        lines.append("|---|---:|---:|---:|---|---|")

        for item in sorted(by_question.get(qid, []), key=lambda x: x.hops):
            assessment = infer_quality_note(item.answer, item.hop_chunk_count)
            summary = truncate_text(item.answer.replace("\n", " "), max_len=180)
            lines.append(
                f"| {item.hops} | {item.direct_chunk_count} | {item.hop_document_count} | {item.hop_chunk_count} | {assessment} | {summary} |"
            )

        lines.append("")
        lines.append("### Full answers")
        lines.append("")
        for item in sorted(by_question.get(qid, []), key=lambda x: x.hops):
            lines.append(f"#### Hops = {item.hops}")
            lines.append("")
            lines.append(item.answer or "(empty answer)")
            lines.append("")

    lines.append("## Overall Notes")
    lines.append("")
    lines.append("- Compare whether hops=1/2 improves evidence breadth versus hops=0.")
    lines.append("- Check if answers become more complete for cross-document legal relation questions.")
    lines.append("- Keep answers grounded: prefer responses with explicit document/chunk evidence.")
    lines.append("")

    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run QA comparison for hops 0/1/2 and export Markdown report.")
    parser.add_argument("--output", default="qa_comparison.md", help="Markdown report output path.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--relation-types", default="CAN_CU,THAY_THE,HOP_NHAT")
    parser.add_argument("--max-hop-documents", type=int, default=20)
    parser.add_argument("--hop-chunk-limit", type=int, default=2)
    parser.add_argument("--max-direct-chunks", type=int, default=6)
    parser.add_argument("--max-hop-chunks", type=int, default=10)
    parser.add_argument("--model", default="gemini-flash-latest")
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument(
        "--save-json-dir",
        default="qa_run_artifacts",
        help="Directory to store per-run JSON payloads.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate empty comparison template without calling retrieval/LLM.",
    )
    return parser


def write_dry_run_template(output_path: Path) -> None:
    lines = [
        "# QA Comparison Report (Multi-hop Graph RAG)",
        "",
        "- Mode: dry-run template",
        "- Fill this file after running real experiments.",
        "",
    ]
    for qid, question in QUESTIONS:
        lines.append(f"## {qid}")
        lines.append("")
        lines.append(f"**Question**: {question}")
        lines.append("")
        lines.append("| Hops | Direct chunks | Hop documents | Hop chunks | Quick assessment | Answer summary |")
        lines.append("|---|---:|---:|---:|---|---|")
        lines.append("| 0 |  |  |  |  |  |")
        lines.append("| 1 |  |  |  |  |  |")
        lines.append("| 2 |  |  |  |  |  |")
        lines.append("")
        lines.append("### Full answers")
        lines.append("")
        lines.append("#### Hops = 0")
        lines.append("")
        lines.append("(pending)")
        lines.append("")
        lines.append("#### Hops = 1")
        lines.append("")
        lines.append("(pending)")
        lines.append("")
        lines.append("#### Hops = 2")
        lines.append("")
        lines.append("(pending)")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = build_arg_parser().parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        write_dry_run_template(output_path)
        print(f"Wrote dry-run template: {output_path}")
        return

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable.")

    relation_types = [part.strip() for part in args.relation_types.split(",") if part.strip()]

    # Import retrieval dependency only when running real experiments.
    from multi_hop_retrieval import MultiHopRetriever

    save_json_dir = Path(args.save_json_dir).resolve()
    save_json_dir.mkdir(parents=True, exist_ok=True)

    results: list[RunResult] = []
    retriever = MultiHopRetriever()
    try:
        for qid, question in QUESTIONS:
            for hops in [0, 1, 2]:
                print(f"Running {qid} with hops={hops}...")
                try:
                    result = run_single_question(
                        retriever=retriever,
                        question_id=qid,
                        question=question,
                        hops=hops,
                        relation_types=relation_types,
                        top_k=args.top_k,
                        max_hop_documents=args.max_hop_documents,
                        hop_chunk_limit=args.hop_chunk_limit,
                        max_direct_chunks=args.max_direct_chunks,
                        max_hop_chunks=args.max_hop_chunks,
                        api_key=api_key,
                        model_name=args.model,
                        temperature=args.temperature,
                    )
                except Exception as exc:
                    result = RunResult(
                        question_id=qid,
                        question=question,
                        hops=hops,
                        answer=f"[ERROR] {type(exc).__name__}: {exc}",
                        direct_chunk_count=0,
                        hop_document_count=0,
                        hop_chunk_count=0,
                    )
                results.append(result)

                artifact_path = save_json_dir / f"{qid}_hops_{hops}.json"
                artifact_payload: dict[str, Any] = {
                    "question_id": qid,
                    "question": question,
                    "hops": hops,
                    "answer": result.answer,
                    "stats": {
                        "direct_chunk_count": result.direct_chunk_count,
                        "hop_document_count": result.hop_document_count,
                        "hop_chunk_count": result.hop_chunk_count,
                    },
                }
                artifact_path.write_text(
                    json.dumps(artifact_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
    finally:
        retriever.close()

    markdown = build_markdown_report(
        results=results,
        relation_types=relation_types,
        top_k=args.top_k,
    )
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote report: {output_path}")


if __name__ == "__main__":
    main()
