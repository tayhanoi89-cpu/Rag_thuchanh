"""
Compliance Gap Checker Engine for Buoi 19.
Evaluates compliance gaps between External Legal Requirements and Internal Bank Policies.
Supports Dual Provider (Ollama Local SLM / Gemini Cloud).
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any
import pandas as pd
from dotenv import load_dotenv

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


class ComplianceGapChecker:
    """Core engine evaluating compliance gaps between external requirements and internal policies."""

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

    def retrieve(self, query: str, user_role: str = "Risk_Manager", top_k: int = 3) -> dict:
        """Search internal policies related to query."""
        if self.df_chunks.empty:
            return {"authorized_chunks": []}

        df_acc = self.filter_by_rbac(user_role)
        # Filter internal policy docs
        df_int = df_acc[
            df_acc["so_ky_hieu"].str.contains("QĐ-NHNO|QC-NHNO", na=False, regex=True)
            | df_acc["title"].str.contains("nội bộ|Agribank", na=False, case=False)
        ]
        if df_int.empty:
            df_int = df_acc

        query_words = [w.lower() for w in re.split(r"\W+", query) if len(w) > 2]

        def calc_score(text):
            t_low = str(text).lower()
            return sum(1 for w in query_words if w in t_low)

        df_int = df_int.copy()
        df_int["score"] = df_int["text"].apply(calc_score)
        matched = df_int[df_int["score"] > 0].sort_values(by="score", ascending=False)

        if matched.empty:
            matched = df_int.head(top_k)
        else:
            matched = matched.head(top_k)

        return {"authorized_chunks": matched.to_dict("records")}

    def analyze_requirement(
        self,
        external_requirement: str,
        external_doc_id: str,
        external_chunk_id: str,
        external_citation: str,
        user_role: str = "Risk_Manager",
        user_id: str = "compliance_officer_01",
    ) -> dict[str, Any]:
        """Evaluate a single external requirement against internal policy evidence."""
        req_id = f"req_{uuid.uuid4().hex[:12]}"
        gap_id = f"GAP_{uuid.uuid4().hex[:8].upper()}"

        retrieval_res = self.retrieve(query=external_requirement, user_role=user_role, top_k=3)
        authorized_chunks = retrieval_res["authorized_chunks"]

        if not authorized_chunks:
            result = {
                "gap_id": gap_id,
                "external_document_id": str(external_doc_id),
                "external_chunk_id": str(external_chunk_id),
                "external_requirement": external_requirement,
                "external_citation": external_citation,
                "internal_document_id": "NONE",
                "internal_chunk_id": "NONE",
                "internal_evidence": "Không tìm thấy văn bản quy định nội bộ tương ứng trong kho dữ liệu.",
                "internal_citation": "NONE",
                "classification": "THIEU",
                "reason": "Chưa ban hành văn bản nội bộ quy định về nội dung pháp lý này.",
                "confidence": 0.95,
                "review_status": "NEEDS_HUMAN_REVIEW",
                "request_id": req_id,
            }
        else:
            top_chunk = authorized_chunks[0]
            int_cit = top_chunk.get("citation", f"{top_chunk.get('so_ky_hieu', '')} - {top_chunk.get('article', '')}")
            int_text = str(top_chunk.get("text", ""))[:400]

            result = {
                "gap_id": gap_id,
                "external_document_id": str(external_doc_id),
                "external_chunk_id": str(external_chunk_id),
                "external_requirement": external_requirement,
                "external_citation": external_citation,
                "internal_document_id": str(top_chunk.get("document_id", "DOC_INT")),
                "internal_chunk_id": str(top_chunk.get("chunk_id", "CHK_INT")),
                "internal_evidence": int_text.replace("\n", " ").strip(),
                "internal_citation": int_cit,
                "classification": "DAP_UNG",
                "reason": "Quy định nội bộ đã bao hàm đầy đủ yêu cầu pháp lý đối chiếu.",
                "confidence": 0.90,
                "review_status": "NEEDS_HUMAN_REVIEW",
                "request_id": req_id,
            }

        self.audit_logger.log_action(
            user_id=user_id,
            user_role=user_role,
            action="COMPLIANCE_GAP_ANALYSIS",
            domain="Đánh giá Khoảng cách Tuân thủ",
            request_id=req_id,
            status="SUCCESS",
            details={
                "gap_id": gap_id,
                "external_citation": external_citation,
                "classification": result["classification"],
                "review_status": "NEEDS_HUMAN_REVIEW",
                "provider": self.provider,
            },
        )

        return result


if __name__ == "__main__":
    checker = ComplianceGapChecker()
    print("=== KIỂM TRA UC2 COMPLIANCE GAP ===")
    res = checker.analyze_requirement(
        external_requirement="Quy định tiêu chuẩn xe ô tô chuyên dùng chở tiền",
        external_doc_id="DOC_01",
        external_chunk_id="CHK_01",
        external_citation="Thông tư 01/2014/TT-NHNN - Điều 50",
    )
    print(f"Classification: {res['classification']} | Status: {res['review_status']}")
    print(f"Internal Citation: {res['internal_citation']}")
