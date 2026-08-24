from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd


ENTITY_RELATION_TYPES = {
    "CoQuan": "BAN_HANH_BOI",
    "NguoiKy": "KY_BOI",
    "DoiTuongApDung": "AP_DUNG_CHO",
    "LinhVuc": "THUOC_LINH_VUC",
}


def normalize_reference(value: object) -> str:
    return re.sub(r"\s+", "", str(value if pd.notna(value) else "")).upper()


def has_phrase_and_reference(text: str, phrase: str, reference: str) -> bool:
    return phrase.casefold() in text.casefold() and normalize_reference(reference) in normalize_reference(text)


def extract_document_relations(documents: pd.DataFrame, candidates: pd.DataFrame) -> list[dict[str, object]]:
    by_reference = {
        normalize_reference(row.so_ky_hieu): row.id
        for row in documents.itertuples(index=False)
        if normalize_reference(row.so_ky_hieu)
    }
    by_id = documents.set_index("id")
    relations: list[dict[str, object]] = []
    for candidate in candidates.itertuples(index=False):
        target_id = by_reference.get(normalize_reference(candidate.target_so_ky_hieu))
        if not target_id or candidate.source_id == target_id:
            continue
        source = by_id.loc[candidate.source_id]
        title = str(source.title)
        evidence = str(candidate.evidence).strip()
        if candidate.trigger == "CAN_CU" and has_phrase_and_reference(evidence, "căn cứ", candidate.target_so_ky_hieu):
            relations.append(
                {
                    "source": candidate.source_id,
                    "target": target_id,
                    "target_type": "Document",
                    "relationship_type": "THAM_CHIEU",
                    "method": "rule_can_cu",
                    "confidence": 0.9,
                    "evidence": evidence,
                }
            )
        elif has_phrase_and_reference(title, "sửa đổi", candidate.target_so_ky_hieu):
            relations.append(
                {
                    "source": candidate.source_id,
                    "target": target_id,
                    "target_type": "Document",
                    "relationship_type": "SUA_DOI_BO_SUNG",
                    "method": "rule_title",
                    "confidence": 0.95,
                    "evidence": title,
                }
            )
        elif has_phrase_and_reference(title, "thay thế", candidate.target_so_ky_hieu):
            relations.append(
                {
                    "source": target_id,
                    "target": candidate.source_id,
                    "target_type": "Document",
                    "relationship_type": "THAY_THE_BOI",
                    "method": "rule_title",
                    "confidence": 0.95,
                    "evidence": title,
                }
            )
    return relations


def extract_entity_relations(entities: pd.DataFrame) -> list[dict[str, object]]:
    relations: list[dict[str, object]] = []
    for entity in entities.itertuples(index=False):
        relation_type = ENTITY_RELATION_TYPES.get(entity.entity_type)
        evidence = str(entity.evidence if pd.notna(entity.evidence) else "").strip()
        if not relation_type or not evidence:
            continue
        confidence = pd.to_numeric(entity.confidence, errors="coerce")
        relations.append(
            {
                "source": str(entity.source_doc_id),
                "target": str(entity.entity_id),
                "target_type": entity.entity_type,
                "relationship_type": relation_type,
                "method": str(entity.method),
                "confidence": round(float(confidence) if pd.notna(confidence) else 0.0, 3),
                "evidence": evidence,
            }
        )
    return relations


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Extract raw knowledge-graph relationships from candidates and entities.")
    parser.add_argument("--documents", default="ner_kb/cleaned_documents.csv")
    parser.add_argument("--candidates", default="ner_kb/relation_candidates.csv")
    parser.add_argument("--entities", default="ner_kb/entities.csv")
    parser.add_argument("--enriched-metadata", default="ner_kb/enriched_metadata.csv")
    parser.add_argument("--output", default="ner_kb/relationships_raw.csv")
    args = parser.parse_args()

    documents = pd.read_csv(args.documents, dtype="string")
    candidates = pd.read_csv(args.candidates, dtype="string")
    entities = pd.read_csv(args.entities, dtype="string")
    enriched_metadata = pd.read_csv(args.enriched_metadata, dtype="string")
    required_documents = {"id", "so_ky_hieu", "title"}
    required_candidates = {"source_id", "target_so_ky_hieu", "trigger", "evidence"}
    required_entities = {"entity_id", "entity_type", "source_doc_id", "method", "confidence", "evidence"}
    for name, frame, required in (
        ("documents", documents, required_documents),
        ("candidates", candidates, required_candidates),
        ("entities", entities, required_entities),
        ("enriched metadata", enriched_metadata, {"id"}),
    ):
        if missing := required - set(frame.columns):
            raise ValueError(f"{name} is missing columns: {', '.join(sorted(missing))}")

    relations = extract_document_relations(documents, candidates) + extract_entity_relations(entities)
    relation_frame = pd.DataFrame(
        relations,
        columns=["source", "target", "target_type", "relationship_type", "method", "confidence", "evidence"],
    )
    relation_frame = relation_frame.drop_duplicates(subset=["source", "target", "relationship_type"])
    relation_frame = relation_frame.sort_values(["relationship_type", "source", "target"], kind="stable")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    relation_frame.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("Relations by type:")
    print(relation_frame["relationship_type"].value_counts().to_string() if not relation_frame.empty else "None")
    print("Sample relationships:")
    print(relation_frame.head(10).to_string(index=False) if not relation_frame.empty else "None")
    print(f"Wrote {len(relation_frame)} relationships to {output_path}")


if __name__ == "__main__":
    main()