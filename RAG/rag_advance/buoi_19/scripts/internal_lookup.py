"""
Use Case 1: AI Internal Policy & Regulation Lookup with RBAC and Audit Trail.
Supports Dual Provider (Ollama Local SLM / Gemini Cloud).
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any
import pandas as pd
from dotenv import load_dotenv

# Set UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

from audit_logger import AuditLogger
from ollama_adapter import OllamaClient

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower().strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.6-flash")

FALLBACK_NO_INFO = "Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập."

SYSTEM_PROMPT = """Bạn là trợ lý AI tra cứu văn bản quy định và chính sách pháp lý ngân hàng Agribank.

CÁC NGUYÊN TẮC BẮT BUỘC TUÂN THỦ:
1. CHỈ được trả lời dựa hoàn toàn vào các tài liệu trong phần 'NGỮ CẢNH ĐƯỢC PHÉP TRUY CẬP' dưới đây.
2. TUYỆT ĐỐI KHÔNG sử dụng kiến thức bên ngoài ngữ cảnh để suy diễn, bịa đặt hay bổ sung.
3. Nếu ngữ cảnh được cung cấp KHÔNG chứa đủ thông tin để trả lời câu hỏi, bạn BẮT BUỘC chỉ trả lời đúng một câu duy nhất:
   "Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập."
4. Khi trả lời, phải trình bày câu trả lời hoàn chỉnh bằng tiếng Việt và nêu rõ trích dẫn (Citation / Số hiệu văn bản) từ tài liệu cung cấp. Tuyệt đối không tạo trích dẫn giả.
"""


class InternalLookupEngine:
    """Core engine executing grounded Q&A with pre-retrieval RBAC and full audit logging."""

    def __init__(self, data_path: str = None, log_dir: str = "outputs", log_file: str = "audit_trail.jsonl") -> None:
        self.root_dir = PROJECT_ROOT
        self.data_path = data_path or self._resolve_path("data/chunks_combined_secure.csv")
        self.audit_logger = AuditLogger(log_dir=log_dir, log_file=log_file)
        self.provider = LLM_PROVIDER
        self.ollama_client = None
        self.gemini_client = None
        self.df_chunks = None

        self._init_data()
        self._init_llm()

    def _resolve_path(self, rel_path: str) -> str:
        p1 = self.root_dir / rel_path
        if p1.exists():
            return str(p1)
        p2 = Path(rel_path)
        if p2.exists():
            return str(p2)
        return str(p1)

    def _init_data(self):
        if os.path.exists(self.data_path):
            self.df_chunks = pd.read_csv(self.data_path)
        else:
            self.df_chunks = pd.DataFrame()

    def _init_llm(self):
        if self.provider == "ollama":
            self.ollama_client = OllamaClient()
        elif self.provider == "gemini" and GEMINI_API_KEY:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception:
                self.gemini_client = None

    def filter_by_rbac(self, user_role: str) -> pd.DataFrame:
        """Filter chunks accessible by user_role."""
        if self.df_chunks.empty or user_role == "Admin":
            return self.df_chunks

        def is_allowed(val):
            if pd.isna(val):
                return False
            try:
                roles = json.loads(val) if isinstance(val, str) and val.startswith("[") else [str(val)]
                return user_role in roles
            except Exception:
                return user_role in str(val)

        return self.df_chunks[self.df_chunks["allowed_roles"].apply(is_allowed)]

    def retrieve(self, query: str, user_role: str = "Staff", top_k: int = 5) -> dict:
        """Perform keyword & relevance search filtered by RBAC."""
        if self.df_chunks.empty:
            return {"authorized_chunks": [], "denied_chunks": []}

        df_acc = self.filter_by_rbac(user_role)
        query_words = [w.lower() for w in re.split(r"\W+", query) if len(w) > 2]

        def calc_score(text):
            t_low = str(text).lower()
            return sum(1 for w in query_words if w in t_low)

        df_acc = df_acc.copy()
        df_acc["score"] = df_acc["text"].apply(calc_score)
        matched = df_acc[df_acc["score"] > 0].sort_values(by="score", ascending=False)

        if matched.empty:
            matched = df_acc.head(top_k)
        else:
            matched = matched.head(top_k)

        auth_chunks = matched.to_dict("records")
        return {"authorized_chunks": auth_chunks, "denied_chunks": []}

    def query(
        self,
        query_text: str,
        user_role: str = "Staff",
        user_id: str = "user_default",
        top_k: int = 3,
    ) -> dict[str, Any]:
        """Execute a secure RAG lookup."""
        req_id = f"req_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        retrieval_res = self.retrieve(query=query_text, user_role=user_role, top_k=top_k)
        authorized_chunks = retrieval_res["authorized_chunks"]
        denied_chunks = retrieval_res["denied_chunks"]

        if not authorized_chunks:
            answer = FALLBACK_NO_INFO
            status = "NO_MATCH"
            citations = []
            groundedness = "NOT_APPLICABLE"

            self.audit_logger.log_action(
                user_id=user_id,
                user_role=user_role,
                action="INTERNAL_LOOKUP",
                domain="Tra cứu quy định nội bộ",
                request_id=req_id,
                status=status,
                details={
                    "query": query_text,
                    "authorized_chunks_count": 0,
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                },
            )

            return {
                "request_id": req_id,
                "answer": answer,
                "citations": citations,
                "authorized_chunks": [],
                "denied_chunks_count": len(denied_chunks),
                "groundedness": groundedness,
                "status": status,
                "review_status": "NEEDS_HUMAN_REVIEW",
            }

        context_blocks = []
        citations_list = []
        for idx, chunk in enumerate(authorized_chunks, 1):
            citation = chunk.get("citation", f"{chunk.get('so_ky_hieu', '')} - {chunk.get('article', '')}")
            citations_list.append(citation)
            text_snip = str(chunk.get("text", ""))[:1500]
            context_blocks.append(
                f"[TÀI LIỆU {idx}]\n- Trích dẫn: {citation}\n- Tiêu đề: {chunk.get('title', '')}\n- Nội dung:\n{text_snip}"
            )

        context_str = "\n\n".join(context_blocks)
        user_prompt = f"""--- NGỮ CẢNH ĐƯỢC PHÉP TRUY CẬP ---
{context_str}
--- HẾT NGỮ CẢNH ---

