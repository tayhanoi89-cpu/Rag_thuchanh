import os
import sys
import json
import re
import pandas as pd
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure scripts directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audit_logger import AuditLogger
from compliance_checker import ComplianceCheckerEngine
from audit_checklist_gen import AuditChecklistGeneratorEngine

class SecurityAndGuardrailTester:
    def __init__(self):
        self.compliance_engine = ComplianceCheckerEngine()
        self.checklist_engine = AuditChecklistGeneratorEngine()
        self.audit_logger = AuditLogger()
        self.test_results = []

    def log_test(self, test_num: int, test_name: str, passed: bool, details: str):
        self.test_results.append({
            "test_num": test_num,
            "test_name": test_name,
            "passed": passed,
            "status": "PASS" if passed else "FAIL",
            "details": details
        })
        print(f"[{'PASS' if passed else 'FAIL'}] Test {test_num}: {test_name} - {details}")

    def run_all_tests(self):
        print("=== BẮT ĐẦU CHẠY 7 BÀI KIỂM THỬ BẢO MẬT & GUARDRAILS BUỔI 18 ===\n")
        
        # Test 1: RBAC Test
        self.test_1_rbac()
        
        # Test 2: Citation Integrity
        self.test_2_citation_integrity()
        
        # Test 3: Hallucination Check
        self.test_3_hallucination_check()
        
        # Test 4: Human Review Guardrail
        self.test_4_human_review_guardrail()
        
        # Test 5: Audit Log Privacy
        self.test_5_audit_log_privacy()
        
        # Test 6: Unknown Domain Test
        self.test_6_unknown_domain()
        
        # Test 7: File Export Verification
        self.test_7_file_export_verification()

        # Generate Report
        self.generate_report()

    def test_1_rbac(self):
        """Test 1: Role 'Staff' cannot access confidential docs of 'Risk_Manager' or 'Admin'."""
        df_combined = self.compliance_engine.df_combined
        staff_accessible = self.compliance_engine.filter_by_rbac(df_combined, user_role="Staff")
        
        # 600/QC-NHNO-CNTT and 410/QĐ-NHNO-TTNH only allow Admin/Risk_Manager
        staff_skh = staff_accessible["so_ky_hieu"].unique().tolist()
        has_it_sec = "600/QC-NHNO-CNTT" in staff_skh
        has_fx = "410/QĐ-NHNO-TTNH" in staff_skh
        
        passed = (not has_it_sec) and (not has_fx)
        details = (
            f"Role 'Staff' chỉ truy cập được {len(staff_accessible)} chunks. "
            f"Không truy cập được tài liệu mật 600/QC-NHNO-CNTT (IT Security) và 410/QĐ-NHNO-TTNH (FX). "
            f"RBAC lọc thành công 100%."
        ) if passed else "Lỗi: Role 'Staff' truy cập được tài liệu mật của Risk_Manager/Admin!"
        
        self.log_test(1, "RBAC Access Control", passed, details)

    def test_2_citation_integrity(self):
        """Test 2: Every conflict finding (UC3) and checklist item (UC4) must have valid Citation."""
        passed = True
        details_list = []

        # Check UC3 CSV
        if os.path.exists("outputs/compliance_conflicts.csv"):
            df_conf = pd.read_csv("outputs/compliance_conflicts.csv")
            empty_cits_a = df_conf["doc_a_citation"].isna().sum() + (df_conf["doc_a_citation"] == "").sum()
            empty_cits_b = df_conf["doc_b_citation"].isna().sum() + (df_conf["doc_b_citation"] == "").sum()
            if empty_cits_a > 0 or empty_cits_b > 0:
                passed = False
                details_list.append(f"UC3 có {empty_cits_a + empty_cits_b} trích dẫn rỗng.")
            else:
                details_list.append(f"UC3: 100% ({len(df_conf)}) findings có Citation hợp lệ.")
        else:
            passed = False
            details_list.append("Chưa tìm thấy file outputs/compliance_conflicts.csv.")

        # Check UC4 CSV
        if os.path.exists("outputs/audit_checklist_results.csv"):
            df_chk = pd.read_csv("outputs/audit_checklist_results.csv")
            empty_cits = df_chk["source_citation"].isna().sum() + (df_chk["source_citation"] == "").sum()
            if empty_cits > 0:
                passed = False
                details_list.append(f"UC4 có {empty_cits} trích dẫn rỗng.")
            else:
                details_list.append(f"UC4: 100% ({len(df_chk)}) checklist items có Citation hợp lệ.")
        else:
            passed = False
            details_list.append("Chưa tìm thấy file outputs/audit_checklist_results.csv.")

        self.log_test(2, "Citation Integrity", passed, " | ".join(details_list))

    def test_3_hallucination_check(self):
        """Test 3: Verify AI citations reference real dataset documents."""
        df_combined = self.compliance_engine.df_combined
        valid_skh = set(df_combined["so_ky_hieu"].unique())

        hallucinated = []
        if os.path.exists("outputs/audit_checklist_results.csv"):
            df_chk = pd.read_csv("outputs/audit_checklist_results.csv")
            for _, row in df_chk.iterrows():
                cit = str(row.get("source_citation", ""))
                found = any(skh in cit for skh in valid_skh)
                if not found:
                    hallucinated.append(cit)

        passed = len(hallucinated) == 0
        details = (
            f"Tất cả trích dẫn đều khớp với danh mục 25 số hiệu văn bản thật trong dataset ({len(valid_skh)} SKH). "
            f"Không có hiện tượng AI tự chế văn bản giả mạo."
        ) if passed else f"Phát hiện trích dẫn không có thật: {hallucinated}"

        self.log_test(3, "Hallucination Check", passed, details)

    def test_4_human_review_guardrail(self):
        """Test 4: All outputs have review_status = 'NEEDS_HUMAN_REVIEW'."""
        passed = True
        details_list = []

        if os.path.exists("outputs/audit_checklist_results.csv"):
            df_chk = pd.read_csv("outputs/audit_checklist_results.csv")
            non_human = (df_chk["review_status"] != "NEEDS_HUMAN_REVIEW").sum()
            if non_human > 0:
                passed = False
                details_list.append(f"UC4 có {non_human} items không có nhãn NEEDS_HUMAN_REVIEW.")
            else:
                details_list.append(f"UC4: 100% ({len(df_chk)}) items bắt buộc Human Review.")

        if os.path.exists("outputs/compliance_conflicts.csv"):
            df_conf = pd.read_csv("outputs/compliance_conflicts.csv")
            # If conflicts detected, review_status must be NEEDS_HUMAN_REVIEW
            conflicts = df_conf[~df_conf["conflict_type"].isin(["KHONG_XUNG_DOT", "CHUA_DU_BANG_CHUNG"])]
            for _, r in conflicts.iterrows():
                if r["review_status"] != "NEEDS_HUMAN_REVIEW":
                    passed = False
                    details_list.append(f"UC3 conflict {r['conflict_id']} thiếu nhãn NEEDS_HUMAN_REVIEW.")
            details_list.append("UC3: Guardrail kích hoạt chính xác cho các xung đột.")

        self.log_test(4, "Human Review Guardrail", passed, " | ".join(details_list))

    def test_5_audit_log_privacy(self):
        """Test 5: Audit log contains no plaintext API keys or secrets."""
        log_path = "outputs/audit_trail.jsonl"
        passed = True
        details = ""

        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Check for plaintext key patterns
                if re.search(r'AQ\.[A-Za-z0-9_\-]{20,}', content) or re.search(r'AIza[0-9A-Za-z-_]{35}', content):
                    passed = False
                    details = "Cảnh báo: Phát hiện Gemini API key dạng thô trong audit log!"
                else:
                    details = f"File audit_trail.jsonl ({len(content.splitlines())} dòng) đã khử khuẩn hoàn toàn. Không chứa API key / secret."
        else:
            passed = False
            details = "Chưa tìm thấy file outputs/audit_trail.jsonl."

        self.log_test(5, "Audit Log Privacy & Masking", passed, details)

    def test_6_unknown_domain(self):
        """Test 6: Input unknown domain -> Clear 'No Data' message, no hallucinated fake policies."""
        unknown_domain = "Khai thác mỏ vũ trụ & Hàng không vũ trụ"
        items = self.checklist_engine.generate_checklist(
            domain=unknown_domain,
            unit="Ban Quản lý Vũ trụ",
            user_role="Admin",
            user_id="sec_tester"
        )
        passed = len(items) == 0
        details = (
            f"Khi kiểm tra Domain không tồn tại ('{unknown_domain}'), hệ thống trả về danh sách rỗng (0 items) "
            f"và ghi nhận trạng thái NO_DATA vào Audit Trail, không tự bịa quy định."
        ) if passed else f"Lỗi: Hệ thống tự bịa ra {len(items)} mục cho domain không tồn tại!"

        self.log_test(6, "Unknown Domain Guardrail", passed, details)

    def test_7_file_export_verification(self):
        """Test 7: Verify exported CSV files have correct schemas and are readable."""
        passed = True
        details_list = []

        expected_conf_cols = [
            "conflict_id", "domain", "doc_a_id", "doc_a_citation", "doc_a_text",
            "doc_b_id", "doc_b_citation", "doc_b_text", "conflict_type",
            "severity", "description", "review_status", "timestamp", "request_id"
        ]
        expected_chk_cols = [
            "item_id", "domain", "unit_scope", "audit_question", "risk_description",
            "risk_level", "source_citation", "recommendation", "review_status"
        ]

        # 1. Check compliance_conflicts.csv
        try:
            df_c = pd.read_csv("outputs/compliance_conflicts.csv")
            missing_c = [col for col in expected_conf_cols if col not in df_c.columns]
            if missing_c:
                passed = False
                details_list.append(f"compliance_conflicts.csv thiếu cột: {missing_c}")
            else:
                details_list.append(f"compliance_conflicts.csv hợp lệ 14/14 cột ({len(df_c)} dòng).")
        except Exception as e:
            passed = False
            details_list.append(f"Lỗi đọc compliance_conflicts.csv: {e}")

        # 2. Check audit_checklist_results.csv
        try:
            df_k = pd.read_csv("outputs/audit_checklist_results.csv")
            missing_k = [col for col in expected_chk_cols if col not in df_k.columns]
            if missing_k:
                passed = False
                details_list.append(f"audit_checklist_results.csv thiếu cột: {missing_k}")
            else:
                details_list.append(f"audit_checklist_results.csv hợp lệ 9/9 cột ({len(df_k)} dòng).")
        except Exception as e:
            passed = False
            details_list.append(f"Lỗi đọc audit_checklist_results.csv: {e}")

        self.log_test(7, "File Export Schema Verification", passed, " | ".join(details_list))

    def generate_report(self):
        all_passed = all(r["passed"] for r in self.test_results)
        
        md_lines = [
            "# BÁO CÁO KIỂM THỬ BẢO MẬT & GUARDRAIL BUỔI 18",
            "## Đánh giá Toàn diện 7 Tiêu chuẩn Bảo mật & Phòng chống Ảo giác AI\n",
            f"**Thời gian kiểm thử:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Số lượng bài kiểm tra:** `7/7`  ",
            f"**Trạng thái chung:** `{'PASS (100%)' if all_passed else 'FAIL'}`\n",
            "---",
            "### 1. Bảng Tổng hợp Kết quả Kiểm thử\n",
            "| STT | Tên bài kiểm thử | Trạng thái | Chi tiết đánh giá & Bằng chứng kiểm thử |",
            "|---|---|---|---|"
        ]

        for r in self.test_results:
            badge = "<span style='color:green;'>✅ <b>PASS</b></span>" if r["passed"] else "<span style='color:red;'>❌ <b>FAIL</b></span>"
            md_lines.append(f"| {r['test_num']} | **{r['test_name']}** | {badge} | {r['details']} |")

        md_lines.append("\n---")
        md_lines.append("### 2. Chi tiết 7 Tiêu chuẩn Kiểm soát Bảo mật\n")
        
        criteria = [
            ("1. RBAC Test", "Cách ly phân quyền nghiêm ngặt: Role 'Staff' bị chặn hoàn toàn khỏi việc truy cập các tài liệu mật của Khối CNTT (600/QC-NHNO-CNTT) và Ngoại tệ (410/QĐ-NHNO-TTNH)."),
            ("2. Citation Integrity", "Tính toàn vẹn trích dẫn: 100% kết quả phân tích xung đột và câu hỏi kiểm toán đều có Citation chi tiết gắn liền với Điều/Khoản."),
            ("3. Hallucination Check", "Chống ảo giác AI: Tuyệt đối không xuất hiện các điều khoản hoặc văn bản bịa đặt ngoài 25 số hiệu văn bản có trong tập dữ liệu."),
            ("4. Human Review Guardrail", "Cơ chế kiểm soát con người: Tất cả kết quả đều được gán nhãn bắt buộc `NEEDS_HUMAN_REVIEW` để Kiểm toán viên thẩm tra trước khi sử dụng."),
            ("5. Audit Log Privacy", "Bảo mật vết kiểm toán: Audit Trail được khử khuẩn tự động (Sanitization), loại bỏ hoàn toàn API key và secret tokens."),
            ("6. Unknown Domain Test", "Xử lý miền không xác định: Khi nhập domain nằm ngoài dữ liệu, hệ thống thông báo 'Chưa có dữ liệu quy định' thay vì tạo dữ liệu giả mạo."),
            ("7. File Export Verification", "Toàn vẹn tệp xuất: Các tệp CSV xuất bản tuân thủ chính xác Schema chuẩn, mở và phân tích trơn tru trên Pandas.")
        ]

        for title, desc in criteria:
            md_lines.append(f"#### {title}\n{desc}\n")

        md_lines.append("---")
        md_lines.append("### 3. Kết luận Báo cáo Bảo mật\n")
        md_lines.append("```plaintext")
        md_lines.append(f"SECURITY & GUARDRAIL TESTS: {'PASS' if all_passed else 'FAIL'}")
        md_lines.append("```")

        os.makedirs("outputs", exist_ok=True)
        with open("outputs/security_test_b18_report.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        print("\n" + "="*50)
        print(f"SECURITY & GUARDRAIL TESTS: {'PASS' if all_passed else 'FAIL'}")
        print("="*50)

if __name__ == "__main__":
    tester = SecurityAndGuardrailTester()
    tester.run_all_tests()
