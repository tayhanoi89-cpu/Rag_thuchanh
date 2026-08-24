from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase


ENTITY_TYPES = {"CoQuan", "NguoiKy", "DoiTuongApDung", "LinhVuc"}
RELATIONSHIP_TYPES = {
    "THAM_CHIEU",
    "SUA_DOI_BO_SUNG",
    "THAY_THE_BOI",
    "BAN_HANH_BOI",
    "KY_BOI",
    "AP_DUNG_CHO",
    "THUOC_LINH_VUC",
}


def text(value: object) -> str:
    return str(value if pd.notna(value) else "").strip()


def records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, object]]:
    return frame.loc[:, columns].fillna("").to_dict("records")


def count_graph(driver: object, database: str) -> tuple[dict[str, int], dict[str, int]]:
    node_records = driver.execute_query(
        "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS total ORDER BY label", database_=database
    ).records
    relationship_records = driver.execute_query(
        "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS total ORDER BY type", database_=database
    ).records
    return (
        {record["label"]: record["total"] for record in node_records},
        {record["type"]: record["total"] for record in relationship_records},
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Import validated legal knowledge graph into Neo4j.")
    parser.add_argument("--documents", default="ner_kb/cleaned_documents.csv")
    parser.add_argument("--entities", default="ner_kb/entities.csv")
    parser.add_argument("--relationships", default="ner_kb/relationships.csv")
    parser.add_argument("--env-file", default="ner_kb/.env")
    parser.add_argument("--error-output", default="ner_kb/neo4j_import_errors.csv")
    args = parser.parse_args()

    documents = pd.read_csv(args.documents, dtype="string")
    entities = pd.read_csv(args.entities, dtype="string")
    relationships = pd.read_csv(args.relationships, dtype="string")
    required_documents = {"id", "title", "so_ky_hieu"}
    required_entities = {"entity_id", "entity_type", "canonical_name"}
    required_relationships = {"source", "target", "target_type", "relationship_type", "method", "confidence", "evidence"}
    for name, frame, required in (
        ("documents", documents, required_documents),
        ("entities", entities, required_entities),
        ("relationships", relationships, required_relationships),
    ):
        if missing := required - set(frame.columns):
            raise ValueError(f"{name} is missing columns: {', '.join(sorted(missing))}")

    document_rows = records(documents, ["id", "title", "so_ky_hieu", "loai_van_ban", "ngay_ban_hanh"])
    entity_rows = entities.drop_duplicates("entity_id")
    entity_rows = records(entity_rows, ["entity_id", "entity_type", "canonical_name"])
    document_ids = set(documents["id"].map(text))
    entity_ids = set(entities["entity_id"].map(text))
    errors: list[dict[str, str]] = []

    load_dotenv(args.env_file)
    required_config = ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DATABASE")
    if missing := [name for name in required_config if not os.getenv(name)]:
        raise RuntimeError(f"Missing Neo4j configuration: {', '.join(missing)}")
    database = os.environ["NEO4J_DATABASE"]
    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
    try:
        driver.verify_connectivity()
        driver.execute_query(
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (document:Document) REQUIRE document.id IS UNIQUE",
            database_=database,
        )
        driver.execute_query(
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (entity:Entity) REQUIRE entity.entity_id IS UNIQUE",
            database_=database,
        )
        driver.execute_query(
            "UNWIND $rows AS row MERGE (document:Document {id: row.id}) SET document += row",
            parameters_={"rows": document_rows},
            database_=database,
        )
        for entity_type in ENTITY_TYPES:
            rows = [row for row in entity_rows if row["entity_type"] == entity_type]
            if not rows:
                continue
            driver.execute_query(
                f"UNWIND $rows AS row MERGE (entity:Entity:{entity_type} {{entity_id: row.entity_id}}) SET entity += row",
                parameters_={"rows": rows},
                database_=database,
            )

        for row in relationships.to_dict("records"):
            source = text(row["source"])
            target = text(row["target"])
            target_type = text(row["target_type"])
            relationship_type = text(row["relationship_type"])
            if source not in document_ids:
                errors.append({"source": source, "target": target, "relationship_type": relationship_type, "reason": "Source document missing"})
                continue
            if relationship_type not in RELATIONSHIP_TYPES:
                errors.append({"source": source, "target": target, "relationship_type": relationship_type, "reason": "Unsupported relationship type"})
                continue
            if target_type == "Document":
                if target not in document_ids:
                    errors.append({"source": source, "target": target, "relationship_type": relationship_type, "reason": "Target document missing"})
                    continue
                target_match = "MATCH (target:Document {id: $target})"
            elif target_type in ENTITY_TYPES:
                if target not in entity_ids:
                    errors.append({"source": source, "target": target, "relationship_type": relationship_type, "reason": "Target entity missing"})
                    continue
                target_match = "MATCH (target:Entity {entity_id: $target})"
            else:
                errors.append({"source": source, "target": target, "relationship_type": relationship_type, "reason": "Unsupported target type"})
                continue
            driver.execute_query(
                f"MATCH (source:Document {{id: $source}}) {target_match} "
                f"MERGE (source)-[relationship:{relationship_type}]->(target) "
                "SET relationship.method = $method, relationship.confidence = $confidence, relationship.evidence = $evidence",
                parameters_={
                    "source": source,
                    "target": target,
                    "method": text(row["method"]),
                    "confidence": float(row["confidence"]),
                    "evidence": text(row["evidence"]),
                },
                database_=database,
            )

        error_path = Path(args.error_output)
        error_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(errors, columns=["source", "target", "relationship_type", "reason"]).to_csv(
            error_path, index=False, encoding="utf-8-sig"
        )
        node_counts, relationship_counts = count_graph(driver, database)
        print("Node counts:")
        for label, total in node_counts.items():
            print(f"{label}: {total}")
        print("Relationship counts:")
        for relationship_type, total in relationship_counts.items():
            print(f"{relationship_type}: {total}")
        print(f"Import errors: {len(errors)}")
        print(f"Wrote import errors to {error_path}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()