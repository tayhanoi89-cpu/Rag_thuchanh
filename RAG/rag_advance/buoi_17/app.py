"""Secure RAG & Compliance AI Assistant - Buổi 17 Streamlit App.

Reuses:
- scripts.internal_lookup.InternalPolicyLookupEngine
- scripts.compliance_gap.ComplianceGapChecker
- scripts.audit_logger.AuditLogger

Features:
- RBAC role-switching in Sidebar
- Banner: 'Demo đào tạo — kết quả AI cần kiểm toán viên xác minh.'
- Tab 1: Tra cứu quy định nội bộ (Pre-filtering RBAC + Grounded Gen + Zero Leaks)
- Tab 2: Compliance Gap Checker (External NHNN vs Internal Policy + Human-in-the-loop)
- Tab 3: Audit Trail viewer (Sanitized logs, role-scoped)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Setup path
APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_logger import AuditLogger
from scripts.compliance_gap import ComplianceGapChecker
from scripts.internal_lookup import InternalPolicyLookupEngine

# Set Page Config
st.set_page_config(
    page_title="Secure RAG & Compliance — Buổi 17",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Banking & Compliance Grade UI
st.markdown(
    """
    <style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #4B5563;
        margin-bottom: 1rem;
    }
    .training-banner {
        background: linear-gradient(90deg, #FEF3C7 0%, #FDE68A 100%);
        border-left: 5px solid #F59E0B;
        padding: 10px 16px;
        border-radius: 6px;
        color: #92400E;
        font-weight: 600;
        margin-bottom: 20px;
        font-size: 0.95rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .badge-allow {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-deny {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-review {
        background-color: #FEF08A;
        color: #854D0E;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
st.markdown('<div class="main-header">🏦 SECURE RAG & AI COMPLIANCE ENGINE</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Hệ thống Trợ lý Tra cứu Quy định & Rà soát Khoảng cách Tuân thủ Ngân hàng (Buổi 17)</div>', unsafe_allow_html=True)

# Mandatory Training Banner
st.markdown(
    '<div class="training-banner">⚠️ <b>DEMO ĐÀO TẠO</b> — Kết quả phân tích của AI mang tính chất khuyến nghị và cần được kiểm toán viên / chuyên viên pháp chế xác minh.</div>',
    unsafe_allow_html=True,
)


# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bank-building.png", width=64)
    st.header("🔐 Phiên làm việc (Session)")
    
    user_id = st.text_input("User ID", value="auditor_demo_01")
    
    user_role = st.selectbox(
        "Vai trò người dùng (RBAC Role)",
        options=["Risk_Manager", "Admin", "Staff", "HR", "Guest", "Unknown_Role"],
        index=0,
        help="Vai trò quyết định phạm vi tài liệu được phép truy xuất trước khi tìm kiếm.",
    )
    
    st.divider()
    st.subheader("🌐 Trạng thái Hạ tầng")
    st.markdown("🟢 **LLM Engine**: `gemini-3.6-flash` (Active)")
    st.markdown("🟢 **RBAC Adapter**: `Pre-filtering` (15 Chunks)")

    # Dynamic Neo4j Connectivity Probe
    def check_neo4j_live_status() -> tuple[bool, str]:
        from neo4j import GraphDatabase
        uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        try:
            with GraphDatabase.driver(uri, auth=(user, password)) as driver:
                driver.verify_connectivity()
                return True, "Connected (Cấu trúc CONTAINS — Không dùng cho Gap)"
        except Exception:
            return False, "Offline (Không khả dụng)"

    is_neo4j_online, neo4j_msg = check_neo4j_live_status()
    if is_neo4j_online:
        st.markdown(f"🟢 **Neo4j Graph**: `{neo4j_msg}`")
    else:
        st.markdown(f"🔴 **Neo4j Graph**: `{neo4j_msg}`")
    
    st.divider()
    st.caption("Khóa học: RAG Nâng cao trong Ngành Ngân hàng & Tài chính")


# Initialize Engines in Session State
if "lookup_engine" not in st.session_state:
    try:
        st.session_state.lookup_engine = InternalPolicyLookupEngine()
    except Exception as e:
        st.session_state.lookup_engine = None
        st.error(f"Lỗi khởi tạo Lookup Engine: {e}")

if "gap_checker" not in st.session_state:
    try:
        st.session_state.gap_checker = ComplianceGapChecker()
    except Exception as e:
        st.session_state.gap_checker = None
        st.error(f"Lỗi khởi tạo Compliance Gap Checker: {e}")


# Tabs Layout
tab_lookup, tab_gap, tab_audit = st.tabs([
    "🔍 1. TRA CỨU QUY ĐỊNH",
    "⚖️ 2. COMPLIANCE GAP CHECKER",
    "📋 3. AUDIT TRAIL LOGS",
])


# ==============================================================================
# TAB 1: TRA CỨU QUY ĐỊNH NỘI BỘ
# ==============================================================================
with tab_lookup:
    st.subheader("Trợ lý AI Tra cứu Văn bản & Quy định Ngân hàng")
    st.write("Hệ thống áp dụng **RBAC Pre-filtering** để bảo đảm người dùng chỉ nhận được câu trả lời từ tài liệu được cấp quyền.")

    sample_questions = [
        "Quy định về việc giao nhận, bảo quản và vận chuyển tiền mặt, tài sản quý, giấy tờ có giá trong ngành ngân hàng?",
        "Theo Luật Hợp tác xã số 17/2023/QH15, việc góp vốn điều lệ và quyền của thành viên hợp tác xã được quy định như thế nào?",
        "Quy định tỷ lệ an toàn vốn tối thiểu (CAR) đối với ngân hàng thương mại theo Thông tư 41/2016/TT-NHNN?",
    ]
    
    selected_sample = st.selectbox("Chọn câu hỏi mẫu hoặc nhập câu hỏi bên dưới:", ["-- Tự nhập câu hỏi --"] + sample_questions)
    
    default_q = "" if selected_sample == "-- Tự nhập câu hỏi --" else selected_sample
    question_input = st.text_area("Nội dung câu hỏi tra cứu:", value=default_q, height=90, placeholder="Nhập câu hỏi quy định cần tra cứu...")
    
    col_k, col_btn = st.columns([2, 1])
    with col_k:
        top_k = st.slider("Số lượng tài liệu truy xuất (Top-K):", min_value=1, max_value=5, value=3)
    with col_btn:
        st.write("")
        st.write("")
        run_lookup = st.button("🚀 Thực hiện Tra cứu", type="primary", use_container_width=True)

    if run_lookup and question_input.strip():
        if st.session_state.lookup_engine is None:
            st.error("Engine chưa được khởi tạo. Vui lòng kiểm tra API Key trong .env.")
        else:
            with st.spinner("Đang thực hiện RBAC Pre-filter và truy vấn LLM..."):
                res = st.session_state.lookup_engine.query_policy(
                    question=question_input.strip(),
                    user_role=user_role,
                    user_id_demo=user_id,
                    top_k=top_k,
                )
                
                st.divider()
                st.markdown("### 📝 Kết quả Tra cứu")
                
                # Metrics Row
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Request ID", res["request_id"])
                with m2:
                    st.metric("Vai trò", res["user_role"])
                with m3:
                    is_allowed = len(res["citations"]) > 0
                    st.markdown(
                        f"**Quyết định truy cập:**<br><span class='badge-{'allow' if is_allowed else 'deny'}'>{'ALLOW' if is_allowed else 'DENIED / NO ACCESS'}</span>",
                        unsafe_allow_html=True,
                    )
                with m4:
                    st.metric("Phạm vi truy cập", res["access_scope"].split()[1] if " " in res["access_scope"] else res["access_scope"])

                # Answer Box
                st.markdown("#### 💬 Câu trả lời từ AI:")
                st.info(res["answer"])

                # Evidence & Citations (Only display if permitted)
                if res["citations"]:
                    st.markdown("#### 📚 Trích dẫn & Bằng chứng pháp lý (Citations):")
                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        st.markdown(f"- **Văn bản trích dẫn**: `{', '.join(res['citations'])}`")
                    with c_col2:
                        st.markdown(f"- **Chunk IDs**: `{', '.join(res['chunk_ids'])}`")
                else:
                    st.warning("🔒 Không có trích dẫn hoặc tài liệu nào được hiển thị do giới hạn quyền truy cập RBAC.")


# ==============================================================================
# TAB 2: COMPLIANCE GAP CHECKER
# ==============================================================================
with tab_gap:
    st.subheader("⚖️ AI Compliance Gap Checker")
    st.write("Đối chiếu các yêu cầu pháp lý từ Ngân hàng Nhà nước (NHNN) với Quy chế/Quy định nội bộ của tổ chức tín dụng.")

    sample_reqs = [
        {
            "doc_id": "44209",
            "chunk_id": "44209__full",
            "citation": "01/2014/TT-NHNN",
            "text": "Quy định tổ chức tín dụng phải thực hiện giao nhận, kiểm đếm bó/túi tiền nguyên niêm phong kẹp chì và bảo quản nghiêm ngặt trong kho tiền.",
        },
        {
            "doc_id": "117310",
            "chunk_id": "117310__full",
            "citation": "41/2016/TT-NHNN",
            "text": "Quy định tỷ lệ an toàn vốn tối thiểu (CAR) của ngân hàng thương mại phải duy trì tối thiểu 8% theo phương pháp tiêu chuẩn.",
        },
        {
            "doc_id": "174218",
            "chunk_id": "174218__full",
            "citation": "62/2024/TT-NHNN",
            "text": "Quy định điều kiện, hồ sơ, thủ tục chấp thuận việc tổ chức lại ngân hàng thương mại và tổ chức tín dụng phi ngân hàng.",
        },
    ]

    selected_req_idx = st.selectbox(
        "Chọn yêu cầu pháp lý mẫu từ NHNN:",
        options=range(len(sample_reqs)),
        format_func=lambda i: f"[{sample_reqs[i]['citation']}] {sample_reqs[i]['text'][:90]}...",
    )
    
    current_req = sample_reqs[selected_req_idx]
    
    st.markdown(
        f"""
        <div class="metric-card">
            <b>Yêu cầu pháp lý bên ngoài (External Requirement):</b><br>
            • <b>Văn bản ban hành:</b> {current_req['citation']} (Doc ID: {current_req['doc_id']})<br>
            • <b>Nội dung quy định:</b> {current_req['text']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🔎 Kiểm tra Khoảng cách Tuân thủ (Run Gap Analysis)", type="primary"):
        if st.session_state.gap_checker is None:
            st.error("Gap Checker Engine chưa được khởi tạo.")
        else:
            with st.spinner("Đang rà soát và đối chiếu bằng chứng tuân thủ..."):
                gap_res = st.session_state.gap_checker.analyze_requirement(
                    external_requirement=current_req["text"],
                    external_doc_id=current_req["doc_id"],
                    external_chunk_id=current_req["chunk_id"],
                    external_citation=current_req["citation"],
                    user_role=user_role,
                    user_id=user_id,
                )
                
                st.divider()
                st.markdown("### 📊 Kết quả Phân tích Khoảng cách Tuân thủ (Compliance Gap)")
                
                g1, g2, g3, g4 = st.columns(4)
                with g1:
                    st.metric("Gap ID", gap_res["gap_id"])
                with g2:
                    st.metric("External Citation", gap_res["external_citation"])
                with g3:
                    st.markdown(
                        f"**Phân loại (Classification):**<br><span class='badge-review'>{gap_res['classification']}</span>",
                        unsafe_allow_html=True,
                    )
                with g4:
                    st.markdown(
                        f"**Trạng thái thẩm định:**<br><span class='badge-review'>{gap_res['review_status']}</span>",
                        unsafe_allow_html=True,
                    )

                st.markdown(f"**Lý do phân loại:** {gap_res['reason']}")
                st.markdown(f"**Bằng chứng nội bộ (Internal Evidence):** `{gap_res['internal_evidence']}`")

                # Results Table View
                st.markdown("#### 📋 Bảng tổng hợp Schema Tuân thủ (14 Fields):")
                df_single = pd.DataFrame([gap_res])
                st.dataframe(df_single, use_container_width=True)

    # Load Full Pre-computed Gap Analysis Results
    csv_results_path = APP_DIR / "outputs" / "compliance_gap_results.csv"
    if csv_results_path.exists():
        st.divider()
        st.markdown("### 📂 Bảng Kết quả Toàn bộ Kiểm định (Batch Compliance Gap Results)")
        try:
            df_all = pd.read_csv(csv_results_path)
            st.dataframe(df_all, use_container_width=True)
        except Exception as ex:
            st.caption(f"Không thể tải CSV lịch sử: {ex}")


# ==============================================================================
# TAB 3: AUDIT TRAIL LOGS
# ==============================================================================
with tab_audit:
    st.subheader("📋 Nhật ký Kiểm toán (Audit Trail Logs)")
    st.write("Toàn bộ các thao tác tra cứu và kiểm định tuân thủ đều được ghi nhận bất biến theo chuẩn ISO-8601 UTC.")

    log_file = APP_DIR / "outputs" / "audit_log.jsonl"
    if not log_file.exists():
        st.info("Chưa có sự kiện audit nào được ghi nhận.")
    else:
        events = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
        
        if not events:
            st.info("File audit log trống.")
        else:
            events.reverse()  # Show newest first
            st.success(f"Tổng số sự kiện kiểm toán đã ghi nhận: **{len(events)}** sự kiện.")
            
            # Convert to DataFrame for clean display
            df_logs = pd.DataFrame(events)
            
            # Ensure sensitive columns are omitted
            safe_cols = [
                col for col in [
                    "timestamp_utc",
                    "request_id",
                    "user_id_demo",
                    "user_role",
                    "action",
                    "query",
                    "retrieval_method",
                    "citation_ids",
                    "rbac_filtered_count",
                    "status",
                ]
                if col in df_logs.columns
            ]
            
            st.dataframe(df_logs[safe_cols], use_container_width=True, height=400)
            
            with st.expander("🔍 Xem chi tiết sự kiện mới nhất (Raw JSON)"):
                st.json(events[0])
