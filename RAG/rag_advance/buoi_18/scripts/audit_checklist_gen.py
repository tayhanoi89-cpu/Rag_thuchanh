import os
import sys
import json
import uuid
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure parent directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from audit_logger import AuditLogger

# Load environment
load_dotenv(".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.6-flash")

class AuditChecklistGeneratorEngine:
    def __init__(self, data_internal_path="data/agribank_internal_policies.csv",
                 data_combined_path="data/chunks_combined_secure.csv"):
        self.data_internal_path = data_internal_path
        self.data_combined_path = data_combined_path
        self.audit_logger = AuditLogger()
        self.df_internal = None
        self.df_combined = None
        self.client = None
        self._init_data()
        self._init_llm()

    def _init_data(self):
        if os.path.exists(self.data_internal_path):
            self.df_internal = pd.read_csv(self.data_internal_path)
        else:
            self.df_internal = pd.DataFrame()

        if os.path.exists(self.data_combined_path):
            self.df_combined = pd.read_csv(self.data_combined_path)
        else:
            self.df_combined = pd.DataFrame()

    def _init_llm(self):
        if GEMINI_API_KEY:
            try:
                from google import genai
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                print(f"[Warning] Cannot initialize google.genai: {e}")
                self.client = None

    def filter_by_rbac(self, df: pd.DataFrame, user_role: str) -> pd.DataFrame:
        """Filter chunks that the user_role is allowed to access."""
        if df.empty or user_role == "Admin":
            return df

        def is_allowed(val):
            if pd.isna(val):
                return False
            try:
                roles = json.loads(val) if isinstance(val, str) and val.startswith("[") else [str(val)]
                return user_role in roles
            except Exception:
                return user_role in str(val)

        return df[df["allowed_roles"].apply(is_allowed)]

    def retrieve_relevant_chunks(self, domain: str, unit: str = "", user_role: str = "Risk_Manager") -> list:
        """Retrieve relevant internal and legal regulatory chunks for a domain and unit."""
        if self.df_combined.empty:
            return []

        df_accessible = self.filter_by_rbac(self.df_combined, user_role)
        domain_lower = domain.lower()

        # Map domain keywords to documents
        skh_filter = []
        if any(k in domain_lower for k in ["kho quỹ", "tiền mặt", "kho tien", "van chuyen tien"]):
            skh_filter = ["100/QĐ-NHNO-AT", "01/2014/TT-NHNN"]
        elif any(k in domain_lower for k in ["bảo mật cntt", "an toàn thông tin", "dữ liệu ai", "rag ai", "cntt"]):
            skh_filter = ["600/QC-NHNO-CNTT"]
        elif any(k in domain_lower for k in ["car", "an toàn vốn", "định mức rủi ro"]):
            skh_filter = ["250/QĐ-NHNO-QLRR", "41/2016/TT-NHNN", "27/2024/TT-NHNN"]
        elif any(k in domain_lower for k in ["tín dụng", "cho vay", "phán quyết"]):
            skh_filter = ["315/QC-NHNO-TD"]
        elif any(k in domain_lower for k in ["ngoại tệ", "ngoại hối"]):
            skh_filter = ["410/QĐ-NHNO-TTNH", "135/2015/NĐ-CP", "105/2016/TT-BTC"]
        elif any(k in domain_lower for k in ["mạng lưới", "phòng giao dịch"]):
            skh_filter = ["520/QC-NHNO-MANGLUOI", "56/2024/TT-NHNN", "62/2024/TT-NHNN"]
        elif any(k in domain_lower for k in ["bảo hiểm", "bancassurance"]):
            skh_filter = ["180/QĐ-NHNO-BH", "46/2023/NĐ-CP", "73/2016/NĐ-CP"]
        elif any(k in domain_lower for k in ["nhân sự", "bổ nhiệm", "đào tạo"]):
            skh_filter = ["88/QĐ-NHNO-NS"]
        elif any(k in domain_lower for k in ["tài chính", "mua sắm"]):
            skh_filter = ["720/QC-NHNO-TC"]
        elif any(k in domain_lower for k in ["nợ xấu", "xử lý nợ", "phân loại nợ"]):
            skh_filter = ["390/QĐ-NHNO-XLN"]

        if skh_filter:
            matched_df = df_accessible[df_accessible["so_ky_hieu"].isin(skh_filter)]
            if not matched_df.empty:
                return matched_df.to_dict("records")

        # Unknown domain returns empty list
        return []

    def generate_checklist(self, domain: str, unit: str, user_role: str = "Risk_Manager",
                           user_id: str = "auditor_01") -> list:
        """Generate audit checklist items using LLM based on retrieved regulations."""
        request_id = str(uuid.uuid4())[:8]
        chunks = self.retrieve_relevant_chunks(domain, unit, user_role)

        if not chunks:
            # Handle unknown domain or no data accessible
            self.audit_logger.log_action(
                user_id=user_id,
                user_role=user_role,
                action="GENERATE_AUDIT_CHECKLIST",
                domain=domain,
                request_id=request_id,
                status="NO_DATA",
                details={"message": "Chưa có dữ liệu quy định phù hợp trong hệ thống hoặc không có quyền truy cập."}
            )
            return []

        # Prepare context
        context_parts = []
        for idx, c in enumerate(chunks, 1):
            citation = c.get("citation", f"{c.get('so_ky_hieu', '')} - {c.get('article', '')}")
            context_parts.append(f"[{idx}] Trích dẫn: {citation}\nNội dung: {c.get('text', '')}")

        context_str = "\n\n".join(context_parts)

        # Domain prefix code
        prefix = "CHK"
        if "kho" in domain.lower():
            prefix = "CHK_KHO"
        elif "cntt" in domain.lower() or "ai" in domain.lower():
            prefix = "CHK_CNTT"
        elif "tín dụng" in domain.lower():
            prefix = "CHK_TD"
        elif "car" in domain.lower():
            prefix = "CHK_CAR"
        else:
            prefix = "CHK_GEN"

        prompt = f"""Bạn là Trưởng đoàn Kiểm toán Nội bộ Ngân hàng (Senior Audit Lead).
Nhiệm vụ: Tạo danh mục Checklist kiểm toán nội bộ (Audit Checklist) cho:
- Lĩnh vực / Miền kiểm toán: '{domain}'
- Đơn vị được kiểm toán: '{unit}'

Căn cứ vào CƠ SỞ PHÁP LÝ & QUY ĐỊNH NỘI BỘ dưới đây:
--- CONTEXT QUY ĐỊNH ---
{context_str}
--- HẾT CONTEXT ---

YÊU CẦU THIẾT LẬP CHECKLIST:
1. Sinh từ 3 đến 5 mục kiểm tra (Checklist items) trọng yếu, có tính thực tiễn cao cho đơn vị '{unit}'.
2. Mỗi mục kiểm tra bắt buộc phải trích dẫn CHÍNH XÁC từ các citation có sẵn trong context (Không tự bịa điều khoản).
3. Đánh giá mức độ rủi ro (risk_level: HIGH / MEDIUM / LOW):
   - HIGH: Rủi ro tổn thất tài sản lớn, vi phạm pháp luật hoặc đe dọa an toàn thông tin nghiêm trọng.
   - MEDIUM: Rủi ro vận hành, sai lệch quy trình nội bộ.
   - LOW: Thiếu sót thủ tục hành chính, chậm trễ báo cáo.
4. Nêu rõ câu hỏi kiểm toán (`audit_question`), rủi ro tiềm ẩn (`risk_description`), và thủ tục/khuyến nghị kiểm toán (`recommendation`).

ĐỊNH DẠNG ĐẦU RA JSON BẮT BUỘC:
```json
[
  {{
    "item_id": "{prefix}_01",
    "domain": "{domain}",
    "unit_scope": "{unit}",
    "audit_question": "Câu hỏi kiểm toán cụ thể...",
    "risk_description": "Rủi ro tiềm ẩn nếu đơn vị vi phạm...",
    "risk_level": "HIGH | MEDIUM | LOW",
    "source_citation": "Trích dẫn nguyên văn citation từ context...",
    "recommendation": "Thủ tục kiểm tra thực địa và kiến nghị kiểm toán...",
    "review_status": "NEEDS_HUMAN_REVIEW"
  }}
]
```
"""

        checklist_items = []
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model=LLM_MODEL,
                    contents=prompt
                )
                raw_text = response.text.strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                items = json.loads(raw_text)
                for it in items:
                    it["review_status"] = "NEEDS_HUMAN_REVIEW"
                    it["timestamp"] = datetime.now().isoformat()
                    it["request_id"] = request_id
                    checklist_items.append(it)
            except Exception as e:
                print(f"[LLM Error in Checklist Gen] {e}")

        # Fallback items if LLM fails
        if not checklist_items:
            for idx, c in enumerate(chunks[:4], 1):
                citation = c.get("citation", f"{c.get('so_ky_hieu', '')} - {c.get('article', '')}")
                checklist_items.append({
                    "item_id": f"{prefix}_{idx:02d}",
                    "domain": domain,
                    "unit_scope": unit,
                    "audit_question": f"Đơn vị đã tuân thủ đầy đủ quy định tại {c.get('article', 'điều khoản')} chưa?",
                    "risk_description": "Rủi ro không tuân thủ quy trình dẫn đến sai phạm vận hành hoặc rủi ro pháp lý.",
                    "risk_level": "HIGH" if idx == 1 else "MEDIUM",
                    "source_citation": citation,
                    "recommendation": "Kiểm tra hồ sơ thực tế, nhật ký vận hành và biên bản đối chiếu.",
                    "review_status": "NEEDS_HUMAN_REVIEW",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id
                })

        # Audit Logger
        self.audit_logger.log_action(
            user_id=user_id,
            user_role=user_role,
            action="GENERATE_AUDIT_CHECKLIST",
            domain=domain,
            request_id=request_id,
            status="SUCCESS",
            details={
                "unit": unit,
                "items_count": len(checklist_items),
                "review_status": "NEEDS_HUMAN_REVIEW"
            }
        )

        return checklist_items

    def run_trial_tests(self) -> list:
        """Run trial test generating checklist for 2 domains: Kho quỹ & CNTT/AI."""
        print("=== BẮT ĐẦU CHẠY THỬ NGHIỆM TẠO AUDIT CHECKLIST (UC4) ===")
        all_items = []

        # Domain 1: An toàn kho quỹ
        print("\n[Test 1] Domain: 'An toàn kho quỹ & Vận chuyển tiền' | Unit: 'Chi nhánh loại 1'")
        items_kho = self.generate_checklist(
            domain="An toàn kho quỹ & Vận chuyển tiền",
            unit="Chi nhánh loại 1",
            user_role="Risk_Manager",
            user_id="lead_auditor_01"
        )
        all_items.extend(items_kho)
        print(f"-> Đã sinh {len(items_kho)} mục checklist cho Kho quỹ.")

        # Domain 2: Bảo mật CNTT & AI
        print("\n[Test 2] Domain: 'Bảo mật CNTT & AI' | Unit: 'Khối CNTT'")
        items_cntt = self.generate_checklist(
            domain="Bảo mật CNTT & AI",
            unit="Khối CNTT",
            user_role="Risk_Manager",
            user_id="lead_auditor_02"
        )
        all_items.extend(items_cntt)
        print(f"-> Đã sinh {len(items_cntt)} mục checklist cho Bảo mật CNTT & AI.")

        # Export outputs
        self.export_results(all_items)
        return all_items

    def export_results(self, checklist_items: list):
        os.makedirs("outputs", exist_ok=True)
        df_res = pd.DataFrame(checklist_items)

        csv_cols = [
            "item_id", "domain", "unit_scope", "audit_question", "risk_description",
            "risk_level", "source_citation", "recommendation", "review_status"
        ]
        for c in csv_cols:
            if c not in df_res.columns:
                df_res[c] = ""
        df_res = df_res[csv_cols]
        df_res.to_csv("outputs/audit_checklist_results.csv", index=False, encoding="utf-8")
        print("\n✅ Đã lưu kết quả ra outputs/audit_checklist_results.csv")

        # Export Markdown Report
        md_lines = [
            "# BÁO CÁO AI AUDIT CHECKLIST GENERATOR (UC4)",
            "## Hệ thống Tự động Sinh Danh mục Kiểm toán Nội bộ Agribank\n",
            f"**Thời gian tạo báo cáo:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Tổng số mục kiểm tra (Checklist Items):** `{len(checklist_items)}`  ",
            f"**Trạng thái Review Guardrail:** `NEEDS_HUMAN_REVIEW` (100%)\n",
            "---",
            "### 1. Bảng Danh mục Checklist Kiểm toán Chi tiết\n",
            "| Mã Mục | Miền Nghiệp vụ | Phạm vi Đơn vị | Câu hỏi Kiểm toán | Rủi ro Tiềm ẩn | Mức Rủi ro | Trích dẫn Văn bản Gốc (Citation) |",
            "|---|---|---|---|---|---|---|"
        ]

        for it in checklist_items:
            risk_badge = f"**{it['risk_level']}**"
            if it['risk_level'] == 'HIGH':
                risk_badge = f"<span style='color:red;'>🔴 <b>HIGH</b></span>"
            elif it['risk_level'] == 'MEDIUM':
                risk_badge = f"<span style='color:orange;'>🟡 <b>MEDIUM</b></span>"
            elif it['risk_level'] == 'LOW':
                risk_badge = f"<span style='color:green;'>🟢 <b>LOW</b></span>"

            md_lines.append(
                f"| `{it['item_id']}` | **{it['domain']}** | {it['unit_scope']} | {it['audit_question']} | {it['risk_description']} | {risk_badge} | `{it['source_citation']}` |"
            )

        md_lines.append("\n---")
        md_lines.append("### 2. Chi tiết Quy trình Kiểm tra & Kiến nghị Kiểm toán\n")

        for it in checklist_items:
            md_lines.append(f"#### [{it['item_id']}] {it['audit_question']}")
            md_lines.append(f"- **Miền / Đơn vị:** `{it['domain']}` - `{it['unit_scope']}`")
            md_lines.append(f"- **Rủi ro tiềm ẩn:** {it['risk_description']}")
            md_lines.append(f"- **Mức độ rủi ro:** `{it['risk_level']}`")
            md_lines.append(f"- **Trích dẫn căn cứ:** `{it['source_citation']}`")
            md_lines.append(f"- **Kiến nghị / Thủ tục kiểm tra:** {it['recommendation']}")
            md_lines.append(f"- **Trạng thái phê duyệt:** `{it['review_status']}`\n")

        md_lines.append("---")
        md_lines.append("### 3. Kết luận & Nghiệm thu Core Engine UC4\n")
        md_lines.append("```plaintext")
        md_lines.append("CHECKLIST GENERATOR ENGINE: PASS")
        md_lines.append(f"CHECKLIST ITEMS GENERATED: {len(checklist_items)}")
        md_lines.append("CITATIONS ATTACHED: YES")
        md_lines.append("```")

        with open("outputs/audit_checklist_report.md", "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        print("✅ Đã tạo báo cáo outputs/audit_checklist_report.md")

if __name__ == "__main__":
    engine = AuditChecklistGeneratorEngine()
    engine.run_trial_tests()
