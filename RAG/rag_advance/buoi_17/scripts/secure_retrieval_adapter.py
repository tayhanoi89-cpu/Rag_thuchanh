"""Secure Retrieval Adapter for Buoi 17.

Wraps Buoi 16's SecureRetriever without re-implementing core retrieval logic,
normalizing output records to include all required governance and citation attributes.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Iterable

# Add Buoi 14 / Buoi 16 path to Python sys.path
BUOI_17_ROOT = Path(__file__).resolve().parent.parent
BUOI_14_ROOT = BUOI_17_ROOT.parent / "buoi_14"

if str(BUOI_14_ROOT) not in sys.path:
    sys.path.insert(0, str(BUOI_14_ROOT))

from src.config import VALID_ROLES, validate_roles
from src.secure_retriever import SecureRetriever, load_secure_corpus

# Standard role aliases mapping
ROLE_ALIASES: dict[str, str] = {
    "Admin": "Admin",
    "HR": "HR_Manager",
    "HR_Manager": "HR_Manager",
    "Risk_Manager": "Risk_Officer",
    "Risk_Officer": "Risk_Officer",
    "Staff": "Employee",
    "Employee": "Employee",
    "Guest": "Guest",
}


def normalize_roles(roles: str | Iterable[str]) -> list[str]:
    """Normalize role names including aliases (e.g. HR -> HR_Manager)."""
    if isinstance(roles, str):
        roles = [roles]
    normalized: list[str] = []
    for r in roles:
        cleaned = r.strip()
        mapped = ROLE_ALIASES.get(cleaned, cleaned)
        normalized.append(mapped)
    return list(validate_roles(normalized))


class SecureRetrievalAdapter:
    """Adapter wrapping SecureRetriever for Buoi 17."""

    def __init__(self, corpus_path: Path | None = None) -> None:
        if corpus_path:
            self.rows = load_secure_corpus(corpus_path)
            self._retriever = SecureRetriever(rows=self.rows)
        else:
            self._retriever = SecureRetriever()
            self.rows = self._retriever.rows

        # Index metadata by chunk_id for rich attribution
        self.chunk_meta: dict[str, dict[str, Any]] = {row["chunk_id"]: row for row in self.rows}

    @property
    def last_filter_stats(self) -> dict[str, int]:
        return self._retriever.last_filter_stats

    def retrieve(
        self,
        query: str,
        user_roles: str | list[str] | tuple[str, ...],
        method: str = "hybrid",
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Retrieve authorized chunks and standardize the output format.
        
        Output keys:
        - rank: int
        - chunk_id: str
        - document_id: str
        - title: str
        - article: str
        - citation: str
        - allowed_roles: list[str]
        - access_decision: str ("ALLOW")
        - retrieval_method: str
        - score: float
        - text: str
        """
        try:
            norm_roles = normalize_roles(user_roles)
        except ValueError as err:
            # Default Deny on invalid/unknown roles
            self._retriever.last_filter_stats = {
                "total": len(self.rows),
                "allowed": 0,
                "filtered": len(self.rows),
            }
            return []

        raw_results = self._retriever.retrieve(
            query=query,
            user_roles=norm_roles,
            method=method,
            top_k=top_k,
            candidate_k=candidate_k,
        )

        standardized: list[dict[str, Any]] = []
        for res in raw_results:
            chunk_id = res["chunk_id"]
            meta = self.chunk_meta.get(chunk_id, {})
            
            # Extract article identifier if available
            doc_type = meta.get("document_type", "")
            title = meta.get("title", res.get("title", ""))
            citation_code = meta.get("citation_code", "")
            
            # Derive specific citation
            citation = citation_code or title
            
            item = {
                "rank": res.get("rank", len(standardized) + 1),
                "chunk_id": chunk_id,
                "document_id": str(res.get("document_id", meta.get("document_id", ""))),
                "title": title,
                "article": doc_type,
                "citation": citation,
                "citation_code": citation_code,
                "allowed_roles": list(res.get("allowed_roles", meta.get("allowed_roles", []))),
                "access_decision": "ALLOW",
                "retrieval_method": res.get("retrieval_method", method),
                "score": float(res.get("score", 0.0)),
                "text": res.get("text", meta.get("text", "")),
            }
            if "hybrid_score" in res:
                item["hybrid_score"] = res["hybrid_score"]
            if "rerank_score" in res:
                item["rerank_score"] = res["rerank_score"]

            standardized.append(item)

        return standardized

    def build_context(self, retrieved_chunks: list[dict[str, Any]]) -> str:
        """Format authorized chunks into clean context text with citations."""
        if not retrieved_chunks:
            return ""
        context_parts = []
        for item in retrieved_chunks:
            part = (
                f"--- [Tài liệu: {item['citation']} | Chunk: {item['chunk_id']}] ---\n"
                f"Tiêu đề: {item['title']}\n"
                f"Nội dung:\n{item['text']}\n"
            )
            context_parts.append(part)
        return "\n\n".join(context_parts)
