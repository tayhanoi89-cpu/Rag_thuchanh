"""Streamlit dashboard cho Buổi 08 Advanced RAG."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import streamlit as st

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from advanced_rag import (
    BASE_DIR,
    answer_question,
    build_status,
    compare_retrieval_modes,
    load_runtime_config,
)


def _load_chunks(strategy: str) -> list[dict[str, Any]]:
    cache_key = f"chunks:{strategy}"
    if cache_key not in st.session_state:
        fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json"
        chunks = [dict(item) for item in json.loads(fixture_path.read_text(encoding="utf-8"))]
        if strategy and chunks and chunks[0].get("strategy") != strategy:
            chunks = [chunk for chunk in chunks if chunk.get("strategy") == strategy]
        st.session_state[cache_key] = chunks
    return st.session_state[cache_key]


def _embedding_provider(text: str, config: dict[str, Any]) -> list[float]:
    lowered = text.lower()
    if "cơ cấu lại thời hạn trả nợ" in lowered or "thời hạn trả nợ" in lowered:
        return [1.0, 0.0, 0.0, 0.0]
    if "điều chỉnh kỳ hạn" in lowered or "thỏa thuận" in lowered or "kỳ hạn" in lowered:
        return [0.5, 1.0, 0.0, 0.0]
    return [0.0, 0.0, 1.0, 0.0]


def _offline_generation(prompt: str, config: dict[str, Any]) -> str:
    labels = re.findall(r"\[(E\d+)\]", prompt)
    return " ".join(labels) if labels else "[E1]"


def _build_sidebar_config() -> tuple[dict[str, Any], dict[str, Any]]:
    config = dict(load_runtime_config())
    st.set_page_config(page_title="Buổi 08 Advanced RAG", page_icon="🧠", layout="wide")
    st.sidebar.title("Advanced RAG controls")
    strategy = st.sidebar.selectbox("Strategy", ["hierarchical", "fixed-size", "semantic"], index=0)
    mode = st.sidebar.selectbox("Retrieval mode", ["bm25", "semantic", "hybrid", "hybrid_rerank"], index=3)
    final_top_k = st.sidebar.number_input("Final top-k", min_value=1, max_value=20, value=config.get("final_top_k", 5))
    bm25_candidates = st.sidebar.number_input("BM25 candidates", min_value=1, max_value=20, value=config.get("bm25_candidates", 20))
    semantic_candidates = st.sidebar.number_input("Semantic candidates", min_value=1, max_value=20, value=config.get("semantic_candidates", 20))
    rrf_k = st.sidebar.number_input("RRF k", min_value=1, max_value=200, value=config.get("rrf_k", 60))
    rrf_bm25_weight = st.sidebar.number_input("RRF BM25 weight", min_value=0.0, max_value=5.0, value=config.get("rrf_bm25_weight", 1.0), step=0.1)
    rrf_semantic_weight = st.sidebar.number_input("RRF semantic weight", min_value=0.0, max_value=5.0, value=config.get("rrf_semantic_weight", 1.0), step=0.1)
    reranker_model = st.sidebar.text_input("Reranker model", value=config.get("reranker_model", ""))
    reranker_device = st.sidebar.selectbox("Reranker device", ["auto", "cpu", "cuda"], index=0)
    rerank_candidates = st.sidebar.number_input("Rerank candidates", min_value=1, max_value=20, value=config.get("rerank_candidates", 20))
    rerank_min_score = st.sidebar.slider("Rerank min score", min_value=0.0, max_value=1.0, value=config.get("rerank_min_score", 0.5), step=0.01)

    config.update(
        {
            "final_top_k": int(final_top_k),
            "bm25_candidates": int(bm25_candidates),
            "semantic_candidates": int(semantic_candidates),
            "rrf_k": int(rrf_k),
            "rrf_bm25_weight": float(rrf_bm25_weight),
            "rrf_semantic_weight": float(rrf_semantic_weight),
            "reranker_model": reranker_model,
            "rerank_device": reranker_device,
            "rerank_candidates": int(rerank_candidates),
            "rerank_min_score": float(rerank_min_score),
        }
    )
    return {"strategy": strategy, "mode": mode}, config


def _render_answer_tab(strategy: str, mode: str, config: dict[str, Any], chunks: list[dict[str, Any]]) -> None:
    st.header("Hỏi đáp Advanced RAG")
    question = st.text_area("Câu hỏi", value=st.session_state.get("last_question", "Điều 7 quy định như thế nào về cơ cấu lại thời hạn trả nợ?"))
    run_query = st.button("Chạy retrieval + answer", use_container_width=True)

    if run_query or "last_result" in st.session_state:
        if run_query:
            st.session_state["last_question"] = question
        result = answer_question(
            question=question,
            mode=mode,
            strategy=strategy,
            chunks=chunks,
            config=config,
            embedding_provider=_embedding_provider,
            generation_fn=_offline_generation,
        )
        st.session_state["last_result"] = result

    result = st.session_state.get("last_result")
    if result is None:
        st.info("Nhập câu hỏi và chạy pipeline để xem answer, evidence và citations.")
        return

    status_color = "green" if result["status"] == "answered" else "orange"
    st.markdown(f"<div style='padding:8px;border-radius:8px;background-color:{status_color}22'>Status: <b>{result['status']}</b></div>", unsafe_allow_html=True)

    if result["status"] == "reranker_unavailable":
        st.warning("Reranker không khả dụng trong phiên này. UI vẫn hiển thị evidence từ retrieval nhưng không giả vờ rằng rerank đã thành công. Bạn có thể thử lại sau khi tải model.")

    st.subheader("Answer")
    st.write(result.get("answer") or "Không có answer được sinh ra.")

    st.subheader("Citations")
    if result.get("citations"):
        for citation in result["citations"]:
            st.write(f"- {citation['label']}: {citation['chunk_id']} ({citation['source']}, trang {citation['page_start']}-{citation['page_end']})")
    else:
        st.write("Không có citation hợp lệ.")

    st.subheader("Evidence")
    for index, item in enumerate(result.get("evidence", []), start=1):
        with st.expander(f"[{index}] {item['chunk_id']} — accepted={bool(item.get('accepted'))}"):
            st.write(f"Source: {item['source']}")
            st.write(f"Page: {item['page']}")
            st.write(f"Text: {item['text']}")
            st.write(f"BM25 rank/score: {item.get('bm25_rank')} / {item.get('bm25_score')}")
            st.write(f"Semantic rank/distance: {item.get('semantic_rank')} / {item.get('semantic_distance')}")
            st.write(f"RRF score / fused rank: {item.get('rrf_score')} / {item.get('fused_rank')}")
            st.write(f"Rerank raw/normalized: {item.get('rerank_raw_score')} / {item.get('rerank_score')}")
            st.write(f"Rerank rank / rank change: {item.get('rerank_rank')} / {item.get('rank_change')}")
            st.write(f"Accepted: {bool(item.get('accepted'))}")


def _render_comparison_tab(strategy: str, mode: str, config: dict[str, Any], chunks: list[dict[str, Any]]) -> None:
    st.header("So sánh Retrieval")
    question = st.session_state.get("last_question", "Điều 7 quy định như thế nào về cơ cấu lại thời hạn trả nợ?")
    if st.button("Chạy so sánh 4 mode", key="compare_button", use_container_width=True):
        st.session_state["comparison_result"] = compare_retrieval_modes(
            question=question,
            strategy=strategy,
            chunks=chunks,
            config=config,
            embedding_provider=_embedding_provider,
        )

    comparison = st.session_state.get("comparison_result")
    if comparison is None:
        st.info("Nhấn nút để chạy BM25, Semantic, Hybrid RRF và Hybrid + Rerank trên cùng một câu hỏi.")
        return

    rows: dict[str, dict[str, Any]] = {}
    for mode_name in ["bm25", "semantic", "hybrid", "hybrid_rerank"]:
        mode_result = comparison["mode_results"][mode_name]
        for item in mode_result["results"]:
            chunk_id = item["chunk_id"]
            row = rows.setdefault(chunk_id, {"chunk_id": chunk_id, "bm25_rank": None, "semantic_rank": None, "fused_rank": None, "rerank_rank": None, "rank_change": None, "final_modes": []})
            if mode_name == "bm25":
                row["bm25_rank"] = item["rank"]
            elif mode_name == "semantic":
                row["semantic_rank"] = item["rank"]
            elif mode_name == "hybrid":
                row["fused_rank"] = item["rank"]
            elif mode_name == "hybrid_rerank":
                row["rerank_rank"] = item["rank"]
            row["final_modes"].append(mode_name)
    for row in rows.values():
        bm25_rank = row.get("bm25_rank")
        rerank_rank = row.get("rerank_rank")
        if bm25_rank is not None and rerank_rank is not None:
            row["rank_change"] = bm25_rank - rerank_rank
        row["final_modes"] = ", ".join(sorted(set(row["final_modes"])))

    st.dataframe(
        [
            {
                "chunk_id": row["chunk_id"],
                "bm25_rank": row["bm25_rank"],
                "semantic_rank": row["semantic_rank"],
                "fused_rank": row["fused_rank"],
                "rerank_rank": row["rerank_rank"],
                "rank_change": row["rank_change"],
                "final_modes": row["final_modes"],
            }
            for row in sorted(rows.values(), key=lambda item: (item["bm25_rank"] or 999, item["chunk_id"]))
        ]
    )

    cols = st.columns(4)
    for col, mode_name in zip(cols, ["bm25", "semantic", "hybrid", "hybrid_rerank"]):
        with col:
            st.subheader(mode_name)
            mode_result = comparison["mode_results"][mode_name]["results"]
            for item in mode_result[:5]:
                st.write(f"{item['rank']}. {item['chunk_id']}")


def _render_trace_tab(result: dict[str, Any] | None) -> None:
    st.header("Pipeline Trace")
    if result is None:
        st.info("Chạy một query trước để xem trace từ BM25, semantic, fusion, rerank và generation.")
        return

    trace = result.get("trace", {})
    metrics = trace.get("latency_ms", {})
    st.metric("BM25 candidates", trace.get("bm25_candidates", 0))
    st.metric("Semantic candidates", trace.get("semantic_candidates", 0))
    st.metric("Union / Overlap", f"{trace.get('union', 0)} / {trace.get('overlap', 0)}")
    st.metric("Reranked", trace.get("reranked", 0))
    st.metric("Accepted", trace.get("accepted", 0))

    st.caption("BM25 score cao hơn tốt hơn; cosine distance thấp hơn tốt hơn; RRF/rerank score cao hơn tốt hơn; rerank score không phải xác suất.")

    st.dataframe(
        [
            {"stage": name, "latency_ms": value}
            for name, value in {
                "bm25": metrics.get("bm25", 0.0),
                "semantic": metrics.get("semantic", 0.0),
                "fusion": metrics.get("fusion", 0.0),
                "rerank": metrics.get("rerank", 0.0),
                "generation": metrics.get("generation", 0.0),
                "total": metrics.get("total", 0.0),
            }.items()
        ]
    )


def _render_evaluation_tab() -> None:
    st.header("Đánh giá")
    reports_dir = BASE_DIR / "reports"
    report_files = sorted([path for path in reports_dir.glob("*.json")]) if reports_dir.exists() else []
    if not report_files:
        st.info("Chưa có report JSON. Chạy evaluate.py trước để tạo report cho tab này.")
        return

    selected = st.selectbox("Report file", [path.name for path in report_files])
    report = json.loads((reports_dir / selected).read_text(encoding="utf-8"))
    if report.get("warnings"):
        st.warning("\n".join(report["warnings"]))

    st.write(report.get("summary", {}))
    st.dataframe(report.get("metrics", []))
    st.dataframe(report.get("latency", []))


def main() -> None:
    config = dict(load_runtime_config())
    sidebar_state, config = _build_sidebar_config()
    strategy = sidebar_state["strategy"]
    mode = sidebar_state["mode"]
    chunks = _load_chunks(strategy)

    st.title("Buổi 08 — Advanced RAG comparison dashboard")
    status = build_status(strategy=strategy, config=config)
    st.caption(f"Semantic collection: {status['collection_name']} | count: {status['collection_count']} | API key: {'Có' if config.get('has_api_key') else 'Thiếu'}")

    tab1, tab2, tab3, tab4 = st.tabs(["Hỏi đáp Advanced RAG", "So sánh Retrieval", "Pipeline Trace", "Đánh giá"])

    with tab1:
        _render_answer_tab(strategy=strategy, mode=mode, config=config, chunks=chunks)
    with tab2:
        _render_comparison_tab(strategy=strategy, mode=mode, config=config, chunks=chunks)
    with tab3:
        _render_trace_tab(st.session_state.get("last_result"))
    with tab4:
        _render_evaluation_tab()


if __name__ == "__main__":
    main()
