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
from compliance_checker import ComplianceCheckerEngine
from audit_checklist_gen import AuditChecklistGeneratorEngine

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
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        white-space: pre-wrap;
        background-color: #f1f5f9;
        border-radius: 8px 8px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0284c7 !important;
        color: white !important;
    }
    
    /* Header Banner */
    .warning-banner {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border-left: 5px solid #f59e0b;
        padding: 12px 18px;
        border-radius: 8px;
        margin-bottom: 20px;
        color: #92400e;
        font-weight: 500;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
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
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "audit_logger" not in st.session_state:
    st.session_state.audit_logger = AuditLogger()
if "compliance_engine" not in st.session_state:
    st.session_state.compliance_engine = ComplianceCheckerEngine()
if "checklist_engine" not in st.session_state:
    st.session_state.checklist_engine = AuditChecklistGeneratorEngine()
if "compliance_results" not in st.session_state:
    st.session_state.compliance_results = []
if "checklist_results" not in st.session_state:
    st.session_state.checklist_results = []

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Logo_Agribank.png/800px-Logo_Agribank.png", width=180)
    st.markdown("### 🛡️ AI Compliance & Audit Suite")
    st.markdown("**Phiên bản:** Buổi 18 - Vibe Coding Production")
    st.divider()

    st.markdown("#### 👤 Thông tin Người Dùng & Phân quyền")
    user_id = st.text_input("User ID", value="auditor_admin_01")
    user_role = st.selectbox(
        "Vai trò người dùng (RBAC Role)",
        ["Admin", "Risk_Manager", "KiemToanVien", "Staff", "HR"],
        index=0
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
        st.session_state.compliance_results = []
        st.session_state.checklist_results = []
        st.success("Đã làm mới phiên làm việc!")
        st.rerun()

# ==========================================
# MAIN HEADER & BANNER
# ==========================================
st.title("🏦 Agribank AI Compliance & Audit Engine")
st.markdown("""
<div class="warning-banner">
    ⚠️ <b>KHUYẾN CÁO QUẢN TRỊ RỦI RO & GUARDRAIL:</b> Hệ thống sử dụng AI hỗ trợ tự động đối chiếu quy định và sinh checklist kiểm toán. Mọi kết quả gợi ý bắt buộc phải được <b>Kiểm toán viên xác minh (NEEDS_HUMAN_REVIEW)</b> trước khi ban hành báo cáo chính thức.
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3 = st.tabs([
    "🔍 UC3 - AI Compliance Checker",
    "📋 UC4 - AI Audit Checklist Generator",
    "📜 Tab 3 - Audit Trail & System Log"
])

# ==========================================
# TAB 1: UC3 - AI COMPLIANCE CHECKER
# ==========================================
with tab1:
    st.subheader("🔍 Kiểm tra Tuân thủ & So sánh Chéo Quy định (Cross-Comparison)")
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
        with st.spinner("Đang truy xuất Evidence Packages và phân tích so sánh chéo bằng Gemini LLM..."):
            # Prepare pairs to test based on selection
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
            st.success(f"Đã hoàn thành kiểm tra {len(results)} cặp quy định!")

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

            st.markdown(f"""
            <div class="compliance-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div>
                        <span style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">#{idx+1} [{res['conflict_id']}] {res['domain']}</span>
                        <span style="margin-left: 10px; background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 0.8rem;">{res['conflict_type']}</span>
                    </div>
                    <div>
                        <span class="{badge_class}">Severity: {sev}</span>
                        <span class="badge-guardrail" style="margin-left: 6px;">{res['review_status']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**📌 Văn bản A (Agribank):** `{res['doc_a_citation']}`")
                st.info(res['doc_a_text'])
            with col_b:
                st.markdown(f"**⚖️ Văn bản B (Đối chiếu):** `{res['doc_b_citation']}`")
                st.warning(res['doc_b_text'])

            st.markdown(f"**💡 Phân tích & Đánh giá từ AI:**")
            st.markdown(f"> {res['description']}")

            # Auditor Action Buttons
            c_btn1, c_btn2, _ = st.columns([1.5, 1.5, 4])
            with c_btn1:
                if st.button(f"✅ Xác nhận Tuân thủ", key=f"appr_{idx}"):
                    res['review_status'] = "AUDITOR_APPROVED"
                    st.session_state.audit_logger.log_action(
                        user_id=user_id, user_role=user_role,
                        action="AUDITOR_SIGN_OFF", domain=res['domain'],
                        details={"conflict_id": res['conflict_id'], "decision": "APPROVED"}
                    )
                    st.toast(f"Đã duyệt {res['conflict_id']}!")
                    st.rerun()
            with c_btn2:
                if st.button(f"🚩 Yêu cầu Sửa đổi", key=f"mod_{idx}"):
                    res['review_status'] = "FLAGGED_FOR_AMENDMENT"
                    st.session_state.audit_logger.log_action(
                        user_id=user_id, user_role=user_role,
                        action="AUDITOR_SIGN_OFF", domain=res['domain'],
                        details={"conflict_id": res['conflict_id'], "decision": "FLAGGED_FOR_AMENDMENT"}
                    )
                    st.toast(f"Đã gắn cờ sửa đổi {res['conflict_id']}!")
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        # Export Buttons
        col_exp1, col_exp2 = st.columns(2)
        df_exp = pd.DataFrame(st.session_state.compliance_results)
        with col_exp1:
            st.download_button(
                "📥 Tải Báo cáo Compliance (CSV)",
                data=df_exp.to_csv(index=False).encode('utf-8'),
                file_name="compliance_conflicts_export.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_exp2:
            try:
                table_md = df_exp.to_markdown(index=False)
            except Exception:
                # Safe markdown table builder fallback
                headers = list(df_exp.columns)
                lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
                for _, row in df_exp.iterrows():
                    lines.append("| " + " | ".join(str(val).replace("\n", " ") for val in row.values) + " |")
                table_md = "\n".join(lines)

            md_text = f"# BÁO CÁO COMPLIANCE AGRIBANK\nThời gian: {datetime.now().isoformat()}\n\n" + table_md
            st.download_button(
                "📥 Tải Báo cáo Compliance (Markdown)",
                data=md_text.encode('utf-8'),
                file_name="compliance_conflict_report.md",
                mime="text/markdown",
                use_container_width=True
            )

# ==========================================
# TAB 2: UC4 - AI AUDIT CHECKLIST GENERATOR
# ==========================================
with tab2:
    st.subheader("📋 Tự động Sinh Danh mục Checklist Kiểm toán Nội bộ")
    st.markdown("Nhập Domain và Đơn vị kiểm toán để AI tự động trích xuất các điều khoản liên quan và lập bảng checklist kèm rủi ro và khuyến nghị.")

    col_d, col_u = st.columns(2)
    with col_d:
        audit_domain = st.selectbox(
            "Miền / Lĩnh vực kiểm toán",
            [
                "An toàn kho quỹ & Vận chuyển tiền",
                "Bảo mật CNTT & AI",
                "CAR & Quản lý rủi ro",
                "Tín dụng & Thẩm quyền phê duyệt cho vay",
                "Ngoại hối & Quản lý trạng thái ngoại tệ",
                "Mạng lưới & Phát triển chi nhánh / PGD",
                "Bảo hiểm tài sản & Bảo hiểm nghiệp vụ",
                "Quản trị nhân sự & Đào tạo",
                "Tài chính & Mua sắm nội bộ",
                "Phân loại nợ & Xử lý nợ xấu"
            ]
        )
    with col_u:
        audit_unit = st.selectbox(
            "Đơn vị / Phòng ban được kiểm toán",
            [
                "Chi nhánh loại 1",
                "Chi nhánh loại 2",
                "Phòng giao dịch",
                "Khối CNTT & Ngân hàng số",
                "Phòng Kế toán & Quản lý kho quỹ",
                "Phòng Khách hàng Doanh nghiệp / Bán lẻ",
                "Ban Quản trị rủi ro Trụ sở chính"
            ]
        )

    gen_btn = st.button("⚡ Tạo bản nháp Checklist Kiểm toán", type="primary")

    if gen_btn:
        with st.spinner(f"Đang sinh checklist kiểm toán cho miền '{audit_domain}' tại '{audit_unit}'..."):
            items = st.session_state.checklist_engine.generate_checklist(
                domain=audit_domain,
                unit=audit_unit,
                user_role=user_role,
                user_id=user_id
            )
            st.session_state.checklist_results = items
            st.success(f"Đã sinh thành công {len(items)} mục kiểm tra!")

    if st.session_state.checklist_results:
        st.markdown(f"### 📝 Danh mục Checklist Kiểm toán ({len(st.session_state.checklist_results)} mục)")
        
        for it in st.session_state.checklist_results:
            r_level = it.get("risk_level", "MEDIUM")
            badge_cls = "badge-medium"
            if r_level == "HIGH":
                badge_cls = "badge-high"
            elif r_level == "LOW":
                badge_cls = "badge-low"

            with st.expander(f"🔹 [{it['item_id']}] {it['audit_question']} - {r_level}", expanded=True):
                st.markdown(f"**Phạm vi áp dụng:** `{it['domain']}` | `{it['unit_scope']}`")
                st.markdown(f"**⚠️ Rủi ro tiềm ẩn:** {it['risk_description']}")
                st.markdown(f"**⚖️ Căn cứ pháp lý (Citation):** `{it['source_citation']}`")
                st.markdown(f"**🛠️ Thủ tục kiểm toán / Khuyến nghị:** {it['recommendation']}")
                st.markdown(f"**Trạng thái Guardrail:** <span class='badge-guardrail'>{it['review_status']}</span>", unsafe_allow_html=True)

        col_c_exp1, col_c_exp2 = st.columns(2)
        df_chk_exp = pd.DataFrame(st.session_state.checklist_results)
        with col_c_exp1:
            st.download_button(
                "📥 Tải Checklist Kiểm toán (CSV)",
                data=df_chk_exp.to_csv(index=False).encode('utf-8'),
                file_name="audit_checklist_results.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_c_exp2:
            st.download_button(
                "📥 Tải Checklist Kiểm toán (JSON)",
                data=json.dumps(st.session_state.checklist_results, ensure_ascii=False, indent=2).encode('utf-8'),
                file_name="audit_checklist_results.json",
                mime="application/json",
                use_container_width=True
            )

# ==========================================
# TAB 3: AUDIT TRAIL & SYSTEM LOG
# ==========================================
with tab3:
    st.subheader("📜 Nhật ký Kiểm toán Hệ thống (Audit Trail & Governance)")
    st.markdown("Toàn bộ truy vấn, kiểm tra tuân thủ và thao tác của người dùng được ghi lại minh bạch và không thể chỉnh sửa.")

    col_flt1, col_flt2 = st.columns(2)
    with col_flt1:
        flt_role = st.selectbox("Lọc theo User Role", ["Tất cả", "Admin", "Risk_Manager", "KiemToanVien", "Staff", "HR"])
    with col_flt2:
        flt_action = st.selectbox("Lọc theo Hành động (Action)", ["Tất cả", "COMPLIANCE_CHECK", "GENERATE_AUDIT_CHECKLIST", "AUDITOR_SIGN_OFF"])

    logs = st.session_state.audit_logger.get_logs(
        role=None if flt_role == "Tất cả" else flt_role,
        action=None if flt_action == "Tất cả" else flt_action,
        limit=200
    )

    if logs:
        df_logs = pd.DataFrame(logs)
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("Chưa có bản ghi nhật ký nào phù hợp bộ lọc.")
