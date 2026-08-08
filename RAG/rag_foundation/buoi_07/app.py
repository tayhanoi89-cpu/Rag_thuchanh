"""Minimal Streamlit UI for the Buổi 07 RAG workflow."""

from __future__ import annotations

import os
from typing import Any

import streamlit as st

from rag import (
    build_collection_name,
    load_runtime_config,
    run_index,
    run_status,
    ask_question,
)


st.set_page_config(page_title="RAG Buổi 07", page_icon="📚", layout="wide")


def _format_status_label(status: str) -> str:
    mapping = {
        "answered": "Đã có câu trả lời",
        "insufficient_evidence": "Thiếu evidence",
        "retrieval_only": "Chỉ có retrieval",
    }
    return mapping.get(status, status)


def _safe_status() -> dict[str, Any]:
    try:
        return run_status(strategy=st.session_state.get("strategy", "hierarchical"))
    except Exception as exc:
        return {
            "api_key_present": False,
            "embedding_model": "",
            "embedding_dim": 0,
            "generation_model": "",
            "strategy": st.session_state.get("strategy", "hierarchical"),
            "collection_name": "",
            "collection_exists": False,
            "record_count": 0,
            "error": str(exc),
        }


def _render_sidebar() -> None:
    st.sidebar.header("⚙️ Trạng thái hệ thống")

    status = _safe_status()
    try:
        config = load_runtime_config()
    except Exception:
        config = {}

    st.sidebar.text(f"API key: {'Có' if status.get('api_key_present') else 'Thiếu'}")
    st.sidebar.text(f"Embedding model: {config.get('embedding_model', '')}")
    st.sidebar.text(f"Embedding dimension: {config.get('embedding_dim', '')}")
    st.sidebar.text(f"Generation model: {config.get('generation_model', '')}")
    st.sidebar.text(f"Strategy: {status.get('strategy', st.session_state.get('strategy', 'hierarchical'))}")
    st.sidebar.text(f"Collection: {status.get('collection_name', '')}")
    st.sidebar.text(f"Collection tồn tại: {'Có' if status.get('collection_exists') else 'Không'}")
    st.sidebar.text(f"Số chunk: {status.get('record_count', 0)}")
    st.sidebar.text(f"RAG_MAX_DISTANCE: {config.get('rag_max_distance', '')}")

    if status.get("error"):
        st.sidebar.warning(f"Không thể đọc trạng thái: {status['error']}")


def _render_index_area() -> None:
    st.subheader("🗂️ Index dữ liệu")
    reset_collection = st.checkbox("Reset collection trước khi index", value=False)
    if st.button("Index dữ liệu", use_container_width=True):
        with st.spinner("Đang index dữ liệu..."):
            try:
                result = run_index(
                    strategy=st.session_state.get("strategy", "hierarchical"),
                    reset=reset_collection,
                )
                st.session_state["last_index_result"] = result
                st.success("Index thành công")
                st.json(result)
            except Exception as exc:
                st.error(f"Không thể index dữ liệu: {exc}")


def _render_question_area() -> None:
    st.subheader("💬 Hỏi đáp")
    question = st.text_area("Nhập câu hỏi", placeholder="Ví dụ: Điều gì được quy định về ...")
    if st.button("Gửi câu hỏi", use_container_width=True):
        strategy = st.session_state.get("strategy", "hierarchical")
        status = _safe_status()

        if not question.strip():
            st.info("Vui lòng nhập câu hỏi trước khi gửi.")
            return
        if not status.get("api_key_present"):
            st.warning("Thiếu API key. Hãy điền GEMINI_API_KEY vào file .env trước khi hỏi.")
            return
        if not status.get("collection_exists"):
            st.warning("Collection chưa tồn tại. Hãy chạy index trước khi hỏi.")
            return
        if status.get("record_count", 0) <= 0:
            st.warning("Collection hiện đang rỗng. Hãy chạy index trước khi hỏi.")
            return

        with st.spinner("Đang truy vấn..."):
            try:
                result = ask_question(question=question, top_k=st.session_state.get("top_k", 5), strategy=strategy)
                st.session_state["last_query_result"] = result
                st.session_state["last_query_question"] = question
            except Exception as exc:
                st.error(f"Không thể thực hiện truy vấn: {exc}")
                return

        st.markdown("### Kết quả")
        st.write(f"Status: **{_format_status_label(result.get('status', ''))}**")
        if result.get("warnings"):
            for warning in result["warnings"]:
                st.warning(warning)

        if result.get("status") == "answered":
            st.write(result.get("answer", ""))
        elif result.get("status") == "insufficient_evidence":
            st.info("Không tìm thấy đủ thông tin liên quan trong tài liệu đã cung cấp.")
        else:
            st.info("Đã truy xuất được nguồn nhưng chưa thể tạo câu trả lời tổng hợp.")

        if result.get("citations"):
            st.subheader("📎 Citation")
            for citation in result["citations"]:
                st.write(citation.get("display", ""))

        st.subheader("📚 Nguồn tham khảo")
        if result.get("evidence"):
            for evidence in result.get("evidence", []):
                summary = f"{evidence.get('source', '')} – tr. {evidence.get('page_start', 1)}"
                if evidence.get('page_start') != evidence.get('page_end'):
                    summary = f"{summary}-{evidence.get('page_end', 1)}"
                summary = f"{summary} – {evidence.get('chunk_id', '')}"
                with st.expander(summary):
                    st.write(f"- evidence_id: {evidence.get('evidence_id', '')}")
                    st.write(f"- source: {evidence.get('source', '')}")
                    st.write(f"- page: {evidence.get('page_start', 1)}-{evidence.get('page_end', 1)}")
                    st.write(f"- chunk_id: {evidence.get('chunk_id', '')}")
                    st.write(f"- distance: {evidence.get('distance', 0):.4f}")
                    st.write(f"- accepted: {'Có' if evidence.get('accepted') else 'Không'}")
                    st.write("- nội dung chunk:")
                    st.write(evidence.get("text", ""))
        else:
            st.info("Chưa có evidence")


def main() -> None:
    if "strategy" not in st.session_state:
        st.session_state["strategy"] = "hierarchical"
    if "top_k" not in st.session_state:
        st.session_state["top_k"] = 5
    if "last_index_result" not in st.session_state:
        st.session_state["last_index_result"] = None
    if "last_query_result" not in st.session_state:
        st.session_state["last_query_result"] = None

    _render_sidebar()

    st.title("RAG Buổi 07")
    st.caption("Giao diện tiếng Việt cho retrieval, grounding và citation")

    strategy = st.selectbox("Strategy", ["hierarchical", "semantic", "fixed-size"], index=0)
    if strategy != st.session_state.get("strategy"):
        st.session_state["strategy"] = strategy
        st.session_state["last_query_result"] = None
        st.session_state["last_index_result"] = None

    top_k = st.slider("Top-k", min_value=1, max_value=10, value=st.session_state.get("top_k", 5))
    st.session_state["top_k"] = top_k

    _render_index_area()
    _render_question_area()


if __name__ == "__main__":
    main()
