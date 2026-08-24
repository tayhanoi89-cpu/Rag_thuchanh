"""Load the Buoi 14 mini Knowledge Graph without deleting existing Neo4j data."""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


csv.field_size_limit(10_000_000)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTED_SOURCE_DIR = PROJECT_ROOT.parent / "kb+hops"
FALLBACK_SOURCE_DIR = PROJECT_ROOT.parents[2] / "graph_rag_labs" / "graph_rag_labs" / "kb+hops"
CORPUS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_normalized.csv"
SCHEMA_PATH = PROJECT_ROOT / "cypher" / "schema.cypher"
LAB_SESSION = "buoi_14"
RELATIONSHIP_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def source_dir() -> Path:
    if DOCUMENTED_SOURCE_DIR.exists():
        return DOCUMENTED_SOURCE_DIR
    if FALLBACK_SOURCE_DIR.exists():
        print(f"source_path_fallback: {FALLBACK_SOURCE_DIR}")
        return FALLBACK_SOURCE_DIR
    raise FileNotFoundError("Cannot find the Buoi 14 source CSV directory.")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def properties(row: dict[str, str], extra: dict[str, str] | None = None) -> dict[str, str]:
    values = {key: value for key, value in row.items() if value not in (None, "")}
    if extra:
        values.update(extra)
    return values


def run_schema(session) -> None:
    schema = "\n".join(
        line for line in SCHEMA_PATH.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("//")
    )
    for statement in (part.strip() for part in schema.split(";")):
        if statement:
            session.run(statement).consume()


def load_nodes(session, metadata: list[dict[str, str]], corpus: list[dict[str, str]]) -> None:
    for document in metadata:
        document_props = properties(
            {
                "id": document["id"],
                "title": document.get("title", ""),
                "document_type": document.get("loai_van_ban", ""),
                "status": document.get("tinh_trang_hieu_luc", ""),
                "citation_code": document.get("so_ky_hieu", ""),
                "issued_date": document.get("ngay_ban_hanh", ""),
                "effective_date": document.get("ngay_co_hieu_luc", ""),
            },
            {"lab_session": LAB_SESSION},
        )
        session.run(
            "MERGE (node:VanBan {id: $id, lab_session: $lab_session}) SET node += $properties",
            id=document["id"],
            lab_session=LAB_SESSION,
            properties=document_props,
        ).consume()

    for clause in corpus:
        clause_props = properties(clause, {"lab_session": LAB_SESSION})
        session.run(
            "MERGE (node:DieuKhoan {id: $id, lab_session: $lab_session}) SET node += $properties",
            id=clause["chunk_id"],
            lab_session=LAB_SESSION,
            properties=clause_props,
        ).consume()
        session.run(
            "MATCH (document:VanBan {id: $document_id, lab_session: $lab_session}), "
            "(clause:DieuKhoan {id: $clause_id, lab_session: $lab_session}) "
            "MERGE (document)-[relationship:CONTAINS {lab_session: $lab_session}]->(clause)",
            document_id=clause["document_id"],
            clause_id=clause["chunk_id"],
            lab_session=LAB_SESSION,
        ).consume()


def load_relationships(session, relationships: list[dict[str, str]]) -> list[str]:
    relationship_types = sorted({row["relationship_type"] for row in relationships})
    for relationship in relationships:
        relationship_type = relationship["relationship_type"]
        if not RELATIONSHIP_PATTERN.fullmatch(relationship_type):
            raise ValueError(f"Unsafe relationship type from source data: {relationship_type}")
        query = (
            f"MATCH (source:VanBan {{id: $source_id, lab_session: $lab_session}}), "
            f"(target:VanBan {{id: $target_id, lab_session: $lab_session}}) "
            f"MERGE (source)-[edge:{relationship_type} {{lab_session: $lab_session}}]->(target) "
            "SET edge += $properties"
        )
        session.run(
            query,
            source_id=relationship["doc_id"],
            target_id=relationship["other_doc_id"],
            lab_session=LAB_SESSION,
            properties=properties(relationship, {"source_file": "relationships.csv"}),
        ).consume()
    return relationship_types


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE") or "neo4j"
    if not uri or not user or not password:
        raise RuntimeError("Missing NEO4J_URI, NEO4J_USER, or NEO4J_PASSWORD in buoi_14/.env")

    root = source_dir()
    metadata = read_csv(root / "metadata.csv")
    relationships = read_csv(root / "relationships.csv")
    corpus = read_csv(CORPUS_PATH)
    if {row["id"] for row in metadata} != {row["document_id"] for row in corpus}:
        raise ValueError("Corpus document IDs do not match metadata IDs.")

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session(database=database) as session:
            run_schema(session)
            load_nodes(session, metadata, corpus)
            relationship_types = load_relationships(session, relationships)
            node_counts = {
                label: session.run(
                    f"MATCH (node:{label} {{lab_session: $lab_session}}) RETURN count(node) AS count",
                    lab_session=LAB_SESSION,
                ).single()["count"]
                for label in ("VanBan", "DieuKhoan")
            }
            relationship_counts = {
                relation_type: session.run(
                    f"MATCH ()-[edge:{relation_type} {{lab_session: $lab_session}}]->() RETURN count(edge) AS count",
                    lab_session=LAB_SESSION,
                ).single()["count"]
                for relation_type in ["CONTAINS", *relationship_types]
            }
            orphan_count = session.run(
                "MATCH (node {lab_session: $lab_session}) "
                "WHERE NOT (node)--() RETURN count(node) AS count",
                lab_session=LAB_SESSION,
            ).single()["count"]

    report = [
        "# Buoi 14 Mini KG Build Report",
        "",
        f"- lab_session: `{LAB_SESSION}`",
        f"- source: `{root}`",
        f"- VanBan nodes: {node_counts['VanBan']}",
        f"- DieuKhoan nodes: {node_counts['DieuKhoan']}",
        "- Relationship counts:",
        *[f"  - `{name}`: {count}" for name, count in relationship_counts.items()],
        f"- Orphan nodes: {orphan_count}",
        "- NEXT relations: 0 (not created; article order is not verified in the full-document corpus)",
        "- Existing Neo4j data was not deleted.",
        "",
    ]
    report_path = PROJECT_ROOT / "outputs" / "kg_build_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report), encoding="utf-8")
    print("MINI KG LOADED")
    print(f"nodes: {node_counts}")
    print(f"relationships: {relationship_counts}")
    print(f"orphan_nodes: {orphan_count}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()