"""Streamlit demo for the shared Buoi 14 retrieval pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.graph_hints import direct_graph_hints
from src.hybrid_retriever import HybridRetriever
from src.reranker import CandidateReranker
from src.unified_retriever import retrieve


METHOD_LABELS = {
    "BM25": "bm25",
    "Dense": "dense",
    "Hybrid": "hybrid",
    "Hybrid + Rerank": "hybrid_rerank",
}

SAMPLE_QUERIES = {
    "Mã thông tư 01/2014/TT-NHNN": "01/2014/TT-NHNN",
    "Quan hệ sửa đổi, bổ sung văn bản": "văn bản sửa đổi bổ sung",
    "Văn bản thay thế và hiệu lực": "văn bản thay thế hiệu lực",
    "Tìm điều khoản về hoạt động tín dụng": "hoạt động tín dụng điều khoản",
}
COMPARE_METHODS = list(METHOD_LABELS.values())
COMPARE_LABELS = {value: label for label, value in METHOD_LABELS.items()}


st.set_page_config(page_title="RAG Hybrid Search | Buoi 14", page_icon=":material/search:", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --ink: #14213d; --muted: #667085; --line: #dce4ee; --teal: #0f766e; --teal-soft: #e7f5f2; --gold: #d97706; }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif; color: var(--ink); letter-spacing: 0; }
    .block-container { max-width: 1380px; padding-top: 2.2rem; padding-bottom: 4rem; }
    [data-testid="stSidebar"] { border-right: 1px solid var(--line); background: #f7fafc; }
    [data-testid="stSidebar"] .block-container { padding-top: 2rem; }
    .eyebrow { color: var(--teal); font-size: .76rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .35rem; }
    .hero { border-bottom: 1px solid var(--line); padding: .25rem 0 1.5rem; margin-bottom: 1.5rem; }
    .hero h1 { font-size: clamp(2rem, 4vw, 3.35rem); line-height: 1.05; margin: 0; }
    .hero-copy { color: var(--muted); font-size: 1rem; margin-top: .7rem; max-width: 760px; }
    .pill { display: inline-block; background: var(--teal-soft); color: var(--teal); border: 1px solid #b9e4dc; border-radius: 999px; padding: .35rem .7rem; font-size: .78rem; font-weight: 700; }
    .section-label { color: var(--muted); font-size: .78rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; margin: 1.4rem 0 .65rem; }
    .result-kicker { color: var(--teal); font-size: .78rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
    .result-title { color: var(--ink); font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem; font-weight: 600; margin-top: .15rem; }
    .score-strip { background: #f8fafc; border: 1px solid var(--line); border-radius: 10px; padding: .65rem .85rem; color: var(--muted); font-size: .86rem; }
    .empty-state { border: 1px dashed #b8c5d4; border-radius: 12px; padding: 2rem; text-align: center; color: var(--muted); background: #fbfdff; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### :material/tune: Search controls")
    st.caption("Tune the retrieval strategy and evidence depth.")
    method_label = st.selectbox("Retrieval method", list(METHOD_LABELS), index=2)
    top_k = st.slider("Evidence count", min_value=1, max_value=10, value=5)
    compare_k = st.slider("Comparison depth", min_value=3, max_value=10, value=5)
    st.divider()
    st.markdown("**Available methods**")
    st.caption("BM25 · Dense · Hybrid RRF · Hybrid + Rerank")

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Buoi 14 / Retrieval workspace</div>
      <h1>RAG Hybrid Search</h1>
      <div class="hero-copy">Find grounded legal evidence with lexical, semantic, and hybrid retrieval in one focused workspace.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

query_choice = st.selectbox(
    "Sample question",
    [*SAMPLE_QUERIES, "Custom question"],
    index=0,
    help="Choose a prepared legal retrieval query or switch to Custom question.",
)
default_question = SAMPLE_QUERIES.get(query_choice, "")
question = st.text_area(
    "Search question",
    value=default_question,
    height=90,
    placeholder="Enter a regulation, article, or legal question...",
    label_visibility="visible",
)
search_col, compare_col, hint_col = st.columns([1, 1.35, 2.65], vertical_alignment="center")
with search_col:
    search_clicked = st.button("Search evidence", icon=":material/search:", type="primary", use_container_width=True, disabled=not question.strip())
with compare_col:
    compare_clicked = st.button("Compare rankings", icon=":material/leaderboard:", use_container_width=True, disabled=not question.strip())
with hint_col:
    st.caption(f"Active method: {method_label}  ·  Returning up to {top_k} evidence items")

if compare_clicked:
    with st.spinner("Comparing retrieval rankings..."):
        comparison_results = {method: retrieve(question.strip(), method, compare_k) for method in COMPARE_METHODS}
    comparison_rows: dict[str, dict[str, object]] = {}
    for method, rows in comparison_results.items():
        for row in rows:
            item = comparison_rows.setdefault(
                row["chunk_id"],
                {"chunk_id": row["chunk_id"], "document_id": row["document_id"], "citation": row["citation"], "text": row["text"]},
            )
            item[f"{method}_rank"] = row["rank"]
            item[f"{method}_score"] = row["score"]

    ranking_frame = pd.DataFrame(comparison_rows.values())
    rank_columns = [f"{method}_rank" for method in COMPARE_METHODS]
    score_columns = [f"{method}_score" for method in COMPARE_METHODS]
    for column in [*rank_columns, *score_columns]:
        if column not in ranking_frame:
            ranking_frame[column] = pd.NA
    ranking_frame["rank_spread"] = ranking_frame[rank_columns].max(axis=1, skipna=True) - ranking_frame[rank_columns].min(axis=1, skipna=True)
    ranking_frame = ranking_frame.sort_values(["rank_spread", "hybrid_rerank_rank", "hybrid_rank"], na_position="last")
    display_frame = ranking_frame[["chunk_id", "document_id", *rank_columns, "rank_spread", *score_columns]].rename(
        columns={
            "chunk_id": "Chunk",
            "document_id": "Document",
            "rank_spread": "Rank spread",
            **{f"{method}_rank": f"{COMPARE_LABELS[method]} rank" for method in COMPARE_METHODS},
            **{f"{method}_score": f"{COMPARE_LABELS[method]} score" for method in COMPARE_METHODS},
        }
    )
    st.markdown('<div class="section-label">Ranking comparison</div>', unsafe_allow_html=True)
    compare_summary = st.columns(3)
    compare_summary[0].metric("Compared chunks", len(display_frame), border=True)
    compare_summary[1].metric("Methods", len(COMPARE_METHODS), border=True)
    compare_summary[2].metric("Depth per method", f"Top {compare_k}", border=True)
    st.caption(":material/lightbulb: Rank spread shows how differently each retriever orders the same chunk. Lower spread means stronger agreement.")

    def highlight_ranks(column: pd.Series) -> list[str]:
        numeric = pd.to_numeric(column, errors="coerce")
        if numeric.isna().all():
            return ["" for _ in column]
        best = numeric.min()
        return ["background-color: #dff4ef; color: #11665f; font-weight: 700" if value == best else "" for value in numeric]

    styled_frame = display_frame.style.apply(highlight_ranks, subset=[f"{COMPARE_LABELS[method]} rank" for method in COMPARE_METHODS])
    st.dataframe(styled_frame, width="stretch", hide_index=True, height=min(620, 120 + len(display_frame) * 42))
    with st.expander("Inspect compared passages"):
        for _, row in ranking_frame.iterrows():
            st.markdown(f"**{row['chunk_id']}** · {row['citation']}")
            st.caption(str(row["text"])[:500] + ("..." if len(str(row["text"])) > 500 else ""))

if search_clicked:
    method = METHOD_LABELS[method_label]
    with st.spinner("Đang truy vấn..."):
        results = retrieve(question.strip(), method, top_k)

    st.markdown('<div class="section-label">Evidence results</div>', unsafe_allow_html=True)
    summary_cols = st.columns(3)
    summary_cols[0].metric("Matches", len(results), border=True)
    summary_cols[1].metric("Method", method_label, border=True)
    summary_cols[2].metric("Evidence depth", f"Top {top_k}", border=True)

    if not results:
        st.markdown('<div class="empty-state">No evidence found for this query. Try a broader legal phrase or another retrieval method.</div>', unsafe_allow_html=True)

    for row in results:
        with st.container(border=True):
            st.markdown(f'<div class="result-kicker">Evidence {row["rank"]:02d} · {row["retrieval_method"]}</div><div class="result-title">{row["chunk_id"]}</div>', unsafe_allow_html=True)
            first_row = st.columns(4)
            first_row[0].metric("Document", row["document_id"], border=False)
            first_row[1].metric("Score", f"{row['score']:.6f}", border=False)
            first_row[2].write(f"**Citation**\n{row['citation']}")
            first_row[3].write(f"**Rank**\n#{row['rank']}")
            if "hybrid_score" in row:
                st.markdown(f'<div class="score-strip">Hybrid score <b>{row["hybrid_score"]:.8f}</b> &nbsp; · &nbsp; Rerank score <b>{row["rerank_score"]:.8f}</b> &nbsp; · &nbsp; Hybrid rank <b>{row["hybrid_rank"]}</b></div>', unsafe_allow_html=True)
            with st.expander("View source passage", expanded=True):
                st.write(row["text"])

    if method == "hybrid_rerank":
        st.markdown('<div class="section-label">Rerank diagnostics</div>', unsafe_allow_html=True)
        st.subheader("Before / After Rerank", anchor=False)
        candidates = HybridRetriever().search(question.strip(), top_k=max(top_k, 20), candidate_k=max(top_k, 20))
        reranker = CandidateReranker()
        reranked = reranker.rerank(question.strip(), candidates, top_k)
        before = {row["chunk_id"]: row["final_rank"] for row in candidates[:top_k]}
        after = {row["chunk_id"]: row["final_rank"] for row in reranked}
        comparison = [
            {
                "chunk_id": chunk_id,
                "before_hybrid_rank": before.get(chunk_id),
                "after_rerank_rank": after.get(chunk_id),
            }
            for chunk_id in dict.fromkeys([*before, *after])
        ]
        st.dataframe(comparison, width="stretch", hide_index=True)
        st.caption(f":material/auto_awesome: Reranker mode: {reranker.mode}")

    st.markdown('<div class="section-label">Knowledge graph context</div>', unsafe_allow_html=True)
    st.subheader("Graph hints", anchor=False)
    document_ids = list(dict.fromkeys(row["document_id"] for row in results))
    chunk_ids = list(dict.fromkeys(row["chunk_id"] for row in results))
    st.caption(f":material/description: Documents  ·  {', '.join(document_ids) or 'None'}")
    st.caption(f":material/segment: Chunks  ·  {', '.join(chunk_ids) or 'None'}")
    hints, error = direct_graph_hints(document_ids)
    if error:
        st.warning(error, icon=":material/warning:")
    elif hints:
        st.dataframe(hints, width="stretch", hide_index=True)
    else:
        st.info("No direct Buoi 14 relationships found for these documents.", icon=":material/info:")
else:
    st.markdown('<div class="empty-state"><b>Ready to search</b><br>Enter a legal question or document code, then choose a retrieval method.</div>', unsafe_allow_html=True)