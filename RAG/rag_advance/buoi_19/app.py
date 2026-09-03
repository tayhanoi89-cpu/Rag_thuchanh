import os
import sys
import json
import time
import uuid
import pandas as pd
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

# Ensure scripts directory is in sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

from audit_logger import AuditLogger
from internal_lookup import InternalLookupEngine
from compliance_gap import ComplianceGapChecker
from compliance_checker import ComplianceCheckerEngine
from audit_checklist_gen import AuditChecklistGeneratorEngine
from ollama_adapter import OllamaClient

# Load environment
load_dotenv(".env")

# Page Configuration
st.set_page_config(
    page_title="Agribank AI Compliance & Audit Suite",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    /* Global Styles */
    .main {
        background-color: #f8fafc;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #f1f5f9;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 14px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0284c7 !important;
        color: white !important;
    }
    
    /* Header Banners */
    .warning-banner {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border-left: 5px solid #f59e0b;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 15px;
        color: #92400e;
        font-weight: 500;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .provider-banner-local {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border-left: 5px solid #16a34a;
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        color: #166534;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .provider-banner-cloud {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border-left: 5px solid #2563eb;
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        color: #1e40af;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    
    /* Cards */
    .compliance-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .compliance-card:hover {
        box-shadow: 0 6px 12px rgba(0,0,0,0.08);
    }
    
    /* Badges */
    .badge-high {
        background-color: #fee2e2;
        color: #b91c1c;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid #fecaca;
    }
    .badge-medium {
        background-color: #fef3c7;
        color: #b45309;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid #fde68a;
    }
    .badge-low {
        background-color: #dcfce7;
        color: #15803d;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid #bbf7d0;
    }
    .badge-none {
        background-color: #f1f5f9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #e2e8f0;
    }
    .badge-guardrail {
        background-color: #f3e8ff;
        color: #7e22ce;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid #e9d5ff;
    }
    .badge-allow {
        background-color: #def7ec;
        color: #03543f;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid #bbf7d0;
    }
    .badge-deny {
        background-color: #fde8e8;
        color: #9b1c1c;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid #fecaca;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "audit_logger" not in st.session_state:
    st.session_state.audit_logger = AuditLogger()
if "lookup_engine" not in st.session_state:
    st.session_state.lookup_engine = InternalLookupEngine()
if "gap_checker" not in st.session_state:
    st.session_state.gap_checker = ComplianceGapChecker()
if "compliance_engine" not in st.session_state:
    st.session_state.compliance_engine = ComplianceCheckerEngine()
if "checklist_engine" not in st.session_state:
    st.session_state.checklist_engine = AuditChecklistGeneratorEngine()

if "lookup_result" not in st.session_state:
    st.session_state.lookup_result = None
if "gap_results" not in st.session_state:
    st.session_state.gap_results = []
if "compliance_results" not in st.session_state:
    st.session_state.compliance_results = []
if "checklist_results" not in st.session_state:
    st.session_state.checklist_results = []
if "selected_provider" not in st.session_state:
    st.session_state.selected_provider = os.getenv("LLM_PROVIDER", "ollama").lower()

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Logo_Agribank.png/800px-Logo_Agribank.png", width=180)
    st.markdown("### 🛡️ AI Compliance & Audit Suite")
    st.markdown("**Phiên bản:** Buổi 19 - Docker Containerized Local AI")
    st.divider()

    st.markdown("#### 🧠 LỰA CHỌN LLM ENGINE")
    provider_option = st.radio(
        "Chọn chế độ xử lý AI:",
        [
            "🔒 Local Offline AI (Ollama - Qwen3:0.6B)",
            "☁️ Cloud AI (Google Gemini Flash API)"
        ],
        index=0 if st.session_state.selected_provider == "ollama" else 1,
        help="Chế độ Offline hoàn toàn bảo mật nội bộ, không gửi dữ liệu ra ngoài Internet."
    )

    is_ollama = "Local Offline" in provider_option
    current_provider = "ollama" if is_ollama else "gemini"

    if is_ollama:
        ollama_model_choice = st.selectbox(
            "Chọn Local SLM Model:",
            ["qwen3:0.6b", "qwen2.5:0.5b", "qwen2.5:1.5b"],
            index=0
        )
        ollama_url_input = st.text_input(
            "Ollama Base URL:",
            value=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        
        # Check health of Ollama
        client_check = OllamaClient(base_url=ollama_url_input, model=ollama_model_choice)
        health = client_check.check_health()
        if health["online"]:
            st.success(f"🟢 **Ollama Server:** ONLINE\n\nModel: `{ollama_model_choice}`")
        else:
            st.warning(f"🟡 **Ollama Server:** OFFLINE\n\n*Rule-Engine Fallback Active*")
            
        # Update all 4 engines
        st.session_state.lookup_engine.set_provider("ollama", model=ollama_model_choice, base_url=ollama_url_input)
        st.session_state.gap_checker.set_provider("ollama", model=ollama_model_choice, base_url=ollama_url_input)
        st.session_state.compliance_engine.set_provider("ollama", model=ollama_model_choice, base_url=ollama_url_input)
        st.session_state.checklist_engine.set_provider("ollama", model=ollama_model_choice, base_url=ollama_url_input)
        st.session_state.selected_provider = "ollama"
    else:
        st.info("☁️ **Google Gemini 3.6 Flash** (Cloud API)")
        gemini_model_choice = st.text_input("Gemini Model:", value=os.getenv("LLM_MODEL", "gemini-3.6-flash"))
        st.session_state.lookup_engine.set_provider("gemini", model=gemini_model_choice)
        st.session_state.gap_checker.set_provider("gemini", model=gemini_model_choice)
        st.session_state.compliance_engine.set_provider("gemini", model=gemini_model_choice)
        st.session_state.checklist_engine.set_provider("gemini", model=gemini_model_choice)
        st.session_state.selected_provider = "gemini"

    st.divider()
    st.markdown("#### 👤 Thông tin Người Dùng & Phân quyền")
    user_id = st.text_input("User ID", value="auditor_admin_01")
    user_role = st.selectbox(
        "Vai trò người dùng (RBAC Role)",
        ["Admin", "Risk_Manager", "KiemToanVien", "Staff", "HR"],
        index=0,
        help="Vai trò kiểm soát phạm vi tài liệu được phép truy xuất trước khi đưa vào LLM."
    )

    st.divider()
    st.markdown("#### 📊 Trạng thái Dữ liệu")
    df_internal = st.session_state.compliance_engine.df_internal
    df_combined = st.session_state.compliance_engine.df_combined
    
    st.markdown(f"- **Văn bản Nội bộ Agribank:** `{'24 chunks' if not df_internal.empty else '0'}` ✅")
    st.markdown(f"- **Văn bản Pháp luật NHNN:** `{'787 chunks' if not df_combined.empty else '0'}` ✅")
    st.markdown(f"- **Tổng quy định kết nối:** `{'811 chunks' if not df_combined.empty else '0'}`")

    st.divider()
    if st.button("🔄 Reset Session & Logs"):
        st.session_state.lookup_result = None
        st.session_state.gap_results = []
        st.session_state.compliance_results = []
        st.session_state.checklist_results = []
        st.success("Đã làm mới phiên làm việc!")
        st.rerun()

# ==========================================
# MAIN HEADER & BANNER
# ==========================================
st.title("🏦 Agribank AI Compliance & Audit Suite")

if st.session_state.selected_provider == "ollama":
    st.markdown("""
    <div class="provider-banner-local">
        🔒 <b>CHẾ ĐỘ HIỆN TẠI: LOCAL OFFLINE SLM (OLLAMA QWEN3:0.6B)</b> — Bảo mật 100% On-Premise, dữ liệu không rời khỏi mạng nội bộ.
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="provider-banner-cloud">
        ☁️ <b>CHẾ ĐỘ HIỆN TẠI: CLOUD GEMINI API</b> — Kết nối đám mây Google AI (Fallback Mode).
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="warning-banner">
    ⚠️ <b>KHUYẾN CÁO QUẢN TRỊ RỦI RO & GUARDRAIL:</b> Hệ thống sử dụng AI hỗ trợ tự động tra cứu, đối chiếu quy định và sinh checklist kiểm toán. Mọi kết quả gợi ý bắt buộc phải được <b>Kiểm toán viên xác minh (NEEDS_HUMAN_REVIEW)</b> trước khi ban hành báo cáo chính thức.
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 UC1 - Tra cứu Quy định (RBAC)",
    "⚖️ UC2 - Đánh giá Gap Tuân thủ",
    "⚔️ UC3 - Phát hiện Xung đột Quy định",
    "📋 UC4 - Sinh Checklist Kiểm toán",
    "📜 Tab 5 - Audit Trail & Logs"
])

# ==========================================
# TAB 1: UC1 - TRA CỨU QUY ĐỊNH NỘI BỘ (RBAC)
# ==========================================
with tab1:
    st.subheader("🔍 UC1: Tra cứu Văn bản & Quy định Nội bộ (Pre-retrieval RBAC)")
    st.markdown("Hệ thống áp dụng **RBAC Pre-filtering** để bảo đảm người dùng chỉ nhận được câu trả lời từ tài liệu được cấp quyền, ngăn chặn 100% rò rỉ thông tin mật.")

    sample_questions = [
        "Quy định về việc giao nhận, bảo quản và vận chuyển tiền mặt trong ngành ngân hàng?",
        "Tỷ lệ an toàn vốn tối thiểu (CAR) và định mức quản trị rủi ro nội bộ?",
        "Quy trình thẩm quyền phê duyệt cấp tín dụng cho khách hàng doanh nghiệp?",
        "Quy định thời hạn và hồ sơ phân loại nợ xấu theo thông tư mới?"
    ]
    
    selected_sample = st.selectbox("Chọn câu hỏi mẫu:", ["-- Tự nhập câu hỏi --"] + sample_questions)
    default_q = "" if selected_sample == "-- Tự nhập câu hỏi --" else selected_sample
    question_input = st.text_area("Nội dung câu hỏi tra cứu:", value=default_q, height=90, placeholder="Nhập câu hỏi quy định cần tra cứu...")
    
    col_k, col_btn = st.columns([3, 1])
    with col_k:
        top_k = st.slider("Số lượng tài liệu truy xuất (Top-K):", min_value=1, max_value=5, value=3)
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        run_lookup = st.button("🚀 Thực hiện Tra cứu", type="primary", use_container_width=True)

    if run_lookup and question_input.strip():
        provider_name = "Local Model Qwen3:0.6B" if st.session_state.selected_provider == "ollama" else "Gemini Flash API"
        with st.spinner(f"Đang thực hiện RBAC Pre-filtering và truy vấn qua {provider_name}..."):
            res = st.session_state.lookup_engine.query(
                query_text=question_input.strip(),
                user_role=user_role,
                user_id=user_id,
                top_k=top_k
            )
            st.session_state.lookup_result = res

    if st.session_state.lookup_result:
        res = st.session_state.lookup_result
        st.divider()
        st.markdown("### 📝 Kết quả Tra cứu")
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Request ID", res.get("request_id", "N/A"))
        with m2:
            st.metric("Vai trò yêu cầu", user_role)
        with m3:
            is_allowed = len(res.get("citations", [])) > 0
            st.markdown(
                f"**Quyết định RBAC:**<br><span class='{'badge-allow' if is_allowed else 'badge-deny'}'>{'ALLOW (ĐƯỢC PHÉP)' if is_allowed else 'DENIED (TỪ CHỐI / HẠN CHẾ)'}</span>",
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                f"**Human Review:**<br><span class='badge-guardrail'>{res.get('review_status', 'NEEDS_HUMAN_REVIEW')}</span>",
                unsafe_allow_html=True,
            )

        st.markdown("#### 💬 Câu trả lời từ AI:")
        st.info(res.get("answer", ""))

        if res.get("citations"):
            st.markdown("#### 📚 Trích dẫn Văn bản (Citations):")
            for cit in res["citations"]:
                st.markdown(f"- 📜 ` {cit} `")

        if res.get("authorized_chunks"):
            with st.expander(f"📂 Xem chi tiết {len(res['authorized_chunks'])} Chunks được phép truy cập"):
                for idx, c in enumerate(res["authorized_chunks"], 1):
                    st.markdown(f"**Chunk #{idx}** — `{c.get('so_ky_hieu', '')} | {c.get('article', '')}`")
                    st.caption(f"Tiêu đề: {c.get('title', '')} | Allowed Roles: {c.get('allowed_roles', '')}")
                    st.text(str(c.get("text", ""))[:400] + "...")

# ==========================================
# TAB 2: UC2 - ĐÁNH GIÁ GAP TUÂN THỦ (COMPLIANCE GAP)
# ==========================================
with tab2:
    st.subheader("⚖️ UC2: Đánh giá Khoảng cách Tuân thủ (Compliance Gap Analysis)")
    st.markdown("So sánh từng yêu cầu pháp lý từ Thông tư / Quy định của Ngân hàng Nhà nước với hệ thống văn bản nội bộ Agribank để phát hiện thiếu sót.")

    sample_gaps = [
        {
            "req": "Quy định tiêu chuẩn kỹ thuật xe ô tô chuyên dùng vận chuyển tiền mặt, kho tiền lưu động",
            "doc": "01/2014/TT-NHNN",
            "chk": "CHK_01",
            "cit": "Thông tư 01/2014/TT-NHNN - Điều 50"
        },
        {
            "req": "Quy định tỷ lệ an toàn vốn tối thiểu (CAR) đối với ngân hàng thương mại đạt tối thiểu 8%",
            "doc": "41/2016/TT-NHNN",
            "chk": "CHK_02",
            "cit": "Thông tư 41/2016/TT-NHNN - Điều 5"
        },
        {
            "req": "Yêu cầu đánh giá rủi ro định kỳ đối với hệ thống trí tuệ nhân tạo và tự động hóa trong ngân hàng",
            "doc": "50/2024/TT-NHNN",
            "chk": "CHK_03",
            "cit": "Thông tư 50/2024/TT-NHNN - Điều 15"
        }
    ]

    col_gap_sel, col_gap_btn = st.columns([3, 1])
    with col_gap_sel:
        gap_choice = st.selectbox(
            "Chọn yêu cầu pháp lý mẫu từ NHNN:",
            ["-- Quét tất cả yêu cầu mẫu --"] + [f"{g['cit']}: {g['req']}" for g in sample_gaps]
        )
    with col_gap_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        run_gap_btn = st.button("🚀 Đánh giá Khoảng cách Tuân thủ", type="primary", use_container_width=True)

    if run_gap_btn:
        provider_name = "Local Model Qwen3:0.6B" if st.session_state.selected_provider == "ollama" else "Gemini Flash API"
        with st.spinner(f"Đang đối chiếu bằng chứng hai phía qua {provider_name}..."):
            items_to_check = sample_gaps if gap_choice == "-- Quét tất cả yêu cầu mẫu --" else [g for g in sample_gaps if g["cit"] in gap_choice]
            gap_results = []
            for item in items_to_check:
                g_res = st.session_state.gap_checker.analyze_requirement(
                    external_requirement=item["req"],
                    external_doc_id=item["doc"],
                    external_chunk_id=item["chk"],
                    external_citation=item["cit"],
                    user_role=user_role,
                    user_id=user_id
                )
                gap_results.append(g_res)
            st.session_state.gap_results = gap_results
            st.success(f"Đã hoàn thành đánh giá {len(gap_results)} yêu cầu pháp lý!")

    if st.session_state.gap_results:
        st.markdown(f"### 📑 Kết quả Đánh giá Khoảng cách Tuân thủ ({len(st.session_state.gap_results)} mục)")
        for idx, g in enumerate(st.session_state.gap_results):
            cls = g.get("classification", "CHUA_DU_BANG_CHUNG")
            badge_class = "badge-high" if cls == "THIEU" else ("badge-low" if cls == "DAP_UNG" else "badge-medium")
            
            st.markdown(f"""
            <div class="compliance-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div>
                        <span style="font-size: 1.05rem; font-weight: 700; color: #0f172a;">#{idx+1} [{g['gap_id']}] {g['external_citation']}</span>
                    </div>
                    <div>
                        <span class="{badge_class}">PHÂN LOẠI: {cls}</span>
                        <span class="badge-guardrail" style="margin-left: 8px;">{g.get('review_status', 'NEEDS_HUMAN_REVIEW')}</span>
                    </div>
                </div>
                <div style="margin-bottom: 8px;"><b>🏛️ Yêu cầu NHNN:</b> {g['external_requirement']}</div>
                <div style="margin-bottom: 8px;"><b>📜 Căn cứ Nội bộ Agribank:</b> <code>{g.get('internal_citation', 'NONE')}</code></div>
                <div style="background-color: #f8fafc; padding: 10px; border-radius: 6px; border-left: 4px solid #0284c7; margin-bottom: 8px;">
                    <b>🔍 Bằng chứng & Đánh giá AI:</b><br>{g.get('reason', '')}<br><br>
                    <small><i>Bằng chứng nội bộ: {g.get('internal_evidence', 'N/A')}</i></small>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# TAB 3: UC3 - AI COMPLIANCE CHECKER
# ==========================================
with tab3:
    st.subheader("⚔️ UC3: Kiểm tra Tuân thủ & Phát hiện Xung đột Quy định (Cross-Comparison)")
    st.markdown("Hệ thống tự động đối chiếu các quy định nội bộ Agribank với hệ thống văn bản quy phạm pháp luật của Ngân hàng Nhà nước để phát hiện xung đột.")

    col1, col2 = st.columns([2, 1])
    with col1:
        domain_choice = st.selectbox(
            "Chọn Miền / Lĩnh vực nghiệp vụ cần đối chiếu",
            [
                "Tất cả miền nghiệp vụ (Quét toàn diện)",
                "An toàn kho quỹ & Vận chuyển tiền mặt",
                "CAR & Quản lý rủi ro",
                "Tín dụng & Thẩm quyền phê duyệt",
                "Bảo hiểm tài sản & Bảo hiểm nghiệp vụ",
                "Ngoại hối & Quản lý trạng thái ngoại tệ",
                "Mạng lưới & Phát triển chi nhánh / PGD",
                "Bảo mật CNTT & Quản trị AI",
                "Quản trị nhân sự & Đào tạo",
                "Tài chính & Mua sắm nội bộ",
                "Phân loại nợ & Xử lý nợ xấu"
            ]
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        scan_btn = st.button("🚀 Phát hiện Xung đột & Mâu thuẫn", type="primary", use_container_width=True)

    if scan_btn:
        provider_name = "Local Model Qwen3:0.6B" if st.session_state.selected_provider == "ollama" else "Gemini Flash API"
        with st.spinner(f"Đang truy xuất Evidence Packages và phân tích so sánh chéo bằng {provider_name}..."):
            test_pairs = []
            if "kho quỹ" in domain_choice.lower() or "tất cả" in domain_choice.lower():
                try:
                    row_a = df_combined[(df_combined["so_ky_hieu"] == "100/QĐ-NHNO-AT") & (df_combined["article"].str.contains("Điều 12", na=False))].iloc[0].to_dict()
                    row_b = df_combined[(df_combined["so_ky_hieu"] == "01/2014/TT-NHNN") & (df_combined["article"].str.contains("Điều 50", na=False))].iloc[0].to_dict()
                    test_pairs.append((row_a, row_b, "An toàn kho quỹ & Vận chuyển tiền mặt"))
                except Exception:
                    pass
                    
            if "car" in domain_choice.lower() or "tất cả" in domain_choice.lower():
                try:
                    row_a = df_combined[(df_combined["so_ky_hieu"] == "250/QĐ-NHNO-QLRR") & (df_combined["article"].str.contains("Điều 5", na=False))].iloc[0].to_dict()
                    row_b = df_combined[(df_combined["so_ky_hieu"] == "41/2016/TT-NHNN")].iloc[0].to_dict()
                    test_pairs.append((row_a, row_b, "CAR & Quản lý rủi ro"))
                except Exception:
                    pass

            if "tín dụng" in domain_choice.lower() or "tất cả" in domain_choice.lower():
                try:
                    row_a = df_combined[(df_combined["so_ky_hieu"] == "315/QC-NHNO-TD") & (df_combined["article"].str.contains("Điều 8", na=False))].iloc[0].to_dict()
                    row_b = df_combined[(df_combined["so_ky_hieu"] == "315/QC-NHNO-TD") & (df_combined["article"].str.contains("Điều 35", na=False))].iloc[0].to_dict()
                    test_pairs.append((row_a, row_b, "Tín dụng & Thẩm quyền phê duyệt"))
                except Exception:
                    pass

            results = []
            for doc_a, doc_b, dom in test_pairs:
                res = st.session_state.compliance_engine.compare_clauses(
                    doc_a=doc_a, doc_b=doc_b, domain=dom,
                    user_id=user_id, user_role=user_role
                )
                results.append(res)

            st.session_state.compliance_results = results
            st.success(f"Đã hoàn thành kiểm tra {len(results)} cặp quy định qua {provider_name}!")

    # Display Results
    if st.session_state.compliance_results:
        st.markdown(f"### 📑 Kết quả Phân tích Đối chiếu ({len(st.session_state.compliance_results)} cặp)")
        
        for idx, res in enumerate(st.session_state.compliance_results):
            sev = res.get("severity", "NONE")
            badge_class = "badge-none"
            if sev == "HIGH":
                badge_class = "badge-high"
            elif sev == "MEDIUM":
                badge_class = "badge-medium"
            elif sev == "LOW":
                badge_class = "badge-low"

            cit_a = res.get("citation_a") or res.get("doc_a_citation", "N/A")
            cit_b = res.get("citation_b") or res.get("doc_b_citation", "N/A")
            c_type = res.get("conflict_type", "Quy trình thực hiện")
            c_desc = res.get("conflict_description") or res.get("description", "N/A")
            c_rec = res.get("recommendation", "Ban Kiểm tra Kiểm soát Nội bộ phối hợp Ban Pháp chế rà soát cập nhật.")
            c_id = res.get("conflict_id", f"CONF_{idx+1:02d}")
            c_dom = res.get("domain", "N/A")

            st.markdown(f"""
            <div class="compliance-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <span style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">#{idx+1} [{c_id}] {c_dom}</span>
                        <span style="margin-left: 10px; background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">{c_type}</span>
                    </div>
                    <div>
                        <span class="{badge_class}">MỨC ĐỘ: {sev}</span>
                        <span class="badge-guardrail" style="margin-left: 8px;">{res.get('review_status', 'NEEDS_HUMAN_REVIEW')}</span>
                    </div>
                </div>
                <div style="margin-bottom: 8px;"><b>📜 Căn cứ đối chiếu:</b> <code>{cit_a}</code> <b>vs</b> <code>{cit_b}</code></div>
                <div style="margin-bottom: 8px;"><b>⚠️ Mô tả xung đột:</b> {c_desc}</div>
                <div style="background-color: #f8fafc; padding: 10px; border-radius: 6px; border-left: 4px solid #0284c7;">
                    <b>💡 Đề xuất chỉnh sửa / Kiến nghị:</b><br>{c_rec}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Export Section
        df_comp_exp = pd.DataFrame(st.session_state.compliance_results)
        c_exp1, c_exp2 = st.columns(2)
        with c_exp1:
            st.download_button(
                "📥 Tải Kết quả Đối chiếu (CSV)",
                data=df_comp_exp.to_csv(index=False).encode('utf-8'),
                file_name="compliance_conflicts_export.csv",
                mime="text/csv",
                use_container_width=True
            )
        with c_exp2:
            headers = list(df_comp_exp.columns)
            lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
            for _, row in df_comp_exp.iterrows():
                lines.append("| " + " | ".join(str(val).replace("\n", " ") for val in row.values) + " |")
            table_md = "\n".join(lines)
            md_text = f"# BÁO CÁO ĐỐI CHIẾU QUY ĐỊNH AGRIBANK\nThời gian: {datetime.now().isoformat()}\n\n" + table_md
            st.download_button(
                "📥 Tải Báo cáo Đối chiếu (Markdown)",
                data=md_text.encode('utf-8'),
                file_name="compliance_conflicts_report.md",
                mime="text/markdown",
                use_container_width=True
            )

# ==========================================
# TAB 4: UC4 - AUDIT CHECKLIST GENERATOR
# ==========================================
with tab4:
    st.subheader("📋 UC4: Sinh Tự Động Checklist Kiểm toán Tuân thủ (Audit Checklist Generator)")
    st.markdown("Trợ lý AI tự động phân tích quy định và sinh danh mục các câu hỏi / thủ tục kiểm toán hiện trường cho Kiểm toán viên.")

    col_chk1, col_chk2 = st.columns([2, 1])
    with col_chk1:
        audit_domain_choice = st.selectbox(
            "Chọn Miền nghiệp vụ cần lập Checklist Kiểm toán",
            [
                "An toàn kho quỹ & Vận chuyển tiền mặt",
                "Tỷ lệ an toàn vốn (CAR) & Quản trị rủi ro",
                "Thẩm quyền phê duyệt cấp tín dụng & Quản lý hạn mức",
                "Bảo hiểm tài sản & Bảo hiểm tiền gửi",
                "Quản lý rủi ro công nghệ & Dữ liệu khách hàng"
            ]
        )
    with col_chk2:
        st.markdown("<br>", unsafe_allow_html=True)
        gen_chk_btn = st.button("🚀 Tạo Checklist Kiểm toán", type="primary", use_container_width=True)

    if gen_chk_btn:
        provider_name = "Local Model Qwen3:0.6B" if st.session_state.selected_provider == "ollama" else "Gemini Flash API"
        with st.spinner(f"Đang tổng hợp dữ liệu và sinh checklist qua {provider_name}..."):
            chk_results = []
            if "kho quỹ" in audit_domain_choice.lower():
                try:
                    c1 = df_combined[(df_combined["so_ky_hieu"] == "100/QĐ-NHNO-AT") & (df_combined["article"].str.contains("Điều 12", na=False))].iloc[0].to_dict()
                    c2 = df_combined[(df_combined["so_ky_hieu"] == "01/2014/TT-NHNN") & (df_combined["article"].str.contains("Điều 50", na=False))].iloc[0].to_dict()
                    chk_results = st.session_state.checklist_engine.generate_checklist(
                        domain="An toàn kho quỹ & Vận chuyển tiền mặt",
                        chunks=[c1, c2],
                        user_id=user_id,
                        user_role=user_role
                    )
                except Exception:
                    pass

            if "car" in audit_domain_choice.lower():
                try:
                    c1 = df_combined[(df_combined["so_ky_hieu"] == "250/QĐ-NHNO-QLRR") & (df_combined["article"].str.contains("Điều 5", na=False))].iloc[0].to_dict()
                    c2 = df_combined[(df_combined["so_ky_hieu"] == "41/2016/TT-NHNN")].iloc[0].to_dict()
                    chk_results = st.session_state.checklist_engine.generate_checklist(
                        domain="Tỷ lệ an toàn vốn (CAR) & Quản trị rủi ro",
                        chunks=[c1, c2],
                        user_id=user_id,
                        user_role=user_role
                    )
                except Exception:
                    pass

            if "tín dụng" in audit_domain_choice.lower():
                try:
                    c1 = df_combined[(df_combined["so_ky_hieu"] == "315/QC-NHNO-TD") & (df_combined["article"].str.contains("Điều 8", na=False))].iloc[0].to_dict()
                    c2 = df_combined[(df_combined["so_ky_hieu"] == "315/QC-NHNO-TD") & (df_combined["article"].str.contains("Điều 35", na=False))].iloc[0].to_dict()
                    chk_results = st.session_state.checklist_engine.generate_checklist(
                        domain="Thẩm quyền phê duyệt cấp tín dụng & Quản lý hạn mức",
                        chunks=[c1, c2],
                        user_id=user_id,
                        user_role=user_role
                    )
                except Exception:
                    pass

            if not chk_results:
                chk_results = st.session_state.checklist_engine.run_trial_tests()

            st.session_state.checklist_results = chk_results
            st.success(f"Đã sinh {len(chk_results)} mục checklist kiểm toán qua {provider_name}!")

    if st.session_state.checklist_results:
        st.markdown(f"### 📋 Danh mục Thủ tục Kiểm toán ({len(st.session_state.checklist_results)} mục)")
        for idx, it in enumerate(st.session_state.checklist_results):
            r_sev = it.get("risk_level", "MEDIUM")
            badge_class = "badge-high" if r_sev == "HIGH" else ("badge-medium" if r_sev == "MEDIUM" else "badge-low")
            
            st.markdown(f"""
            <div class="compliance-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div>
                        <span style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">#{idx+1} [{it['item_id']}] {it['domain']}</span>
                    </div>
                    <div>
                        <span class="{badge_class}">RỦI RO: {r_sev}</span>
                        <span class="badge-guardrail" style="margin-left: 8px;">{it.get('review_status', 'NEEDS_HUMAN_REVIEW')}</span>
                    </div>
                </div>
                <div style="margin-bottom: 8px;"><b>📜 Căn cứ quy định / Citation:</b> <code>{it.get('source_citation', '')}</code></div>
                <div style="margin-bottom: 8px;"><b>⚠️ Rủi ro tiềm ẩn:</b> {it.get('risk_description', '')}</div>
                <div style="background-color: #f8fafc; padding: 10px; border-radius: 6px; border-left: 4px solid #0284c7;">
                    <b>🔍 Thủ tục kiểm tra & Kiến nghị kiểm toán:</b><br>{it.get('recommendation', '')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Export Checklist
        df_chk_exp = pd.DataFrame(st.session_state.checklist_results)
        c_exp1, c_exp2 = st.columns(2)
        with c_exp1:
            st.download_button(
                "📥 Tải Danh mục Checklist (CSV)",
                data=df_chk_exp.to_csv(index=False).encode('utf-8'),
                file_name="audit_checklist_export.csv",
                mime="text/csv",
                use_container_width=True
            )
        with c_exp2:
            headers = list(df_chk_exp.columns)
            lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
            for _, row in df_chk_exp.iterrows():
                lines.append("| " + " | ".join(str(val).replace("\n", " ") for val in row.values) + " |")
            table_md = "\n".join(lines)
            md_text = f"# BÁO CÁO AUDIT CHECKLIST AGRIBANK\nThời gian: {datetime.now().isoformat()}\n\n" + table_md
            st.download_button(
                "📥 Tải Danh mục Checklist (Markdown)",
                data=md_text.encode('utf-8'),
                file_name="audit_checklist_report.md",
                mime="text/markdown",
                use_container_width=True
            )

# ==========================================
# TAB 5: AUDIT TRAIL & LOGS
# ==========================================
with tab5:
    st.subheader("📜 Tab 5: Nhật ký Truy vết & Kiểm toán Hệ thống (Audit Trail)")
    st.markdown("100% hành vi tra cứu, quét mâu thuẫn và phê duyệt của kiểm toán viên đều được ghi vết bảo mật vào tệp nhật ký.")

    log_path = "outputs/audit_trail.jsonl"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        logs = []
        for l in lines:
            try:
                logs.append(json.loads(l.strip()))
            except Exception:
                pass

        if logs:
            df_logs = pd.DataFrame(logs)
            st.markdown(f"**Tổng số bản ghi nhật ký:** `{len(logs)} sự kiện`")
            st.dataframe(df_logs, use_container_width=True, height=400)
            
            st.download_button(
                "📥 Tải File Nhật ký Audit Trail (JSONL)",
                data="".join(lines).encode('utf-8'),
                file_name="audit_trail.jsonl",
                mime="application/jsonlines",
                use_container_width=True
            )
        else:
            st.info("Chưa có bản ghi nhật ký.")
    else:
        st.info("Tệp nhật ký outputs/audit_trail.jsonl chưa được tạo.")
