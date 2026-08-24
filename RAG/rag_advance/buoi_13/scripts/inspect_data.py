"""Inspect the seed CSV files used by the Wiki Risk Graph lab."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

CSV_FILES = {
    "risk_profiles_seed.csv": {
        "primary_key": "id",
        "foreign_keys": ["owner_unit_id"],
    },
    "controls_seed.csv": {
        "primary_key": "id",
        "foreign_keys": ["owner_role_id"],
    },
    "risk_events_seed.csv": {
        "primary_key": "id",
        "foreign_keys": ["risk_id"],
    },
    "relationships_seed.csv": {
        "primary_key": None,
        "foreign_keys": ["source_id", "target_id"],
    },
}


def read_csv(file_name: str) -> tuple[list[str], list[dict[str, str]]]:
    path = DATA_DIR / file_name
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
    return reader.fieldnames or [], rows


def print_file_report(file_name: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    config = CSV_FILES[file_name]
    print(f"\n[{file_name}]")
    print(f"rows: {len(rows)}")
    print(f"columns: {', '.join(columns)}")
    print(f"primary_key: {config['primary_key'] or 'none (composite relationship row)'}")

    null_counts = {
        column: sum(not row.get(column, "").strip() for row in rows)
        for column in columns
    }
    null_counts = {column: count for column, count in null_counts.items() if count}
    print(f"nulls: {null_counts or 'none'}")

    primary_key = config["primary_key"]
    if primary_key:
        values = [row.get(primary_key, "") for row in rows]
        duplicates = sorted(value for value, count in Counter(values).items() if value and count > 1)
        print(f"duplicate_{primary_key}: {duplicates or 'none'}")
    else:
        row_keys = [tuple(row.get(column, "") for column in columns) for row in rows]
        duplicate_rows = sum(count - 1 for count in Counter(row_keys).values() if count > 1)
        print(f"duplicate_rows: {duplicate_rows or 'none'}")

    for foreign_key in config["foreign_keys"]:
        values = sorted({row.get(foreign_key, "") for row in rows if row.get(foreign_key, "")})
        print(f"{foreign_key}_sample: {values[:5]}" + (" ..." if len(values) > 5 else ""))

    if file_name == "relationships_seed.csv":
        relationship_types = Counter(row.get("relationship_type", "") for row in rows)
        print(f"relationship_type_counts: {dict(sorted(relationship_types.items()))}")


def check_references(
    datasets: dict[str, tuple[list[str], list[dict[str, str]]]],
) -> None:
    risk_ids = {row["id"] for row in datasets["risk_profiles_seed.csv"][1]}
    control_ids = {row["id"] for row in datasets["controls_seed.csv"][1]}
    event_ids = {row["id"] for row in datasets["risk_events_seed.csv"][1]}
    entity_ids = risk_ids | control_ids | event_ids

    event_orphans = sorted(
        row["risk_id"]
        for row in datasets["risk_events_seed.csv"][1]
        if row["risk_id"] not in risk_ids
    )
    relationship_orphans = sorted(
        {
            value
            for row in datasets["relationships_seed.csv"][1]
            for value in (row["source_id"], row["target_id"])
            if value not in entity_ids
        }
    )

    print("\n[reference_checks]")
    print(f"risk_event_missing_risk_id: {event_orphans or 'none'}")
    print(f"relationship_missing_entity_id: {relationship_orphans or 'none'}")
    print("owner_unit_id: reference-like code in risk profiles; no unit master data found.")
    print("owner_role_id: reference-like code in controls; no role master data found.")


def main() -> None:
    datasets = {}
    for file_name in CSV_FILES:
        path = DATA_DIR / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing required data file: {path}")
        datasets[file_name] = read_csv(file_name)

    print(f"Project root: {PROJECT_ROOT}")
    print("Node types available: RuiRo, KiemSoat, SuKienRuiRo")
    print("Edge types available: MITIGATES, OBSERVED_AS")
    for file_name, (columns, rows) in datasets.items():
        print_file_report(file_name, columns, rows)
    check_references(datasets)


if __name__ == "__main__":
    main()