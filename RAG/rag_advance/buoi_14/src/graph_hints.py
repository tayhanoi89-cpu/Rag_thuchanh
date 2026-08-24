"""Optional direct Neo4j hints for documents returned by retrieval."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

from .corpus import PROJECT_ROOT


def direct_graph_hints(document_ids: list[str]) -> tuple[list[dict[str, Any]], str | None]:
    if not document_ids:
        return [], "No retrieved document IDs."
    load_dotenv(PROJECT_ROOT / ".env")
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE") or "neo4j"
    if not uri or not user or not password:
        return [], "Neo4j is not configured in buoi_14/.env."

    query = (
        "MATCH (source:VanBan {lab_session: $lab_session})-[relationship]->"
        "(target:VanBan {lab_session: $lab_session}) "
        "WHERE source.id IN $document_ids OR target.id IN $document_ids "
        "RETURN source.id AS source_id, type(relationship) AS relationship_type, "
        "target.id AS target_id, relationship.relationship AS relationship_label"
    )
    try:
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            driver.verify_connectivity()
            with driver.session(database=database) as session:
                records = session.run(
                    query,
                    lab_session="buoi_14",
                    document_ids=document_ids,
                )
                return [record.data() for record in records], None
    except Exception as error:
        return [], f"Neo4j hints unavailable: {type(error).__name__}: {error}"