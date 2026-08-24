from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv


ENTITY_SPECS = {
    "co_quan": ("CoQuan", "co_quan_ban_hanh"),
    "nguoi_ky": ("NguoiKy", "nguoi_ky"),
    "doi_tuong_ap_dung": ("DoiTuongApDung", "thong_tin_ap_dung"),
    "linh_vuc": ("LinhVuc", "linh_vuc"),
}
UNCLEAR_VALUES = {"", "null", "none", "nan", "chưa phân loại", "chua phan loai"}


def is_unclear(value: object) -> bool:
    return str(value if pd.notna(value) else "").strip().casefold() in UNCLEAR_VALUES


def clean_value(value: object) -> str:
    return str(value if pd.notna(value) else "").strip()


def required_llm_fields(row: pd.Series) -> set[str]:
    fields = {"doi_tuong_ap_dung"}
    for response_field, (_, metadata_column) in ENTITY_SPECS.items():
        if is_unclear(row[metadata_column]):
            fields.add(response_field)
    return fields


def build_prompt(row: pd.Series, fields: set[str]) -> str:
    requested = ", ".join(sorted(fields))
    return f"""
Bạn là chuyên gia trích xuất thực thể từ văn bản pháp luật Việt Nam.

Chỉ trích xuất các trường cần bổ sung: {requested}.
Chỉ tạo thực thể nếu có bằng chứng nguyên văn trong nội dung. Không suy đoán.
Mỗi mục phải có entity, confidence (0 đến 1), evidence. Evidence là đoạn trích nguyên văn ngắn.
Trả về đúng JSON, không thêm markdown:
{{
  "co_quan": [{{"entity": "", "confidence": 0.0, "evidence": ""}}],
  "nguoi_ky": [{{"entity": "", "confidence": 0.0, "evidence": ""}}],
  "doi_tuong_ap_dung": [{{"entity": "", "confidence": 0.0, "evidence": ""}}],
  "linh_vuc": [{{"entity": "", "confidence": 0.0, "evidence": ""}}]
}}
Với trường không được yêu cầu hoặc không có bằng chứng, trả về mảng rỗng.

Metadata gốc:
- Tiêu đề: {clean_value(row['title'])}
- Cơ quan ban hành: {clean_value(row['co_quan_ban_hanh'])}
- Người ký: {clean_value(row['nguoi_ky'])}
- Lĩnh vực: {clean_value(row['linh_vuc'])}

Nội dung:
{clean_value(row['content_clean'])[:6000]}
""".strip()


def parse_response(text: str) -> dict[str, list[dict[str, Any]]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Gemini response is not a JSON object.")
    result: dict[str, list[dict[str, Any]]] = {}
    for field in ENTITY_SPECS:
        values = payload.get(field, [])
        if not isinstance(values, list):
            raise ValueError(f"Gemini response field {field} is not a list.")
        result[field] = [value for value in values if isinstance(value, dict)]
    return result


def call_gemini(client: Any, model: str, prompt: str) -> dict[str, list[dict[str, Any]]]:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": 0.1, "response_mime_type": "application/json"},
    )
    if not response.text:
        raise ValueError("Gemini returned an empty response.")
    return parse_response(response.text)


def append_metadata_entities(row: pd.Series, entities: list[dict[str, Any]]) -> None:
    for response_field, (entity_type, metadata_column) in ENTITY_SPECS.items():
        value = clean_value(row[metadata_column])
        if is_unclear(value):
            continue
        entities.append(
            {
                "source_doc_id": clean_value(row["id"]),
                "entity": value,
                "entity_type": entity_type,
                "source": metadata_column,
                "method": "metadata",
                "confidence": 0.95,
                "evidence": value,
            }
        )


