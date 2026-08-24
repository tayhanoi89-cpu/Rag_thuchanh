"""BUỔI 16: RAG Evaluation Dashboard (Ragas Evaluation Viewer & Interactive Benchmark)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Buổi 16 — RAG Evaluation Dashboard",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

PROJECT_ROOT = Path(__file__).resolve().parent
EVAL_DIR = PROJECT_ROOT / "data" / "eval"
QA_PATH = EVAL_DIR / "qa_dataset.csv"
RESULTS_PATH = EVAL_DIR / "evaluation_results.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "ragas_evaluation_report.md"

# Custom CSS for rich aesthetics
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4F46E5, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        margin: 6px 0;
    }
    .metric-status-pass {
        color: #10B981;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .metric-status-warn {
        color: #F59E0B;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-hr {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-risk {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-common {
        background-color: #F1F5F9;
        color: #334155;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> tuple[pd.DataFrame | None, pd.DataFrame | None, str]:
    qa_df = pd.read_csv(QA_PATH) if QA_PATH.exists() else None
    res_df = pd.read_csv(RESULTS_PATH) if RESULTS_PATH.exists() else None
    report_text = REPORT_PATH.read_text(encoding="utf-8") if REPORT_PATH.exists() else ""
    return qa_df, res_df, report_text


qa_df, res_df, report_text = load_data()

# Sidebar
with st.sidebar:
    st.image("https://raw.githubusercontent.com/explodinggradients/ragas/main/docs/static/imgs/logo.png", width=180)
    st.markdown("### ⚙️ Cấu hình & Thông tin")
    st.markdown(
        """
        - **Khóa học**: Graph RAG Advanced
        - **Bài thực hành**: Buổi 16
        - **Mô hình Pipeline**: `Qwen/Qwen3.5-9B:deepinfra`
        - **Mô hình Judger**: `openai/gpt-oss-20b:deepinfra`
        - **Khung đánh giá**: Ragas Framework
        """
    )
    st.divider()
    if st.button("🔄 Tải lại dữ liệu (Reload)"):
        st.cache_data.clear()
        st.rerun()

# Main Header
st.markdown('<div class="main-header">⚖️ BUỔI 16 — RAG EVALUATION DASHBOARD</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Hệ thống đánh giá hiệu năng tự động RAG Pipeline (Context Precision, Context Recall, Faithfulness, Answer Relevancy) bằng Ragas.</div>',
    unsafe_allow_html=True,
)

if res_df is None or res_df.empty:
    st.warning("⚠️ Chưa tìm thấy tệp dữ liệu kết quả `evaluation_results.csv`. Hãy chạy tập lệnh `evaluate_rag_pipeline.py` trước.")
    st.stop()

# 1. Summary Metrics KPIs
avg_prec = float(res_df["context_precision"].mean())
avg_rec = float(res_df["context_recall"].mean())
avg_faith = float(res_df["faithfulness"].mean())
avg_rel = float(res_df["answer_relevancy"].mean())

col1, col2, col3, col4 = st.columns(4)

with col1:
    status_cls = "metric-status-pass" if avg_prec >= 0.7 else "metric-status-warn"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">🎯 Context Precision</div>
            <div class="metric-value" style="color: #4F46E5;">{avg_prec:.3f}</div>
            <div class="{status_cls}">{'✓ Đạt chuẩn (≥ 0.70)' if avg_prec >= 0.7 else '⚠️ Cần cải thiện (< 0.70)'}</div>
            <small style="color: #94A3B8;">Đo vị trí xếp hạng tài liệu đúng</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    status_cls = "metric-status-pass" if avg_rec >= 0.7 else "metric-status-warn"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">🔍 Context Recall</div>
            <div class="metric-value" style="color: #06B6D4;">{avg_rec:.3f}</div>
            <div class="{status_cls}">{'✓ Đạt chuẩn (≥ 0.70)' if avg_rec >= 0.7 else '⚠️ Cần cải thiện (< 0.70)'}</div>
            <small style="color: #94A3B8;">Độ phủ thông tin đối chiếu Ground Truth</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    status_cls = "metric-status-pass" if avg_faith >= 0.8 else "metric-status-warn"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">🛡️ Faithfulness</div>
            <div class="metric-value" style="color: #10B981;">{avg_faith:.3f}</div>
            <div class="{status_cls}">{'✓ Đạt chuẩn (≥ 0.80)' if avg_faith >= 0.8 else '⚠️ Cần cải thiện (< 0.80)'}</div>
            <small style="color: #94A3B8;">Độ trung thực, không bịa đặt (Hallucination)</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    status_cls = "metric-status-pass" if avg_rel >= 0.8 else "metric-status-warn"
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">💬 Answer Relevancy</div>
            <div class="metric-value" style="color: #8B5CF6;">{avg_rel:.3f}</div>
            <div class="{status_cls}">{'✓ Đạt chuẩn (≥ 0.80)' if avg_rel >= 0.8 else '⚠️ Cần cải thiện (< 0.80)'}</div>
            <small style="color: #94A3B8;">Độ khớp giữa câu hỏi và câu trả lời</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Phân tích & Biểu đồ",
    "🔍 Chi tiết từng câu hỏi",
    "🎯 Golden Dataset (20 câu)",
    "⚠️ Phân tích lỗi (< 0.70)",
    "📄 Báo cáo chi tiết Markdown",
])

# TAB 1: Visualizations
with tab1:
    st.subheader("📈 Phân bố điểm số theo Lĩnh vực & Độ khó")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Điểm trung bình theo Lĩnh vực (Usecase)**")
        usecase_metrics = res_df.groupby("usecase")[["context_precision", "context_recall", "faithfulness", "answer_relevancy"]].mean()
        st.bar_chart(usecase_metrics, height=320)

    with c2:
        st.markdown("**Điểm trung bình theo Độ khó (Difficulty)**")
        diff_order = ["easy", "medium", "hard"]
        diff_metrics = res_df.groupby("difficulty")[["context_precision", "context_recall", "faithfulness", "answer_relevancy"]].mean().reindex(diff_order)
        st.bar_chart(diff_metrics, height=320)

# TAB 2: Detailed Question Explorer
with tab2:
    st.subheader("🔍 Danh sách đánh giá chi tiết từng câu hỏi")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_usecase = st.multiselect("Lọc theo Lĩnh vực (Usecase):", options=sorted(res_df["usecase"].unique()), default=sorted(res_df["usecase"].unique()))
    with col_f2:
        selected_diff = st.multiselect("Lọc theo Độ khó (Difficulty):", options=sorted(res_df["difficulty"].unique()), default=sorted(res_df["difficulty"].unique()))

    filtered_df = res_df[res_df["usecase"].isin(selected_usecase) & res_df["difficulty"].isin(selected_diff)]
    
    st.dataframe(
        filtered_df[["question_id", "usecase", "difficulty", "question", "context_precision", "context_recall", "faithfulness", "answer_relevancy"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 🔎 Chi tiết ngữ cảnh & câu trả lời từng câu:")
    for _, row in filtered_df.iterrows():
        with st.expander(f"📌 [{row['question_id']}] - {row['question']} ({row['usecase']} | {row['difficulty']})"):
            c_left, c_right = st.columns([3, 2])
            with c_left:
                st.markdown(f"**🎯 Đáp án chuẩn (Ground Truth):**\n> {row['ground_truth']}")
                st.markdown(f"**🤖 Câu trả lời RAG sinh ra (Answer):**\n```text\n{row['answer']}\n```")
                
                try:
                    contexts = json.loads(row["contexts"]) if isinstance(row["contexts"], str) and row["contexts"].startswith("[") else [str(row["contexts"])]
                    st.markdown(f"**📚 Ngữ cảnh đã truy xuất (Retrieved Contexts - {len(contexts)} chunks):**")
                    for c_idx, ctx in enumerate(contexts, 1):
                        st.text_area(f"Chunk #{c_idx}", value=ctx[:500] + ("..." if len(ctx) > 500 else ""), height=100, key=f"ctx_{row['question_id']}_{c_idx}")
                except Exception:
                    st.write(row.get("contexts", ""))

            with c_right:
                st.markdown("**Điểm số Ragas chi tiết:**")
                st.write(f"• Context Precision: `{row['context_precision']}`")
                st.progress(float(row['context_precision']))
                st.write(f"• Context Recall: `{row['context_recall']}`")
                st.progress(float(row['context_recall']))
                st.write(f"• Faithfulness: `{row['faithfulness']}`")
                st.progress(float(row['faithfulness']))
                st.write(f"• Answer Relevancy: `{row['answer_relevancy']}`")
                st.progress(float(row['answer_relevancy']))

# TAB 3: Golden Dataset
with tab3:
    st.subheader("🎯 Bộ câu hỏi & đáp án chuẩn (Golden Dataset)")
    if qa_df is not None:
        st.dataframe(qa_df, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa tìm thấy `qa_dataset.csv`.")

# TAB 4: Failure Cases Analysis
with tab4:
    st.subheader("⚠️ Phân tích các trường hợp điểm số thấp (< 0.70)")
    low_cases = res_df[
        (res_df["context_precision"] < 0.70)
        | (res_df["context_recall"] < 0.70)
        | (res_df["faithfulness"] < 0.80)
        | (res_df["answer_relevancy"] < 0.80)
    ]
    if not low_cases.empty:
        st.warning(f"Tìm thấy {len(low_cases)} câu hỏi cần xem xét tối ưu hóa:")
        st.dataframe(
            low_cases[["question_id", "usecase", "difficulty", "question", "context_precision", "context_recall", "faithfulness", "answer_relevancy"]],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown(
            """
            ### 💡 Đề xuất phương án tối ưu kỹ thuật:
            1. **Nếu Context Precision < 0.70**:
               - Tinh chỉnh trọng số RRF giữa BM25 và Dense Search.
               - Sử dụng Cross-Encoder Reranker (`BAAI/bge-reranker-v2-m3`) để đưa đúng tài liệu cốt lõi lên Rank #1.
            2. **Nếu Context Recall < 0.70**:
               - Tăng `top_k` từ 5 lên 8 hoặc 10.
               - Bổ sung Query Expansion với từ đồng nghĩa và từ viết tắt.
            3. **Nếu Faithfulness < 0.80**:
               - Ép buộc System Prompt khắt khe hơn: chỉ trả lời dựa vào ngữ cảnh, không suy diễn kiến thức bên ngoài.
            4. **Nếu Answer Relevancy < 0.80**:
               - Yêu cầu câu trả lời trực diện, súc tích, đi thẳng vào trọng tâm câu hỏi.
            """
        )
    else:
        st.success("🎉 Tất cả các câu hỏi đều đạt điểm xuất sắc trên ngưỡng chuẩn khuyến nghị!")

# TAB 5: Markdown Report
with tab5:
    st.subheader("📄 Báo cáo đánh giá Markdown")
    if report_text:
        st.markdown(report_text)
    else:
        st.info("Chưa tìm thấy tệp `ragas_evaluation_report.md`.")
