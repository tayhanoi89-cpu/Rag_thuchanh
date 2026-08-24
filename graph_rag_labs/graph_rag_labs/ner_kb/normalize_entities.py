from __future__ import annotations

import argparse
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd


CONTROLLED_ALIASES = {
    ("CoQuan", "nhnn"): "Ngân hàng Nhà nước Việt Nam",
    ("CoQuan", "ngân hàng nhà nước"): "Ngân hàng Nhà nước Việt Nam",
}


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFC", str(value if pd.notna(value) else ""))
    return re.sub(r"\s+", " ", text).strip()


def canonical_id(entity_type: str, canonical_name: str) -> str:
    digest = hashlib.sha256(f"{entity_type}|{canonical_name.casefold()}".encode("utf-8")).hexdigest()[:16]
    return f"{entity_type}:{digest}"


def normalize_entities(raw_entities: pd.DataFrame, document_ids: set[str]) -> tuple[pd.DataFrame, list[tuple[str, str, str]]]:
    rows: list[dict[str, object]] = []
    aliases: list[tuple[str, str, str]] = []
    for row in raw_entities.itertuples(index=False):
        entity_type = normalize_text(row.entity_type)
        original_name = normalize_text(row.entity)
        source_doc_id = normalize_text(row.source_doc_id)
        if not entity_type or not original_name or source_doc_id not in document_ids:
            continue
        alias_key = (entity_type, original_name.casefold())
        canonical_name = CONTROLLED_ALIASES.get(alias_key, original_name)
        rows.append(
            {
                "entity_id": canonical_id(entity_type, canonical_name),
                "entity_type": entity_type,
                "canonical_name": canonical_name,
                "original_name": original_name,
                "source_doc_id": source_doc_id,
                "method": normalize_text(row.method),
                "confidence": pd.to_numeric(row.confidence, errors="coerce"),
                "evidence": normalize_text(row.evidence),
            }
        )
        if canonical_name != original_name:
            aliases.append((entity_type, original_name, canonical_name))

    result = pd.DataFrame(
        rows,
        columns=[
            "entity_id",
            "entity_type",
            "canonical_name",
            "original_name",
            "source_doc_id",
            "method",
            "confidence",
            "evidence",
        ],
    )
    if result.empty:
        return result, aliases

    canonical_by_key = (
        result.groupby(["entity_type", result["canonical_name"].str.casefold()])["canonical_name"]
        .agg(lambda values: values.value_counts().index[0])
        .to_dict()
    )
    result["canonical_name"] = result.apply(
        lambda row: canonical_by_key[(row["entity_type"], row["canonical_name"].casefold())], axis=1
    )
    result["entity_id"] = result.apply(lambda row: canonical_id(row["entity_type"], row["canonical_name"]), axis=1)
    result = result.drop_duplicates(
        subset=["source_doc_id", "entity_type", "canonical_name", "method", "evidence"]
    ).sort_values(["entity_type", "canonical_name", "source_doc_id"], kind="stable")
    for row in result.loc[result["original_name"] != result["canonical_name"]].itertuples(index=False):
        aliases.append((row.entity_type, row.original_name, row.canonical_name))
    return result.reset_index(drop=True), sorted(set(aliases))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Normalize extracted legal entities conservatively.")
    parser.add_argument("--raw-input", default="ner_kb/extracted_entities_raw.csv")
    parser.add_argument("--metadata-input", default="ner_kb/enriched_metadata.csv")
    parser.add_argument("--output", default="ner_kb/entities.csv")
    args = parser.parse_args()

    raw_entities = pd.read_csv(args.raw_input, dtype="string")
    enriched_metadata = pd.read_csv(args.metadata_input, dtype={"id": "string"})
    required_raw = {"source_doc_id", "entity", "entity_type", "method", "confidence", "evidence"}
    if missing_columns := required_raw - set(raw_entities.columns):
        raise ValueError(f"Raw entity input is missing: {', '.join(sorted(missing_columns))}")
    if "id" not in enriched_metadata.columns:
        raise ValueError("Enriched metadata input is missing id.")

    document_ids = set(enriched_metadata["id"].map(normalize_text))
    normalized, aliases = normalize_entities(raw_entities, document_ids)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Entities before normalization: {len(raw_entities)}")
    print(f"Entities after normalization: {len(normalized)}")
    print("Aliases merged:")
    print("\n".join(f"{entity_type}: {original} -> {canonical}" for entity_type, original, canonical in aliases) or "None")
    print("Sample entities:")
    print(normalized.head(10).to_string(index=False) if not normalized.empty else "None")
    print(f"Wrote normalized entities to {output_path}")


if __name__ == "__main__":
    main()