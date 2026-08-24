"""Load normalized Wiki Risk Graph CSV files into Neo4j."""

from __future__ import annotations

import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
SCHEMA_PATH = PROJECT_ROOT / "cypher" / "schema.cypher"

TYPE_LABELS = {
    "RuiRo": "RuiRo",
    "KiemSoat": "KiemSoat",
    "SuKienRuiRo": "SuKienRuiRo",
}
RELATIONSHIP_TYPES = {"MITIGATES", "OBSERVED_AS"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def clean_properties(row: dict[str, str]) -> dict[str, str | float]:
    properties: dict[str, str | float] = {}
    for key, value in row.items():
        if key == "type" or value == "":
            continue
        if key == "confidence":
            properties[key] = float(value)
        else:
            properties[key] = value
    return properties


def load_schema(session) -> None:
    schema = "\n".join(
        line for line in SCHEMA_PATH.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("//")
    )
    statements = [statement.strip() for statement in schema.split(";")]
    for statement in statements:
        if statement:
            session.run(statement).consume()


def load_entities(session, entities: list[dict[str, str]]) -> None:
    for entity in entities:
        label = TYPE_LABELS.get(entity.get("type", ""))
        if label is None:
            raise ValueError(f"Unsupported entity type: {entity.get('type')}")
        query = f"MERGE (node:{label} {{id: $id}}) SET node += $properties"
        session.run(query, id=entity["id"], properties=clean_properties(entity)).consume()


def load_relations(session, relations: list[dict[str, str]], entity_types: dict[str, str]) -> None:
    for relation in relations:
        relationship_type = relation.get("relationship_type", "")
        if relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(f"Unsupported relationship type: {relationship_type}")
        source_id = relation["source_id"]
        target_id = relation["target_id"]
        source_label = TYPE_LABELS[entity_types[source_id]]
        target_label = TYPE_LABELS[entity_types[target_id]]
        query = (
            f"MATCH (source:{source_label} {{id: $source_id}}), "
            f"(target:{target_label} {{id: $target_id}}) "
            f"MERGE (source)-[relationship:{relationship_type}]->(target) "
            "SET relationship += $properties"
        )
        session.run(
            query,
            source_id=source_id,
            target_id=target_id,
            properties=clean_properties(relation),
        ).consume()


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE") or "neo4j"
    if not uri or not user or not password:
        raise RuntimeError("Missing NEO4J_URI, NEO4J_USER, or NEO4J_PASSWORD in .env")

    entities = read_csv(OUTPUT_DIR / "entities.csv")
    relations = read_csv(OUTPUT_DIR / "relations.csv")
    entity_types = {entity["id"]: entity["type"] for entity in entities}
    missing_ids = sorted(
        {
            entity_id
            for relation in relations
            for entity_id in (relation["source_id"], relation["target_id"])
            if entity_id not in entity_types
        }
    )
    if missing_ids:
        raise ValueError(f"Orphan relationship references: {', '.join(missing_ids)}")

    try:
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            driver.verify_connectivity()
            with driver.session(database=database) as session:
                load_schema(session)
                load_entities(session, entities)
                load_relations(session, relations, entity_types)
        print(f"Loaded {len(entities)} entities and {len(relations)} relations into Neo4j.")
    except Exception as error:
        print("Neo4j is unavailable or the load failed.")
        print(f"Error: {error}")
        print("Check that Neo4j is running and .env contains valid connection settings.")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()