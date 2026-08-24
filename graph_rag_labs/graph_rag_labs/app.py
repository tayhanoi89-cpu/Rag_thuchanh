from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from graph_rag_qa_gemini import _build_context_text, _build_system_prompt, ask_gemini
from multi_hop_retrieval import MultiHopRetriever, parse_relation_types


st.set_page_config(page_title="Buổi 11 - Multi-hop Graph RAG", page_icon="🧠", layout="wide")

st.markdown(
    """
    <style>
    .main .block-container { padding-top: 1.2rem; }
    div[data-testid="stExpander"] > div[role="button"] { background: #f5f7ff; border-radius: 0.7rem; }
    .metric-card {
        background: linear-gradient(135deg, #eef4ff, #f7f9ff);
        border: 1px solid #dfe7ff;
        border-radius: 0.8rem;
        padding: 0.9rem 1rem;
        margin-bottom: 0.6rem;
    }
    .metric-card .label { color: #5a6787; font-size: 0.78rem; font-weight: 600; }
    .metric-card .value { font-size: 1.5rem; font-weight: 700; color: #1f2a44; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Buổi 11 - Multi-hop Graph RAG QA")
st.caption("Truy vấn vector + mở rộng multi-hop trong Neo4j + trả lời bằng Gemini")

with st.sidebar:
    st.header("Cấu hình truy vấn")
    api_key = st.text_input("GEMINI_API_KEY", value=os.getenv("GEMINI_API_KEY", ""), type="password")
    top_k = st.slider("Top-k direct chunks", 1, 20, 5)
    compare_hops = st.multiselect("So sánh hops", options=[0, 1, 2, 3], default=[0, 1, 2])
    relation_types = st.text_input("Relation types", value="CAN_CU,THAY_THE,HOP_NHAT")
    max_hop_documents = st.slider("Max expanded docs", 1, 50, 20)
    hop_chunk_limit = st.slider("Chunks mỗi doc mở rộng", 1, 10, 2)
    max_direct_chunks = st.slider("Max direct chunks trong context", 1, 12, 6)
    max_hop_chunks = st.slider("Max hop chunks trong context", 1, 20, 10)
    st.divider()
    st.subheader("Tùy chỉnh câu trả lời")
    answer_style = st.selectbox(
        "Kiểu câu trả lời",
        options=["Ngắn gọn", "Chi tiết", "Theo định dạng luật"],
        index=0,
    )
    include_citations = st.checkbox("Có trích dẫn nguồn", value=True)
    answer_temperature = st.slider("Độ sáng tạo / nhiệt độ", min_value=0.0, max_value=1.0, value=0.1, step=0.05)
    max_answer_chars = st.slider("Độ dài mục tiêu", min_value=200, max_value=2000, value=800, step=50)


DEFAULT_QUESTION = "Nghị định 46/2023/NĐ-CP thay thế nghị định nào?"
question = st.text_area("Câu hỏi", value=DEFAULT_QUESTION, height=120)


def render_metric_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if st.button("Chạy truy vấn", type="primary"):
    if not question.strip():
        st.warning("Vui lòng nhập câu hỏi.")
        st.stop()

    api_key_value = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not api_key_value:
        st.warning("Chưa có GEMINI_API_KEY. Hãy nhập vào sidebar hoặc đặt biến môi trường trước khi chạy.")
        st.stop()

    os.environ["GEMINI_API_KEY"] = api_key_value
    relation_types_list = parse_relation_types(relation_types)
    compare_hops = sorted(set(compare_hops)) if compare_hops else [0]

    with st.spinner("Đang truy vấn Neo4j, xây dựng ngữ cảnh và gọi Gemini cho từng hop..."):
        retriever = MultiHopRetriever()
        try:
            results = []
            for hop_value in compare_hops:
                retrieval_result = retriever.search_context(
                    question=question,
                    top_k=top_k,
                    hops=hop_value,
                    relation_types=relation_types_list,
                    max_hop_documents=max_hop_documents,
                    hop_chunk_limit=hop_chunk_limit,
                )

                context_text = _build_context_text(
                    retrieval_result=retrieval_result,
                    max_direct_chunks=max_direct_chunks,
                    max_hop_chunks=max_hop_chunks,
                )

                answer = ask_gemini(
                    api_key=api_key_value,
                    model_name="gemini-flash-latest",
                    system_prompt=_build_system_prompt(
                        response_style=answer_style,
                        include_citations=include_citations,
                        max_answer_chars=max_answer_chars,
                    ),
                    user_question=question,
                    context_text=context_text,
                    temperature=answer_temperature,
                    response_style=answer_style,
                    include_citations=include_citations,
                    max_answer_chars=max_answer_chars,
                )

                results.append(
                    {
                        "hops": hop_value,
                        "direct_chunks": len(retrieval_result.get("direct_chunks", [])),
                        "hop_documents": len(retrieval_result.get("hop_documents", [])),
                        "hop_chunks": len(retrieval_result.get("hop_chunks", [])),
                        "seed_documents": len(retrieval_result.get("seed_document_ids", [])),
                        "answer": answer.strip(),
                        "retrieval_result": retrieval_result,
                    }
                )

            if not results:
                st.warning("Chưa có kết quả nào được tạo.")
                st.stop()

            summary_df = pd.DataFrame(results)
            summary_df = summary_df[
                ["hops", "seed_documents", "direct_chunks", "hop_documents", "hop_chunks"]
            ]

            st.subheader("Tổng quan so sánh")
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown("<div class='metric-card'><div class='label'>Hops được so sánh</div><div class='value'>" + str(len(compare_hops)) + "</div></div>", unsafe_allow_html=True)
            c2.markdown("<div class='metric-card'><div class='label'>Top-k direct chunks</div><div class='value'>" + str(top_k) + "</div></div>", unsafe_allow_html=True)
            c3.markdown("<div class='metric-card'><div class='label'>Relation types</div><div class='value'>" + (", ".join(relation_types_list) if relation_types_list else "ALL") + "</div></div>", unsafe_allow_html=True)
            c4.markdown("<div class='metric-card'><div class='label'>Doc mở rộng tối đa</div><div class='value'>" + str(max_hop_documents) + "</div></div>", unsafe_allow_html=True)

            st.dataframe(
                summary_df.style.format({"hops": lambda x: f"{int(x)}"}),
                use_container_width=True,
            )

            st.subheader("Chi tiết từng cấu hình")
            for item in results:
                with st.expander(f"Hops = {item['hops']}", expanded=(item["hops"] == max(compare_hops))):
                    col_a, col_b, col_c, col_d = st.columns(4)
                    col_a.metric("Seed docs", item["seed_documents"])
                    col_b.metric("Direct chunks", item["direct_chunks"])
                    col_c.metric("Hop documents", item["hop_documents"])
                    col_d.metric("Hop chunks", item["hop_chunks"])

                    retrieval_result = item["retrieval_result"]
                    direct_df = pd.DataFrame(retrieval_result.get("direct_chunks", []))
                    if not direct_df.empty:
                        direct_df = direct_df[["document_id", "document_title", "chunk_id", "chunk_type", "score"]]
                        st.write("Direct chunks")
                        st.dataframe(direct_df.head(max_direct_chunks), use_container_width=True)
                    else:
                        st.info("Không có direct chunk nào được tìm thấy.")

                    hop_df = pd.DataFrame(retrieval_result.get("hop_documents", []))
                    if not hop_df.empty:
                        hop_df = hop_df[["document_id", "document_title", "min_hop"]]
                        st.write("Expanded documents (multi-hop)")
                        st.dataframe(hop_df, use_container_width=True)
                    else:
                        st.info("Không có tài liệu mở rộng nào cho cấu hình này.")

                    hop_chunks_df = pd.DataFrame(retrieval_result.get("hop_chunks", []))
                    if not hop_chunks_df.empty:
                        hop_chunks_df = hop_chunks_df[["document_id", "document_title", "chunk_id", "chunk_type"]]
                        st.write("Hop chunks")
                        st.dataframe(hop_chunks_df.head(max_hop_chunks), use_container_width=True)
                    else:
                        st.info("Không có chunk nào từ tài liệu mở rộng.")

                    st.write("Câu trả lời")
                    st.markdown(item["answer"] or "Không có câu trả lời.")

        except Exception as exc:  # pragma: no cover - UI error handling
            st.error(f"Lỗi khi chạy pipeline: {type(exc).__name__}: {exc}")
        finally:
            retriever.close()

st.info("Mẹo: nếu Neo4j chưa chạy, hãy đảm bảo database kb-hops đang online trên localhost:7687.")
