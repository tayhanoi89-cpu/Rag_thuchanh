from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunking_pipeline import build_chunks_from_csv
from embedding_pipeline import collect_texts, embed_chunks
from neo4j_config import build_neo4j_config
from neo4j_import import Neo4jImporter


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def _write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "doc_id",
        "other_doc_id",
        "relationship",
        "relationship_type",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "doc_id": row.get("doc_id", ""),
                "other_doc_id": row.get("other_doc_id", ""),
                "relationship": row.get("relationship", ""),
                "relationship_type": row.get("relationship_type", ""),
            })


def _normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in rows:
        doc_id = row.get("doc_id", "").strip()
        other_doc_id = row.get("other_doc_id", "").strip()
        if not doc_id or not other_doc_id or doc_id == other_doc_id:
            continue
        relationship_type = (row.get("relationship_type") or "RELATED").strip().upper()
        relationship_text = row.get("relationship", "").strip()
        key = (doc_id, other_doc_id, relationship_type)
        merged[key] = {
            "doc_id": doc_id,
            "other_doc_id": other_doc_id,
            "relationship": relationship_text,
            "relationship_type": relationship_type,
        }
    return list(merged.values())


def merge_predictions(base_path: Path, predicted_path: Path, output_path: Path) -> list[dict[str, str]]:
    base_rows = _normalize_rows(_read_csv_rows(base_path))
    predicted_rows = _normalize_rows(_read_csv_rows(predicted_path))

    merged_map: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in base_rows + predicted_rows:
        doc_id = row["doc_id"]
        other_doc_id = row["other_doc_id"]
        relationship_type = row["relationship_type"]
        key = (doc_id, other_doc_id, relationship_type)
        merged_map[key] = row

    merged_rows = list(merged_map.values())
    _write_csv_rows(output_path, merged_rows)
    return merged_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge predicted legal relationships into a graph-ready CSV and import them into Neo4j.")
    parser.add_argument("--data-dir", default="ner_kb", help="Directory containing metadata.csv and content.csv.")
    parser.add_argument("--predictions", default="ner_kb/predicted_relationships.csv", help="CSV file with predicted relationships.")
    parser.add_argument("--output", default="ner_kb/relationships.csv", help="Merged graph-ready CSV output.")
    parser.add_argument("--dry-run", action="store_true", help="Only merge and print summary without importing to Neo4j.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    predictions_path = Path(args.predictions)
    output_path = Path(args.output)

    if not predictions_path.exists():
        raise FileNotFoundError(f"Predictions CSV not found: {predictions_path}")

    merge_rows = merge_predictions(base_path=data_dir / "relationships.csv", predicted_path=predictions_path, output_path=output_path)
    print(f"Merged {len(merge_rows)} relationship rows into {output_path}")

    if args.dry_run:
        for row in merge_rows[:10]:
            print(row)
        return

    config = build_neo4j_config()
    importer = Neo4jImporter(config)
    try:
        importer.ensure_database()
        importer.reset_database()
        documents = build_chunks_from_csv(data_dir)
        chunks = collect_texts(documents)
        embed_chunks(chunks)
        metadata_rows = []
        with (data_dir / "metadata.csv").open("r", encoding="utf-8-sig", newline="") as handle:
            metadata_rows = list(csv.DictReader(handle))
        importer.import_documents(documents, metadata_rows)
        importer.import_relationships(merge_rows)
        print(f"Imported {len(merge_rows)} relationships into Neo4j database {config['database']}")
    finally:
        importer.close()


if __name__ == "__main__":
    main()
