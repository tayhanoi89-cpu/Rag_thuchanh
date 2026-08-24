"""RBAC-aware Streamlit app for the Buoi 15 retrieval demo."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd
import streamlit as st

from src.config import ROLES
from src.secure_retriever import SecureRetriever, secure_graph_hints


METHOD_LABELS = {
    "BM25": "bm25",
    "Dense": "dense",
    "Hybrid": "hybrid",
    "Hybrid + Rerank": "hybrid_rerank",
    "Graph": "graph",
}
COMPARE_METHODS = ("bm25", "dense", "hybrid", "hybrid_rerank")
COMPARE_LABELS = {
    "bm25": "BM25",
    "dense": "Dense",
    "hybrid": "Hybrid",
    "hybrid_rerank": "Hybrid + Rerank",
}
SAMPLE_QUERIES = {
    "Mã thông tư 01/2014/TT-NHNN": "01/2014/TT-NHNN",
    "Quan hệ sửa đổi, bổ sung văn bản": "văn bản sửa đổi bổ sung",
    "Văn bản thay thế và hiệu lực": "văn bản thay thế hiệu lực",
    "Tìm điều khoản về hoạt động tín dụng": "hoạt động tín dụng điều khoản",
}


def _plain_tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return set(re.findall(r"\w+", normalized))


def concise_answer(question: str, results: list[dict[str, object]], limit: int = 520) -> str:
    """Select a short evidence sentence instead of displaying the whole document."""
    if not results:
        return "Không tìm thấy bằng chứng phù hợp với vai trò hiện tại."
    query_tokens = _plain_tokens(question)
    candidates: list[tuple[int, str]] = []
    for result in results[:3]:
        for sentence in re.split(r"(?<=[.!?;])\s+|\n+", str(result["text"])):
            sentence = " ".join(sentence.split())
            if len(sentence) < 30:
                continue
            score = len(query_tokens.intersection(_plain_tokens(sentence)))
            candidates.append((score, sentence))
    if not candidates:
        return "Đã tìm thấy tài liệu phù hợp; hãy mở phần bằng chứng để xem chi tiết."
    answer = max(candidates, key=lambda item: item[0])[1]
    return answer if len(answer) <= limit else answer[:limit].rsplit(" ", 1)[0] + "..."


st.set_page_config(page_title="Secure RAG | Buoi 15", page_icon=":material/lock:", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink: #14213d; --muted: #667085; --line: #dce4ee; --teal: #0f766e; --teal-soft: #e7f5f2; --red: #b42318; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; color: var(--ink); letter-spacing: 0; }
    .block-container { max-width: 1380px; padding-top: 2.2rem; padding-bottom: 4rem; }
    [data-testid="stSidebar"] { border-right: 1px solid var(--line); background: #f7fafc; }
    .hero { border-bottom: 1px solid var(--line); padding: .25rem 0 1.5rem; margin-bottom: 1.5rem; }
    .hero h1 { font-size: clamp(2rem, 4vw, 3.35rem); line-height: 1.05; margin: 0; }
    .hero-copy { color: var(--muted); font-size: 1rem; margin-top: .7rem; max-width: 820px; }
    .eyebrow, .section-label, .result-kicker { color: var(--teal); font-size: .78rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .section-label { margin: 1.4rem 0 .65rem; }
    .result-title { color: var(--ink); font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem; font-weight: 600; margin-top: .15rem; }
    .security-label { color: var(--teal); background: var(--teal-soft); border: 1px solid #b9e4dc; border-radius: 999px; display: inline-block; padding: .3rem .65rem; font-size: .82rem; font-weight: 700; }
    .empty-state { border: 1px dashed #b8c5d4; border-radius: 12px; padding: 2rem; text-align: center; color: var(--muted); background: #fbfdff; }
    </style>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown("### :material/admin_panel_settings: Secure controls")
    st.caption("Every retrieval and graph citation is filtered by the selected roles.")
    method_label = st.selectbox("Retrieval method", list(METHOD_LABELS), index=2)
    selected_roles = st.multiselect("Your roles", list(ROLES), default=["Guest"])
    top_k = st.slider("Evidence count (k)", min_value=1, max_value=10, value=5)
    candidate_k = st.slider("Candidate count", min_value=top_k, max_value=30, value=max(10, top_k))
    compare_k = st.slider("Comparison depth", min_value=3, max_value=10, value=5)
    st.divider()
    st.markdown("**Active access policy**")
    st.caption(", ".join(selected_roles) if selected_roles else "Select at least one role")

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Buoi 15 / Property-based RBAC</div>
      <h1>Secure RAG Search</h1>
      <div class="hero-copy">Search legal evidence while keeping restricted chunks, reranker candidates, and graph citations outside the active user's view.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

query_choice = st.selectbox("Sample question", [*SAMPLE_QUERIES, "Custom question"])
question = st.text_area(
    "Search question",
    value=SAMPLE_QUERIES.get(query_choice, ""),
    height=90,
    placeholder="Enter a regulation, article, or legal question...",
)
search_col, compare_col, status_col = st.columns([1, 1.25, 2.75], vertical_alignment="center")
with search_col:
    search_clicked = st.button("Search securely", icon=":material/search:", type="primary", use_container_width=True, disabled=not question.strip() or not selected_roles)
with compare_col:
    compare_clicked = st.button("Compare rankings", icon=":material/leaderboard:", use_container_width=True, disabled=not question.strip() or not selected_roles)
with status_col:
    st.caption(f"Role scope: {', '.join(selected_roles) or 'none'}  ·  Method: {method_label}")

retriever = SecureRetriever()

if compare_clicked:
    with st.spinner("Comparing authorized rankings..."):
        comparison_results = {
            method: retriever.retrieve(question.strip(), selected_roles, method, compare_k, candidate_k)
            for method in COMPARE_METHODS
        }
    comparison_rows: dict[str, dict[str, object]] = {}
    for method, rows in comparison_results.items():
        for row in rows:
            item = comparison_rows.setdefault(
                row["chunk_id"],
                {"chunk_id": row["chunk_id"], "document_id": row["document_id"], "allowed_roles": ", ".join(row["allowed_roles"])},
            )
            item[f"{method}_rank"] = row["rank"]
            item[f"{method}_score"] = row["score"]
    ranking_frame = pd.DataFrame(comparison_rows.values())
    for method in COMPARE_METHODS:
        for suffix in ("rank", "score"):
            column = f"{method}_{suffix}"
            if column not in ranking_frame:
                ranking_frame[column] = pd.NA
    rank_columns = [f"{method}_rank" for method in COMPARE_METHODS]
    ranking_frame["rank_spread"] = ranking_frame[rank_columns].max(axis=1, skipna=True) - ranking_frame[rank_columns].min(axis=1, skipna=True)
    ranking_frame = ranking_frame.sort_values(["rank_spread", "hybrid_rerank_rank"], na_position="last")
    display_columns = [
        "chunk_id",
        "document_id",
        "allowed_roles",
        *rank_columns,
        "rank_spread",
        *[f"{method}_score" for method in COMPARE_METHODS],
    ]
    display_frame = ranking_frame[display_columns].rename(
        columns={
            "chunk_id": "Chunk",
            "document_id": "Document",
            "allowed_roles": "Quyen xem",
            "rank_spread": "Do lech hang",
            **{f"{method}_rank": f"{COMPARE_LABELS[method]} - Hang" for method in COMPARE_METHODS},
            **{f"{method}_score": f"{COMPARE_LABELS[method]} - Diem" for method in COMPARE_METHODS},
        }
    )
    st.markdown('<div class="section-label">Bảng so sánh thứ hạng</div>', unsafe_allow_html=True)
    summary_cols = st.columns(3)
    summary_cols[0].metric("Số chunk", len(display_frame), border=True)
    summary_cols[1].metric("Số phương pháp", len(COMPARE_METHODS), border=True)
    summary_cols[2].metric("Độ sâu", f"Top {compare_k}", border=True)
    st.dataframe(display_frame, width="stretch", hide_index=True, height=min(620, 180 + len(display_frame) * 42))

if search_clicked:
    method = METHOD_LABELS[method_label]
    with st.spinner("Filtering access and retrieving evidence..."):
        results = retriever.retrieve(question.strip(), selected_roles, method, top_k, candidate_k)
    stats = retriever.last_filter_stats
    if stats["filtered"]:
        st.toast(f"Đã lọc bỏ {stats['filtered']} kết quả do không đủ quyền truy cập", icon=":material/lock:")

    st.markdown('<div class="section-label">Authorized evidence</div>', unsafe_allow_html=True)
    summary_cols = st.columns(4)
    summary_cols[0].metric("Visible matches", len(results), border=True)
    summary_cols[1].metric("Filtered", stats["filtered"], border=True)
    summary_cols[2].metric("Method", method_label, border=True)
    summary_cols[3].metric("Roles", len(selected_roles), border=True)

    if not results:
        st.markdown('<div class="empty-state">No authorized evidence found for this query.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-label">Câu trả lời ngắn</div>', unsafe_allow_html=True)
        st.info(concise_answer(question.strip(), results), icon=":material/auto_awesome:")

    for row in results:
        with st.container(border=True):
            st.markdown(
                f'<div class="result-kicker">Evidence {row["rank"]:02d} · {row["retrieval_method"]}</div>'
                f'<div class="result-title">{row["chunk_id"]}</div>',
                unsafe_allow_html=True,
            )
            first_row = st.columns(4)
            first_row[0].metric("Document", row["document_id"])
            first_row[1].metric("Score", f"{row['score']:.6f}")
            first_row[2].write(f"**Citation**\n{row['citation']}")
            first_row[3].markdown(f'<span class="security-label">Quyền xem: [{", ".join(row["allowed_roles"])}]</span>', unsafe_allow_html=True)
            with st.expander("Mở bằng chứng đầy đủ", expanded=False):
                st.write(row["text"])

    st.markdown('<div class="section-label">Secure knowledge graph context</div>', unsafe_allow_html=True)
    document_ids = list(dict.fromkeys(row["document_id"] for row in results))
    chunk_ids = list(dict.fromkeys(row["chunk_id"] for row in results))
    st.caption(f"Documents: {', '.join(document_ids) or 'None'}")
    st.caption(f"Chunks: {', '.join(chunk_ids) or 'None'}")
    hints, error = secure_graph_hints(document_ids, selected_roles)
    if error:
        st.warning(error, icon=":material/warning:")
    elif hints:
        st.dataframe(hints, width="stretch", hide_index=True)
    else:
        st.info("No authorized graph relationships found for these documents.", icon=":material/info:")
else:
    st.markdown('<div class="empty-state"><b>Secure search ready</b><br>Select a role, enter a legal question, and run an access-filtered search.</div>', unsafe_allow_html=True)