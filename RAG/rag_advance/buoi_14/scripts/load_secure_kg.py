"""Load the security-tagged corpus into a non-destructive Buoi 15 graph session."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase


csv.field_size_limit(10_000_000)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_neo4j_config, validate_roles


INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "chunks_secure.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "secure_kg_load_report.md"
LAB_SESSION = "buoi_15"
REQUIRED_COLUMNS = {"chunk_id", "document_id", "allowed_roles"}


def read_secure_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError(f"Security-tagged corpus is empty: {path}")
    missing_columns = REQUIRED_COLUMNS - set(rows[0])
    if missing_columns:
        raise ValueError(f"Input CSV is missing required columns: {', '.join(sorted(missing_columns))}")

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        try:
            allowed_roles = list(validate_roles(json.loads(row["allowed_roles"])))
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid allowed_roles for chunk {row.get('chunk_id')}: {error}") from error
        normalized_rows.append(
            {
                "document_id": row["document_id"],
                "chunk_id": row["chunk_id"],
                "allowed_roles": allowed_roles,
                "document_properties": {
                    key: row[key]
                    for key in ("title", "document_type", "effective_date", "status", "citation_code", "issued_date")
                    if row.get(key)
                },
                "clause_properties": {
                    key: row[key]
                    for key in ("text", "source_file", "title", "document_id", "security_class")
                    if row.get(key)
                },
            }
        )
    return normalized_rows


UPSERT_QUERY = """
UNWIND $rows AS row
MERGE (document:VanBan {id: row.document_id, lab_session: $lab_session})
SET document.allowed_roles = row.allowed_roles,
    document += row.document_properties
MERGE (clause:DieuKhoan {id: row.chunk_id, lab_session: $lab_session})
SET clause.allowed_roles = row.allowed_roles,
    clause += row.clause_properties
MERGE (document)-[:CONTAINS {lab_session: $lab_session}]->(clause)
"""

COUNT_QUERY = """
MATCH (node {lab_session: $lab_session})
WHERE node.allowed_roles IS NOT NULL
RETURN count(node) AS count
"""

SAMPLE_QUERY = """
MATCH (document:VanBan {lab_session: $lab_session})
OPTIONAL MATCH (document)-[:CONTAINS {lab_session: $lab_session}]->(clause:DieuKhoan)
RETURN document.id AS document_id,
       document.allowed_roles AS document_allowed_roles,
       clause.id AS clause_id,
       clause.allowed_roles AS clause_allowed_roles
ORDER BY document.id
LIMIT 1
"""


def load_graph(rows: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, Any]]:
    config = get_neo4j_config()
    with GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"])) as driver:
        driver.verify_connectivity()
        with driver.session(database=config["database"]) as session:
            session.run(UPSERT_QUERY, rows=rows, lab_session=LAB_SESSION).consume()
            count = session.run(COUNT_QUERY, lab_session=LAB_SESSION).single()["count"]
            sample_record = session.run(SAMPLE_QUERY, lab_session=LAB_SESSION).single()
            node_counts = {
                label: session.run(
                    f"MATCH (node:{label} {{lab_session: $lab_session}}) RETURN count(node) AS count",
                    lab_session=LAB_SESSION,
                ).single()["count"]
                for label in ("VanBan", "DieuKhoan")
            }
            relationship_count = session.run(
                "MATCH ()-[relationship:CONTAINS {lab_session: $lab_session}]->() "
                "RETURN count(relationship) AS count",
                lab_session=LAB_SESSION,
            ).single()["count"]
    return (
        {"nodes_with_allowed_roles": count, "contains_relationships": relationship_count, **node_counts},
        sample_record.data() if sample_record else {},
    )


def write_report(rows: list[dict[str, Any]], counts: dict[str, int], sample: dict[str, Any]) -> None:
    report = [
        "# Buoi 15 Secure KG Load Report",
        "",
        f"- lab_session: `{LAB_SESSION}`",
        f"- input rows: {len(rows)}",
        f"- VanBan nodes: {counts['VanBan']}",
        f"- DieuKhoan nodes: {counts['DieuKhoan']}",
        f"- CONTAINS relationships: {counts['contains_relationships']}",
        f"- Nodes with allowed_roles: {counts['nodes_with_allowed_roles']}",
        f"- Verification sample: `{sample}`",
        "- Existing graph data was not deleted.",
        "",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    args = parser.parse_args()

    rows = read_secure_rows(args.input)
    counts, sample = load_graph(rows)
    write_report(rows, counts, sample)
    print("SECURE KG LOADED")
    print(f"lab_session: {LAB_SESSION}")
    print(f"input_rows: {len(rows)}")
    print(f"node_counts: VanBan={counts['VanBan']}, DieuKhoan={counts['DieuKhoan']}")
    print(f"contains_relationships: {counts['contains_relationships']}")
    print(f"nodes_with_allowed_roles: {counts['nodes_with_allowed_roles']}")
    print(f"verification_sample: {sample}")
    print(f"report: {REPORT_PATH}")


if __name__ == "__main__":
    main()