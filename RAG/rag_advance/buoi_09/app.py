"""Streamlit UI for Buổi 09: Multi-query and Parent–Child Retrieval."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag_advance.buoi_09.hierarchical_rag import (
    compare_modes,
    hierarchy_status,
    load_runtime_config,
    run_query_pipeline,
)

APP_DIR = Path(__file__).resolve().parent
REPORT_DIR = APP_DIR / "reports"

STATUS_HINTS: dict[str, str] = {
    "ready": "Sẵn sàng. Kết quả đã sẵn sàng để xem.",
    "hierarchy_not_ready": "Hierarchy chưa sẵn sàng. Kiểm tra build store hoặc manifest.",
    "collection_not_ready": "Collection chưa sẵn sàng. Kiểm tra trạng thái semantic index.",
    "query_generation_unavailable": "Không thể sinh query mở rộng. Kiểm tra cấu hình hoặc API key.",
    "multi_query_partial": "Multi-query partial: Q0 thành công nhưng query phụ lỗi.",
    "reranker_unavailable": "Reranker không sẵn sàng. Kiểm tra model hoặc cấu hình.",
    "insufficient_evidence": "Không đủ evidence để sinh câu trả lời. Xem lại parent candidates.",
    "generation_error": "Lỗi tạo câu trả lời. Kiểm tra cấu hình Gemini hoặc payload.",
}


def load_latest_report(report_dir: Path | str | None = None) -> dict[str, Any] | None:
    directory = Path(report_dir or REPORT_DIR)
    latest = directory / "latest_report.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return None


def format_citation(citation: dict[str, Any]) -> str:
    label = citation.get("evidence_id", "[P?]")
    parent_id = citation.get("parent_id", "?")
    anchor_child_id = citation.get("anchor_child_id", "?")
    source = citation.get("source", "?")
    page_start = citation.get("page_start", "?")
    page_end = citation.get("page_end", "?")
    structural_path = citation.get("structural_path", {})
    path = "/".join(str(structural_path.get(key, "")) for key in ("chapter", "article", "clause", "point") if structural_path.get(key))
    warnings = citation.get("warnings", []) or []
    warning_text = f" (warnings: {', '.join(warnings)})" if warnings else ""
    return f"{label}: parent={parent_id}, anchor_child={anchor_child_id}, source={source}, pages={page_start}-{page_end}, path={path}{warning_text}"


def status_action_hint(status: str) -> str:
    return STATUS_HINTS.get(status, "Trạng thái chưa rõ. Kiểm tra lỗi và cấu hình.")


def build_query_cards(query_set: dict[str, Any], merged_children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queries = query_set.get("queries", []) if isinstance(query_set, dict) else []
    cards: list[dict[str, Any]] = []
    for query in queries:
        query_id = query.get("query_id", "")
        matched = [child for child in merged_children if query_id in child.get("per_query_ranks", {})]
        rank_values = [child["per_query_ranks"][query_id] for child in matched if query_id in child.get("per_query_ranks", {})]
        cards.append(
            {
                "query_id": query_id,
                "text": query.get("text", ""),
                "origin": query.get("origin", ""),
                "focus": query.get("focus", ""),
                "result_count": len(matched),
                "best_rank": min(rank_values) if rank_values else None,
                "is_original": query.get("origin") == "original",
            }
        )
    return cards


def build_query_child_matrix(query_set: dict[str, Any], merged_children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queries = query_set.get("queries", []) if isinstance(query_set, dict) else []
    query_ids = [query.get("query_id", "") for query in queries]
    matrix: list[dict[str, Any]] = []
    for child in merged_children:
        row = {
            "child_id": child.get("child_id", ""),
            "text": child.get("text", ""),
            "source": child.get("source", ""),
            "page_start": child.get("page_start", ""),
            "page_end": child.get("page_end", ""),
            "multi_query_rrf_score": child.get("multi_query_rrf_score"),
            "support_query_count": child.get("support_query_count", 0),
            "support_query_ids": child.get("support_query_ids", []),
            "per_query_ranks": child.get("per_query_ranks", {}),
        }
        row.update({f"rank_{qid}": row["per_query_ranks"].get(qid, "—") for qid in query_ids})
        matrix.append(row)
    return matrix


def build_parent_tree_nodes(parent_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for candidate in parent_candidates:
        nodes.append(
            {
                "parent_id": candidate.get("parent_id", ""),
                "source": candidate.get("source", ""),
                "page_start": candidate.get("page_start", ""),
                "page_end": candidate.get("page_end", ""),
                "parent_rank": candidate.get("parent_rank"),
                "parent_rerank_rank": candidate.get("parent_rerank_rank"),
                "parent_rrf_score": candidate.get("parent_rrf_score"),
                "parent_rerank_score": candidate.get("parent_rerank_score"),
                "anchor_child_id": candidate.get("anchor_child_id", ""),
                "scoring_child_ids": candidate.get("scoring_child_ids", []),
                "supporting_child_ids": candidate.get("supporting_child_ids", []),
                "support_query_ids": candidate.get("support_query_ids", []),
                "structural_path": candidate.get("structural_path", {}),
                "warnings": candidate.get("warnings", []),
                "ambiguous": candidate.get("ambiguous", False),
                "text": candidate.get("text", ""),
            }
        )
    return nodes


def render_query_child_matrix_html(query_set: dict[str, Any], merged_children: list[dict[str, Any]]) -> str:
    queries = query_set.get("queries", []) if isinstance(query_set, dict) else []
    query_ids = [query.get("query_id", "") for query in queries]
    matrix = build_query_child_matrix(query_set, merged_children)
    if not matrix:
        return ""

    header_cells = ["Child ID", "Source", "Pages", "Support", "MQ-RRF"] + query_ids
    rows_html = []
    for row in matrix:
        cells = [
            f"<td><strong>{row.get('child_id', '')}</strong><br><span class='monospace'>{row.get('source', '')}</span></td>",
            f"<td>{row.get('source', '')}</td>",
            f"<td>{row.get('page_start', '')}–{row.get('page_end', '')}</td>",
            f"<td>{row.get('support_query_count', 0)}</td>",
            f"<td>{row.get('multi_query_rrf_score', 0.0):.4f}</td>",
        ]
        for qid in query_ids:
            rank = row.get("per_query_ranks", {}).get(qid, "—")
            classes = "matrix-rank" if isinstance(rank, int) or (isinstance(rank, str) and rank != "—") else "matrix-empty"
            cells.append(f"<td class='{classes}'>{rank}</td>")
        rows_html.append(f"<tr>{''.join(cells)}</tr>")

    header_html = ''.join(f"<th>{col}</th>" for col in header_cells)
    return f"<table class='matrix-table'><thead><tr>{header_html}</tr></thead><tbody>{''.join(rows_html)}</tbody></table>"


def render_parent_tree_html(parents: list[dict[str, Any]]) -> str:
    html_parts = ["<div class='parent-tree'>"]
    for parent in parents:
        warnings = parent.get("warnings", []) or []
        warning_html = ""
        if warnings:
            warning_html = f"<div class='warning-box'><strong>Warnings:</strong> {', '.join(warnings)}</div>"

        support_ids = ', '.join(parent.get("supporting_child_ids", []))
        query_ids = ', '.join(parent.get("support_query_ids", []))
        html_parts.append(
            "<div class='parent-card'>"
            f"<div class='parent-header'><span class='parent-pill'>Parent {parent.get('parent_id', '')}</span>"
            f"<span class='parent-pill'>rank {parent.get('parent_rank', '')} → rerank {parent.get('parent_rerank_rank', '')}</span>"
            f"<span class='parent-pill'>score {parent.get('parent_rrf_score', ''):.4f} → {parent.get('parent_rerank_score', ''):.4f}</span></div>"
            f"<div class='parent-row'><strong>Source:</strong> {parent.get('source', '')} &nbsp; <strong>Pages:</strong> {parent.get('page_start', '')}-{parent.get('page_end', '')}</div>"
            f"<div class='parent-row'><strong>Path:</strong> {parent.get('structural_path', {})}</div>"
            f"<div class='parent-row'><strong>Anchor child:</strong> {parent.get('anchor_child_id', '')} &nbsp; <strong>Queries:</strong> {query_ids}</div>"
            f"<div class='parent-row'><strong>Supporting children:</strong> {support_ids}</div>"
            f"<div class='parent-row'><strong>Text snippet:</strong> {parent.get('text', '')[:280]}{'...' if len(parent.get('text', '')) > 280 else ''}</div>"
            f"{warning_html}"
            "</div>"
        )
    html_parts.append("</div>")
    return ''.join(html_parts)


def build_mode_comparison_rows(compare_result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mode_results = compare_result.get("mode_results", {})
    for mode, mode_result in mode_results.items():
        child_hits = mode_result.get("child_hits", []) or []
        parent_candidates = mode_result.get("parent_candidates", []) or []
        accepted_evidence = mode_result.get("accepted_evidence", []) or []
        if mode.endswith("_parent"):
            unit_type = "parent"
            evidence_ids = [item.get("parent_id") for item in accepted_evidence if item.get("parent_id")]
            rank_field = "parent_rank"
            sources = {item.get("source") for item in parent_candidates if item.get("source")}
            unique_articles = {item.get("structural_path", {}).get("article") for item in parent_candidates if item.get("structural_path", {}).get("article")}
            expanded_parents = len(parent_candidates)
            context_chars = mode_result.get("trace", {}).get("expanded_parent_chars", 0)
            expansion_factor = mode_result.get("trace", {}).get("context_expansion_factor", 0.0)
        else:
            unit_type = "child"
            evidence_ids = [item.get("child_id") for item in child_hits if item.get("child_id")]
            rank_field = "multi_query_rank"
            sources = {item.get("source") for item in child_hits if item.get("source")}
            unique_articles = set()
            expanded_parents = 0
            context_chars = 0
            expansion_factor = 0.0

        rows.append(
            {
                "mode": mode,
                "status": mode_result.get("status", ""),
                "evidence_ids": evidence_ids,
                "unit_type": unit_type,
                "rank_field": rank_field,
                "source_count": len(sources),
                "unique_article_count": len([a for a in unique_articles if a]),
                "child_count": len(child_hits),
                "parent_count": len(parent_candidates),
                "expanded_parent_count": expanded_parents,
                "context_chars": context_chars,
                "expansion_factor": expansion_factor,
                "generation_calls": mode_result.get("trace", {}).get("generation_api_call_count", 0),
                "answer_calls": mode_result.get("trace", {}).get("answer_generation_call_count", 0),
                "reranker_calls": mode_result.get("trace", {}).get("reranker_call_count", 0),
                "errors": mode_result.get("errors", []),
            }
        )
    return rows


def _safe_load_runtime_config() -> tuple[dict[str, Any] | None, str | None]:
    try:
        return load_runtime_config(), None
    except Exception as exc:
        return None, str(exc)


def _safe_hierarchy_status(input_path: str | None = None, output_dir: str | None = None) -> dict[str, Any]:
    try:
        return hierarchy_status(output_dir)
    except Exception as exc:
        return {"status": "hierarchy_not_ready", "error": str(exc)}


def _load_hierarchical_chunks(strategy: str = "hierarchical") -> list[dict[str, Any]]:
    try:
        from rag_advance.buoi_09.rag import load_chunks
    except ImportError as exc:
        raise RuntimeError("Unable to import hierarchical chunk loader") from exc

    payload = load_chunks(None, strategy=strategy)
    if not isinstance(payload, dict):
        raise RuntimeError("Hierarchical chunks payload is invalid")
    return payload.get("chunks", []) or []


def _default_hybrid_retriever(query_text: str, config: dict[str, Any], query_id: str, strategy: str = "hierarchical") -> list[dict[str, Any]]:
    try:
        from rag_advance.buoi_08.advanced_rag import hybrid_search, search_bm25
    except ImportError as exc:
        raise RuntimeError("Unable to import advanced retrieval implementation") from exc

    chunks = _load_hierarchical_chunks(strategy=strategy)
    candidate_k = int(config.get("PER_QUERY_CANDIDATES", 12))
    try:
        hybrid_result = hybrid_search(
            question=query_text,
            candidate_k=candidate_k,
            strategy=strategy,
            chunks=chunks,
            config={**config, "bm25_candidates": candidate_k, "semantic_candidates": candidate_k, "rrf_k": int(config.get("MULTI_QUERY_RRF_K", 60))},
        )
        hits = []
        for item in hybrid_result.get("results", []):
            hits.append(
                {
                    "child_id": item.get("chunk_id", ""),
                    "text": item.get("text", ""),
                    "source": item.get("source", ""),
                    "page_start": item.get("page_start"),
                    "page_end": item.get("page_end"),
                    "inner_rrf_rank": int(item.get("fused_rank", 0) or 0),
                }
            )
        if hits:
            return hits
    except Exception:
        pass

    bm25_results = search_bm25(query_text, chunks, candidate_k=candidate_k)
    hits = []
    for item in bm25_results:
        hits.append(
            {
                "child_id": item.get("chunk_id", ""),
                "text": item.get("text", ""),
                "source": item.get("source", ""),
                "page_start": item.get("page_start"),
                "page_end": item.get("page_end"),
                "inner_rrf_rank": int(item.get("bm25_rank", 0) or 0),
            }
        )
    return hits


def _default_answer_generator(question: str, accepted_parents: list[dict[str, Any]], config: dict[str, Any], model_name: str) -> dict[str, Any]:
    try:
        from google import genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError("google.genai is not installed; install it to enable answer generation") from exc

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    if not model_name:
        raise RuntimeError("GEMINI_GENERATION_MODEL is not configured")

    prompt_lines = [
        f"Câu hỏi: {question}",
        "Dựa trên bằng chứng sau, hãy trả lời ngắn gọn và chỉ dùng thông tin đó:",
    ]
    for index, parent in enumerate(accepted_parents, start=1):
        prompt_lines.append(
            f"[P{index}] Parent ID: {parent.get('parent_id')} | Source: {parent.get('source')} | Pages: {parent.get('page_start')}-{parent.get('page_end')} | Text: {parent.get('text')}"
        )
    prompt_lines.append("Chỉ trả lời từ bằng chứng và không thêm thông tin ngoài phạm vi.")
    prompt = "\n\n".join(prompt_lines)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "temperature": float(config.get("MULTI_QUERY_TEMPERATURE", 0.2)),
            "response_mime_type": "application/json",
        },
    )

    if not hasattr(response, "text"):
        raise RuntimeError("Gemini returned no text payload")
    payload = json.loads(response.text)
    if not isinstance(payload, dict) or "answer" not in payload or "citations" not in payload:
        raise RuntimeError("Answer generator returned invalid payload")
    return {"answer": str(payload.get("answer", "")), "citations": payload.get("citations", [])}


def main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="RAG Foundation — Buổi 09",
        page_icon="🧠",
        layout="wide",
    )

    st.markdown(
        """
        <style>
        .card {
            border: 1px solid #dfe1e5;
            border-radius: 18px;
            padding: 18px;
            background: #ffffff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            margin-bottom: 16px;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.85rem;
            background: #f5f5f5;
            color: #333333;
            margin-right: 6px;
        }
        .badge-original { background: #e8f0fe; color: #1967d2; }
        .badge-generated { background: #fff4e5; color: #d97706; }
        .status-box { padding: 16px; border-radius: 14px; background: #f8fafc; }
        .monospace { font-family: monospace; }
        .matrix-table { border-collapse: collapse; width: 100%; margin-bottom: 16px; }
        .matrix-table th, .matrix-table td { border: 1px solid #e2e8f0; padding: 8px 10px; text-align: left; }
        .matrix-table th { background: #f8fbff; color: #111827; }
        .matrix-table tr:nth-child(even) { background: #fbfcfe; }
        .matrix-rank { font-weight: 700; color: #0f172a; }
        .matrix-empty { color: #94a3b8; }
        .parent-card { border: 1px solid #d1d5db; border-radius: 16px; padding: 18px; margin-bottom: 18px; background: #ffffff; }
        .parent-header { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 10px; }
        .parent-pill { padding: 4px 10px; border-radius: 999px; font-size: 0.82rem; background: #eef2ff; color: #4338ca; }
        .parent-row { margin-bottom: 8px; }
        .child-list { margin-top: 12px; padding-left: 18px; }
        .child-item { margin-bottom: 6px; }
        .child-item span { display: inline-block; margin-right: 10px; }
        .warning-box { background: #fff1f2; border: 1px solid #fecdd3; padding: 12px; border-radius: 14px; margin-top: 10px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("RAG Foundation — Buổi 09")
    st.markdown("**Query fan-out → Hybrid per query → Cross-query RRF → Parent expansion → Parent rerank**")

    with st.sidebar:
        st.header("Điều khiển")
        mode = st.selectbox("Chọn mode", ["single_flat", "multi_flat", "single_parent", "multi_parent"], index=3)

        if "last_result" not in st.session_state:
            st.session_state["last_result"] = None
        if "last_compare" not in st.session_state:
            st.session_state["last_compare"] = None

        st.markdown("---")
        st.subheader("Chạy thử")
        question = st.text_area("Câu hỏi", value="", height=140)
        run_col1, run_col2 = st.columns([1, 1])
        with run_col1:
            if st.button("Chạy query") and question.strip():
                st.session_state["run_now"] = "query"
        with run_col2:
            if st.button("So sánh 4 mode") and question.strip():
                st.session_state["run_now"] = "compare"

        st.markdown("---")
        st.subheader("Gemini & Reranker")
        reranker_model = os.getenv("RERANKER_MODEL", "").strip()
        st.write("GEMINI_KEY:", "✅ configured" if os.getenv("GEMINI_API_KEY") else "❌ missing")
        st.write("Generation model:", os.getenv("GEMINI_GENERATION_MODEL", "<unset>"))
        st.write("Reranker model:", reranker_model or "<unset>")
        if not reranker_model:
            st.warning("Parent mode sẽ trả reranker_unavailable nếu RERANKER_MODEL chưa cấu hình.")

        st.markdown("---")
        st.subheader("Hierarchy store")
        store_dir = os.getenv("HIERARCHY_STORE_DIR", str(APP_DIR / "storage" / "hierarchy"))
        hierarchy_state = _safe_hierarchy_status(None, store_dir)
        st.write("Status:", hierarchy_state.get("status"))
        st.write("Children:", hierarchy_state.get("child_count"))
        st.write("Parents:", hierarchy_state.get("parent_count"))
        st.write("Ambiguous:", hierarchy_state.get("ambiguous_child_count"))
        if hierarchy_state.get("status") != "ready":
            st.error(hierarchy_state.get("error", "Hierarchy chưa sẵn sàng."))

        st.markdown("---")
        st.subheader("Cấu hình runtime")
        config, config_error = _safe_load_runtime_config()
        if config_error:
            st.error(f"Cấu hình runtime không hợp lệ: {config_error}")
            config = {}
        else:
            st.write("MULTI_QUERY_COUNT:", config.get("MULTI_QUERY_COUNT"))
            st.write("PER_QUERY_CANDIDATES:", config.get("PER_QUERY_CANDIDATES"))
            st.write("PARENT_CANDIDATES:", config.get("PARENT_CANDIDATES"))
            st.write("FINAL_PARENT_TOP_K:", config.get("FINAL_PARENT_TOP_K"))
            st.write("TOTAL_CONTEXT_MAX_CHARS:", config.get("TOTAL_CONTEXT_MAX_CHARS"))

        st.markdown("---")
        st.caption("Nhập câu hỏi phía trên rồi nhấn một trong hai nút. UI này giữ kết quả lần chạy gần nhất trong session.")

    action = st.session_state.get("run_now")
    result = st.session_state.get("last_result")
    compare_result = st.session_state.get("last_compare")

    if action == "query" and question.strip():
        query_result = run_query_pipeline(
            question,
            mode,
            config=config,
            input_path=None,
            store_dir=store_dir,
            query_generator_fn=None,
            hybrid_retriever_fn=_default_hybrid_retriever,
            reranker_fn=None,
            answer_generator_fn=_default_answer_generator,
        )
        st.session_state["last_result"] = query_result
        result = query_result
        st.session_state["run_now"] = None

    if action == "compare" and question.strip():
        compare_result = compare_modes(
            question,
            config=config,
            input_path=None,
            store_dir=store_dir,
            query_generator_fn=None,
            hybrid_retriever_fn=_default_hybrid_retriever,
            reranker_fn=None,
        )
        st.session_state["last_compare"] = compare_result
        st.session_state["run_now"] = None

    if question.strip() and result is None and compare_result is None:
        st.info("Nhập câu hỏi và nhấn 'Chạy query' hoặc 'So sánh 4 mode' trong thanh bên.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Ask Advanced RAG",
        "Query Fan-out",
        "Parent–Child Explorer",
        "Mode Comparison",
        "Evaluation",
    ])

    with tab1:
        st.subheader("Ask Advanced RAG")
        if result is None:
            st.info("Chưa có kết quả query. Vui lòng chạy query trước.")
        else:
            status = result.get("status", "")
            status_text = status_action_hint(status)
            trace = result.get("trace", {}) or {}
            answer = result.get("answer", "")
            citations = result.get("citations", []) or []
            accepted = result.get("accepted_evidence", []) or []

            st.markdown(f"<div class='status-box'><strong>Mode:</strong> {result.get('mode', '')} &nbsp;&nbsp; <strong>Status:</strong> {status} <br>{status_text}</div>", unsafe_allow_html=True)
            if result.get("errors"):
                st.error(result.get("errors"))

            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            metrics_col1.metric("Generation calls", trace.get("generation_api_call_count", 0))
            metrics_col1.metric("Answer calls", trace.get("answer_generation_call_count", 0))
            metrics_col2.metric("Reranker calls", trace.get("reranker_call_count", 0))
            metrics_col2.metric("Expanded parents", len(result.get("parent_candidates", []) or []))
            metrics_col3.metric("Accepted evidence", len(accepted))
            metrics_col3.metric("Child hits", len(result.get("child_hits", []) or []))

            st.markdown("#### Answer")
            st.write(answer or "(Không có câu trả lời)" )

            if citations:
                st.markdown("#### Citations")
                for citation in citations:
                    st.write(format_citation(citation))

            st.markdown("#### Trace details")
            st.json(trace)

            if accepted:
                st.markdown("#### Accepted evidence summary")
                st.write(accepted)

    with tab2:
        st.subheader("Query Fan-out")
        if result is None or not result.get("query_set"):
            st.info("Chưa có query fan-out. Chạy query để xem các truy vấn và ma trận child.")
        else:
            cards = build_query_cards(result["query_set"], result.get("child_hits", []))
            for card in cards:
                badge_class = "badge-original" if card["is_original"] else "badge-generated"
                st.markdown(
                    f"<div class='card'><span class='badge {badge_class}'>{card['query_id']}</span> <strong>{card['focus']}</strong><br><em>{card['text']}</em><br><strong>Hits:</strong> {card['result_count']} — <strong>Best rank:</strong> {card['best_rank'] or '—'}</div>",
                    unsafe_allow_html=True,
                )

            matrix_html = render_query_child_matrix_html(result["query_set"], result.get("child_hits", []))
            if matrix_html:
                st.markdown("#### Query–child matrix")
                st.markdown(matrix_html, unsafe_allow_html=True)
            else:
                st.info("Không có child hits để hiển thị ma trận.")

    with tab3:
        st.subheader("Parent–Child Explorer")
        if result is None or not result.get("parent_candidates"):
            st.info("Không có parent candidates để khám phá. Chạy mode parent để xem cây parent-child.")
        else:
            parents = build_parent_tree_nodes(result["parent_candidates"])
            parent_summary = {
                "Parent candidates": len(parents),
                "Ambiguous parents": sum(1 for p in parents if p.get("ambiguous")),
                "Total supporting children": sum(len(p.get("supporting_child_ids", [])) for p in parents),
            }
            st.write(parent_summary)
            parent_html = render_parent_tree_html(parents)
            st.markdown(parent_html, unsafe_allow_html=True)

    with tab4:
        st.subheader("Mode Comparison")
        if compare_result is None:
            st.info("Nhấn 'So sánh 4 mode' để chạy retrieval-only qua bốn mode.")
        else:
            rows = build_mode_comparison_rows(compare_result)
            st.dataframe(rows, use_container_width=True)

    with tab5:
        st.subheader("Evaluation")
        latest_report = load_latest_report()
        if latest_report is None:
            st.info("Không tìm thấy báo cáo evaluation. Vui lòng chạy evaluator hoặc đặt report vào reports/latest_report.json.")
        else:
            report_summary = {
                "timestamp": latest_report.get("timestamp"),
                "config": latest_report.get("config", {}).get("config_identity"),
                "mode_count": len(latest_report.get("per_question_results", []) or []),
            }
            st.write(report_summary)
            st.write(latest_report)


if __name__ == "__main__":
    main()
