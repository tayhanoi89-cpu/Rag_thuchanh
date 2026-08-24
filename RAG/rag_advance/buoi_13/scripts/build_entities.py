"""Normalize seed CSV files into entity and relationship tables."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

ENTITY_SOURCES = (
    ("risk_profiles_seed.csv", "RuiRo"),
    ("controls_seed.csv", "KiemSoat"),
    ("risk_events_seed.csv", "SuKienRuiRo"),
)
RELATION_SOURCE = "relationships_seed.csv"
ENTITY_COLUMNS = [
    "id",
    "type",
    "name",
    "description",
    "source_file",
    "data_origin",
    "verification_status",
]
RELATION_COLUMNS = [
    "source_id",
    "relationship_type",
    "target_id",
    "source",
    "evidence_quote",
    "confidence",
    "verification_status",
    "data_origin",
]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames or [], list(reader)


def build_entity_rows() -> tuple[list[dict[str, str]], list[str]]:
    entity_rows: list[dict[str, str]] = []
    extra_columns: list[str] = []

    for file_name, entity_type in ENTITY_SOURCES:
        columns, rows = read_csv(DATA_DIR / file_name)
        for column in columns:
            if column not in ENTITY_COLUMNS and column not in extra_columns:
                extra_columns.append(column)

        for row in rows:
            display_name = row.get("name") or row.get("description", "")
            description = row.get("description") or row.get("name", "")
            entity_rows.append(
                {
                    **row,
                    "id": row.get("id", ""),
                    "type": entity_type,
                    "name": display_name,
                    "description": description,
                    "source_file": file_name,
                    "data_origin": row.get("data_origin", ""),
                    "verification_status": row.get("verification_status", ""),
                }
            )

    return entity_rows, extra_columns


def build_relation_rows(entity_ids: set[str]) -> list[dict[str, str]]:
    _, relation_rows = read_csv(DATA_DIR / RELATION_SOURCE)
    orphan_ids = sorted(
        {
            value
            for row in relation_rows
            for value in (row.get("source_id", ""), row.get("target_id", ""))
            if value not in entity_ids
        }
    )
    if orphan_ids:
        raise ValueError(f"Orphan relationship references: {', '.join(orphan_ids)}")

    return relation_rows


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    entities, extra_columns = build_entity_rows()
    entity_ids = {row["id"] for row in entities}
    relations = build_relation_rows(entity_ids)

    write_csv(
        OUTPUT_DIR / "entities.csv",
        entities,
        ENTITY_COLUMNS + extra_columns,
    )
    write_csv(OUTPUT_DIR / "relations.csv", relations, RELATION_COLUMNS)

    entity_counts = Counter(row["type"] for row in entities)
    relation_counts = Counter(row["relationship_type"] for row in relations)
    print(f"entities.csv: {len(entities)} entities")
    print(f"entities_by_type: {dict(sorted(entity_counts.items()))}")
    print(f"relations.csv: {len(relations)} relations")
    print(f"relations_by_type: {dict(sorted(relation_counts.items()))}")
    print("orphan_references: none")
    print(f"outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()