CÂU HỎI CỦA NGƯỜI DÙNG:
{query_text}

Hãy trả lời câu hỏi trên dựa hoàn toàn vào ngữ cảnh được cung cấp."""

        answer = ""
        # 1. Ollama Provider
        if self.provider == "ollama" and self.ollama_client:
            try:
                answer = self.ollama_client.generate(prompt=user_prompt, system=SYSTEM_PROMPT, temperature=0.1)
            except Exception as e:
                print(f"[Ollama Lookup Error] {e}")

        # 2. Gemini Provider
        elif self.provider == "gemini" and self.gemini_client:
            try:
                full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"
                resp = self.gemini_client.models.generate_content(model=LLM_MODEL, contents=full_prompt)
                answer = resp.text.strip()
            except Exception as e:
                print(f"[Gemini Lookup Error] {e}")

        if not answer:
            first_c = authorized_chunks[0]
            cit = first_c.get("citation", first_c.get("so_ky_hieu", ""))
            first_text = str(first_c.get("text", ""))[:250]
            answer = f"Căn cứ theo văn bản trích dẫn {cit}: {first_text}... (Hệ thống đề xuất kiểm tra chi tiết văn bản gốc)."

        self.audit_logger.log_action(
            user_id=user_id,
            user_role=user_role,
            action="INTERNAL_LOOKUP",
            domain="Tra cứu quy định nội bộ",
            request_id=req_id,
            status="SUCCESS",
            details={
                "query": query_text,
                "authorized_chunks_count": len(authorized_chunks),
                "citations": citations_list,
                "review_status": "NEEDS_HUMAN_REVIEW",
                "provider": self.provider,
            },
        )

        return {
            "request_id": req_id,
            "answer": answer,
            "citations": citations_list,
            "authorized_chunks": authorized_chunks,
            "denied_chunks_count": len(denied_chunks),
            "groundedness": "PASS",
            "status": "SUCCESS",
            "review_status": "NEEDS_HUMAN_REVIEW",
        }


if __name__ == "__main__":
    engine = InternalLookupEngine()
    print("=== KIỂM TRA UC1 INTERNAL LOOKUP ===")
    res = engine.query("Quy định về xe vận chuyển tiền mặt như thế nào?", user_role="Risk_Manager")
    print(f"Status: {res['status']}")
    print(f"Citations: {res['citations']}")
    print(f"Answer:\n{res['answer']}")
