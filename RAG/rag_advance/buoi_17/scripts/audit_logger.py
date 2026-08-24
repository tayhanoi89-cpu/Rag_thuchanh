"""Audit Trail Logger for Buoi 17.

Logs all governance, access control, and retrieval actions to audit_log.jsonl.
Complies with financial enterprise audit standards:
- Immutable JSON Lines format
- UTC ISO timestamp
- Strict sanitization of secrets/credentials
- Records both ALLOWED and DENIED events
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BUOI_17_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = BUOI_17_ROOT / "outputs" / "audit_log.jsonl"

# Sensitive patterns to redact if present in queries or metadata
SENSITIVE_PATTERNS = [
    re.compile(r"(password|pwd|secret|token|api_key|apikey|bearer)\s*[:=]\s*['\"]?[^\s'\"]+", re.IGNORECASE),
    re.compile(r"hf_[A-Za-z0-9]{20,}", re.IGNORECASE),
    re.compile(r"AQ\.[A-Za-z0-9_\-]{20,}", re.IGNORECASE),
]


def sanitize_text(text: str) -> str:
    """Mask any accidental tokens, keys or secrets."""
    if not text:
        return ""
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


class AuditLogger:
    """Audit logger writing structured event records to JSONL."""

    def __init__(self, log_path: Path | str | None = None) -> None:
        self.log_path = Path(log_path) if log_path else DEFAULT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        user_id_demo: str,
        user_role: str,
        action: str,
        query: str,
        retrieval_method: str = "hybrid",
        retrieved_document_ids: list[str] | None = None,
        retrieved_chunk_ids: list[str] | None = None,
        citation_ids: list[str] | None = None,
        rbac_filtered_count: int = 0,
        status: str = "SUCCESS",
        request_id: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an audit event. Status must be SUCCESS, DENIED, or ERROR."""
        req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        event = {
            "timestamp": now_utc,
            "request_id": req_id,
            "user_id_demo": user_id_demo,
            "user_role": user_role,
            "action": action,
            "query": sanitize_text(query),
            "retrieval_method": retrieval_method,
            "retrieved_document_ids": retrieved_document_ids or [],
            "retrieved_chunk_ids": retrieved_chunk_ids or [],
            "citation_ids": citation_ids or [],
            "rbac_filtered_count": int(rbac_filtered_count),
            "status": status.upper(),
        }

        if extra_metadata:
            # Sanitize any string values inside extra_metadata
            clean_meta = {}
            for k, v in extra_metadata.items():
                if isinstance(v, str):
                    clean_meta[k] = sanitize_text(v)
                else:
                    clean_meta[k] = v
            event["extra_metadata"] = clean_meta

        # Write to JSONL
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

        return event

    def read_all_logs(self) -> list[dict[str, Any]]:
        """Read all logged events from disk."""
        if not self.log_path.exists():
            return []
        events = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events
