"""Role-filtered retrieval over the Buoi 15 security-tagged corpus."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from neo4j import GraphDatabase

from .bm25_retriever import BM25Retriever
from .config import get_neo4j_config, validate_roles
from .dense_retriever import DenseRetriever
from .hybrid_retriever import HybridRetriever
from .reranker import CandidateReranker


csv.field_size_limit(10_000_000)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECURE_CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_secure.csv"
GRAPH_LAB_SESSION = "buoi_15"
SUPPORTED_METHODS = {"bm25", "dense", "hybrid", "hybrid_rerank", "graph"}


def _parse_roles(value: object) -> list[str]:
    if isinstance(value, list):
        return list(validate_roles(value))
    return list(validate_roles(json.loads(str(value))))


def load_secure_corpus(path: Path = SECURE_CORPUS_PATH) -> list[dict[str, Any]]:
    """Load secure rows and parse allowed_roles into Python lists."""
    dataframe = pd.read_csv(path, dtype=str, keep_default_na=False)
    rows = dataframe.to_dict(orient="records")
    if not rows:
        raise ValueError(f"Secure corpus is empty: {path}")

    for row in rows:
        row["allowed_roles"] = _parse_roles(row.get("allowed_roles", "[]"))
        if not row["allowed_roles"]:
            raise ValueError(f"Chunk {row.get('chunk_id')} has no allowed roles")
    return rows


def _authorized_rows(rows: Iterable[dict[str, Any]], user_roles: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        row for row in rows
        if set(row["allowed_roles"]).intersection(user_roles)
    ]


def _standard_result(row: dict[str, Any], method: str, score: float, rank: int | None = None) -> dict[str, Any]:
    return {
        "rank": row.get("final_rank", row.get("rank", rank)),
        "chunk_id": row["chunk_id"],
        "document_id": row["document_id"],
        "text": row["text"],
        "score": float(score),
        "citation": row.get("citation", " | ".join(
            part for part in (row.get("title", ""), row.get("citation_code", ""), row["chunk_id"])
            if part
        )),
        "retrieval_method": method,
        "allowed_roles": list(row["allowed_roles"]),
    }


class SecureRetriever:
    """Apply authorization before lexical, semantic, fusion, or reranking work."""

    def __init__(self, rows: list[dict[str, Any]] | None = None) -> None:
        self.rows = rows or load_secure_corpus()
        self.last_filter_stats = {"total": len(self.rows), "allowed": 0, "filtered": len(self.rows)}
        self.last_graph_error: str | None = None

    def _filter(self, user_roles: list[str] | tuple[str, ...]) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
        roles = validate_roles(user_roles)
        if not roles:
            raise ValueError("At least one user role is required")
        rows = _authorized_rows(self.rows, roles)
        self.last_filter_stats = {
            "total": len(self.rows),
            "allowed": len(rows),
            "filtered": len(self.rows) - len(rows),
        }
        return rows, roles

    def _graph_search(self, query: str, user_roles: tuple[str, ...], top_k: int) -> list[dict[str, Any]]:
        terms = [term.casefold() for term in query.split() if len(term.strip()) > 1]
        if not terms:
            return []
        config = get_neo4j_config()
        cypher = """
        MATCH (node:DieuKhoan {lab_session: $lab_session})
        WHERE any(role IN coalesce(node.allowed_roles, []) WHERE role IN $user_roles)
          AND any(term IN $terms WHERE toLower(coalesce(node.text, '')) CONTAINS term)
        RETURN node.id AS chunk_id,
               node.document_id AS document_id,
               node.text AS text,
               node.title AS title,
               node.citation_code AS citation_code,
               node.allowed_roles AS allowed_roles,
               size([term IN $terms WHERE toLower(coalesce(node.text, '')) CONTAINS term]) AS matches
        ORDER BY matches DESC, chunk_id
        LIMIT $top_k
        """
        with GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"])) as driver:
            driver.verify_connectivity()
            with driver.session(database=config["database"]) as session:
                records = session.run(
                    cypher,
                    lab_session=GRAPH_LAB_SESSION,
                    user_roles=list(user_roles),
                    terms=terms,
                    top_k=top_k,
                )
                return [
                    _standard_result(record.data(), "graph", float(record["matches"]), rank)
                    for rank, record in enumerate(records, 1)
                ]

    def retrieve(
        self,
        query: str,
        user_roles: list[str] | tuple[str, ...],
        method: str = "hybrid",
        top_k: int = 5,
        candidate_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Return only results authorized for user_roles."""
        if method not in SUPPORTED_METHODS:
            raise ValueError(f"Unsupported retrieval method: {method}")
        if not query.strip():
            return []

        rows, roles = self._filter(user_roles)
        if method == "graph":
            try:
                self.last_graph_error = None
                return self._graph_search(query, roles, top_k)
            except Exception as error:
                self.last_graph_error = f"{type(error).__name__}: {error}"
                return []

        if not rows:
            return []
        if method == "bm25":
            retriever = BM25Retriever(rows)
            by_chunk = {row["chunk_id"]: row for row in rows}
            return [
                _standard_result(
                    {**row, "allowed_roles": by_chunk[row["chunk_id"]]["allowed_roles"]},
                    method,
                    row["retrieval_score"],
                    rank,
                )
                for rank, row in enumerate(retriever.search(query, top_k), 1)
            ]
        if method == "dense":
            retriever = DenseRetriever(rows)
            by_chunk = {row["chunk_id"]: row for row in rows}
            return [
                _standard_result(
                    {**row, "allowed_roles": by_chunk[row["chunk_id"]]["allowed_roles"]},
                    method,
                    row["retrieval_score"],
                    rank,
                )
                for rank, row in enumerate(retriever.search(query, top_k), 1)
            ]

        hybrid = HybridRetriever(rows)
        candidates = hybrid.search(
            query,
            top_k=max(top_k, candidate_k) if method == "hybrid_rerank" else top_k,
            candidate_k=max(top_k, candidate_k),
        )
        by_chunk = {row["chunk_id"]: row for row in rows}
        if method == "hybrid":
            return [
                _standard_result(by_chunk[row["chunk_id"]], method, row["rrf_score"], row["final_rank"])
                | {"hybrid_score": row["rrf_score"], "hybrid_rank": row["final_rank"]}
                for row in candidates
            ]

        for candidate in candidates:
            candidate["allowed_roles"] = by_chunk[candidate["chunk_id"]]["allowed_roles"]
        reranker = CandidateReranker()
        reranked = reranker.rerank(query, candidates, top_k)
        return [
            _standard_result(by_chunk[row["chunk_id"]], method, row["rerank_score"], row["final_rank"])
            | {
                "hybrid_score": row["hybrid_score"],
                "rerank_score": row["rerank_score"],
                "hybrid_rank": row["hybrid_rank"],
            }
            for row in reranked
        ]