def append_llm_entities(
    row: pd.Series,
    response: dict[str, list[dict[str, Any]]],
    requested_fields: set[str],
    entities: list[dict[str, Any]],
) -> None:
    text = clean_value(row["content_clean"])
    for response_field in requested_fields:
        entity_type, _ = ENTITY_SPECS[response_field]
        for item in response[response_field]:
            entity = clean_value(item.get("entity"))
            evidence = clean_value(item.get("evidence"))
            if not entity or not evidence or evidence.casefold() not in text.casefold():
                continue
            try:
                confidence = float(item.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            entities.append(
                {
                    "source_doc_id": clean_value(row["id"]),
                    "entity": entity,
                    "entity_type": entity_type,
                    "source": "content_clean",
                    "method": "gemini",
                    "confidence": round(max(0.0, min(1.0, confidence)), 3),
                    "evidence": evidence,
                }
            )


def enriched_value(entities: pd.DataFrame, document_id: str, entity_type: str, fallback: str) -> str:
    values = entities.loc[
        (entities["source_doc_id"] == document_id) & (entities["entity_type"] == entity_type), "entity"
    ].drop_duplicates()
    return " | ".join(values.tolist()) if not values.empty else fallback


def write_outputs(
    documents: pd.DataFrame,
    entities: list[dict[str, Any]],
    statuses: dict[str, str],
    errors: dict[str, str],
    entities_path: Path,
    enriched_path: Path,
) -> None:
    columns = ["source_doc_id", "entity", "entity_type", "source", "method", "confidence", "evidence"]
    entity_frame = pd.DataFrame(entities, columns=columns)
    if not entity_frame.empty:
        for column in ("source_doc_id", "entity", "entity_type", "source", "method", "evidence"):
            entity_frame[column] = entity_frame[column].astype("string")
        entity_frame["confidence"] = pd.to_numeric(entity_frame["confidence"], errors="coerce")
        entity_frame = entity_frame.drop_duplicates()
    entity_frame.to_csv(entities_path, index=False, encoding="utf-8-sig")

    enriched = documents.copy()
    for response_field, (entity_type, metadata_column) in ENTITY_SPECS.items():
        enriched[f"{metadata_column}_enriched"] = enriched.apply(
            lambda row: enriched_value(entity_frame, clean_value(row["id"]), entity_type, clean_value(row[metadata_column])),
            axis=1,
        )
    enriched["enrichment_status"] = enriched["id"].map(statuses).fillna("NOT_REQUESTED")
    enriched["enrichment_error"] = enriched["id"].map(errors).fillna("")
    enriched.to_csv(enriched_path, index=False, encoding="utf-8-sig")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Extract legal entities and enrich metadata with Gemini.")
    parser.add_argument("--input", default="ner_kb/cleaned_documents.csv")
    parser.add_argument("--entities-output", default="ner_kb/extracted_entities_raw.csv")
    parser.add_argument("--enriched-output", default="ner_kb/enriched_metadata.csv")
    parser.add_argument("--env-file", default="ner_kb/.env")
    parser.add_argument("--model", default="gemini-flash-latest")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Keep successful results from existing output files.")
    parser.add_argument("--finalize-existing", action="store_true", help="Rewrite resumed checkpoint files without calling Gemini.")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")
    documents = pd.read_csv(input_path, dtype={"id": "string"})
    required_columns = {"id", "title", "content_clean", *[metadata for _, metadata in ENTITY_SPECS.values()]}
    missing_columns = required_columns - set(documents.columns)
    if missing_columns:
        raise ValueError(f"Input is missing columns: {', '.join(sorted(missing_columns))}")

    entities_path = Path(args.entities_output)
    enriched_path = Path(args.enriched_output)
    entities_path.parent.mkdir(parents=True, exist_ok=True)
    enriched_path.parent.mkdir(parents=True, exist_ok=True)
    entities: list[dict[str, Any]] = []
    statuses: dict[str, str] = {}
    errors: dict[str, str] = {}
    if args.resume and entities_path.exists():
        entities = pd.read_csv(entities_path, dtype="string").to_dict("records")
    if args.resume and enriched_path.exists():
        previous = pd.read_csv(enriched_path, dtype="string")
        for row in previous.itertuples(index=False):
            document_id = clean_value(row.id)
            status = clean_value(row.enrichment_status)
            error = clean_value(row.enrichment_error)
            if status:
                statuses[document_id] = status
            if error:
                errors[document_id] = error
    for _, row in documents.iterrows():
        append_metadata_entities(row, entities)

    if args.finalize_existing:
        if not args.resume:
            raise ValueError("--finalize-existing requires --resume.")
        write_outputs(documents, entities, statuses, errors, entities_path, enriched_path)
        print("Finalized existing checkpoint files without calling Gemini.")
        return

    if args.dry_run:
        for _, row in documents.iterrows():
            document_id = clean_value(row["id"])
            statuses[document_id] = "DRY_RUN"
            print(f"{document_id}: Gemini fields = {', '.join(sorted(required_llm_fields(row)))}")
        write_outputs(documents, entities, statuses, errors, entities_path, enriched_path)
        return

    load_dotenv(args.env_file)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from the environment or .env file.")
    from google import genai

    client = genai.Client(api_key=api_key)
    rate_limited = False
    for _, row in documents.iterrows():
        document_id = clean_value(row["id"])
        fields = required_llm_fields(row)
        if statuses.get(document_id) == "SUCCESS":
            continue
        if rate_limited:
            statuses[document_id] = "SKIPPED_RATE_LIMIT"
            errors[document_id] = "Skipped after a Gemini rate-limit response."
            continue
        try:
            response = call_gemini(client, args.model, build_prompt(row, fields))
            append_llm_entities(row, response, fields, entities)
            statuses[document_id] = "SUCCESS"
        except Exception as error:
            message = f"{type(error).__name__}: {error}"[:500]
            statuses[document_id] = "FAILED"
            errors[document_id] = message
            if "RESOURCE_EXHAUSTED" in message.upper() or "429" in message:
                rate_limited = True
        finally:
            write_outputs(documents, entities, statuses, errors, entities_path, enriched_path)

    write_outputs(documents, entities, statuses, errors, entities_path, enriched_path)

    entity_frame = pd.DataFrame(entities)
    success_count = sum(status == "SUCCESS" for status in statuses.values())
    failed_count = len(documents) - success_count
    print(f"Documents successful: {success_count}")
    print(f"Documents failed or skipped: {failed_count}")
    print("Entities by type:")
    print(entity_frame["entity_type"].value_counts().to_string() if not entity_frame.empty else "None")
    print("Metadata enrichments from Gemini:")
    print(entity_frame.loc[entity_frame["method"] == "gemini", "entity_type"].value_counts().to_string() if not entity_frame.empty else "None")
    print("First five enrichment results:")
    print(pd.read_csv(enriched_path, dtype="string").loc[:, ["id", "co_quan_ban_hanh", "co_quan_ban_hanh_enriched", "linh_vuc", "linh_vuc_enriched", "thong_tin_ap_dung_enriched"]].head(5).to_string(index=False))
    if errors:
        print("Errors:")
        for document_id, message in errors.items():
            print(f"{document_id}: {message}")


if __name__ == "__main__":
    main()