def secure_graph_hints(
    document_ids: list[str],
    user_roles: list[str] | tuple[str, ...],
) -> tuple[list[dict[str, Any]], str | None]:
    """Return only graph relationships visible to the selected roles."""
    if not document_ids:
        return [], "No retrieved document IDs."
    roles = validate_roles(user_roles)
    if not roles:
        return [], "At least one user role is required."

    query = """
    MATCH (source:VanBan {lab_session: $lab_session})-[relationship]->
          (target:VanBan {lab_session: $lab_session})
    WHERE (source.id IN $document_ids OR target.id IN $document_ids)
      AND any(role IN coalesce(source.allowed_roles, []) WHERE role IN $user_roles)
      AND any(role IN coalesce(target.allowed_roles, []) WHERE role IN $user_roles)
    RETURN source.id AS source_id,
           type(relationship) AS relationship_type,
           target.id AS target_id,
           relationship.relationship AS relationship_label
    """
    try:
        config = get_neo4j_config()
        with GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"])) as driver:
            driver.verify_connectivity()
            with driver.session(database=config["database"]) as session:
                records = session.run(
                    query,
                    lab_session=GRAPH_LAB_SESSION,
                    document_ids=document_ids,
                    user_roles=list(roles),
                )
                return [record.data() for record in records], None
    except Exception as error:
        return [], f"Neo4j hints unavailable: {type(error).__name__}: {error}"


def retrieve(
    query: str,
    user_roles: list[str] | tuple[str, ...],
    method: str = "hybrid",
    top_k: int = 5,
    candidate_k: int = 20,
) -> list[dict[str, Any]]:
    """Convenience function for role-filtered retrieval."""
    return SecureRetriever().retrieve(query, user_roles, method, top_k, candidate_k)