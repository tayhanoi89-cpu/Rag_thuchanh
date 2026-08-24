from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import time
from pathlib import Path
from typing import Any


VALID_RELATION_TYPES = {
    "CAN_CU",
    "THAY_THE",
    "SUA_DOI_BO_SUNG",
    "HOP_NHAT",
    "GIAI_THE",
    "LIEN_QUAN",
    "KHONG_CO",
}


def strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = html.unescape(raw_html)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def load_metadata(path: Path) -> list[dict[str, Any]]:
    csv.field_size_limit(max(csv.field_size_limit(), 50 * 1024 * 1024))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows


def load_contents(path: Path) -> dict[str, str]:
    csv.field_size_limit(max(csv.field_size_limit(), 50 * 1024 * 1024))
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return {row["id"]: row.get("content_html", "") for row in reader}


def merge_documents(metadata_rows: list[dict[str, Any]], content_map: dict[str, str]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for row in metadata_rows:
        doc_id = row.get("id", "").strip()
        if not doc_id:
            continue
        docs.append(
            {
                "id": doc_id,
                "title": clean_text(row.get("title", "")),
                "so_ky_hieu": clean_text(row.get("so_ky_hieu", "")),
                "loai_van_ban": clean_text(row.get("loai_van_ban", "")),
                "ngay_ban_hanh": clean_text(row.get("ngay_ban_hanh", "")),
                "nganh": clean_text(row.get("nganh", "")),
                "linh_vuc": clean_text(row.get("linh_vuc", "")),
                "co_quan_ban_hanh": clean_text(row.get("co_quan_ban_hanh", "")),
                "content_html": content_map.get(doc_id, ""),
                "content_text": strip_html(content_map.get(doc_id, "")),
            }
        )
    return docs


def title_overlap_score(left: dict[str, Any], right: dict[str, Any]) -> int:
    left_tokens = set(re.findall(r"[\w]+", (left.get("title", "") + " " + left.get("so_ky_hieu", "")).lower()))
    right_tokens = set(re.findall(r"[\w]+", (right.get("title", "") + " " + right.get("so_ky_hieu", "")).lower()))
    overlap = len(left_tokens & right_tokens)
    score = 0
    if left.get("nganh") and left.get("nganh") == right.get("nganh"):
        score += 3
    if left.get("co_quan_ban_hanh") and left.get("co_quan_ban_hanh") == right.get("co_quan_ban_hanh"):
        score += 2
    if left.get("linh_vuc") and left.get("linh_vuc") == right.get("linh_vuc"):
        score += 2
    if overlap > 0:
        score += overlap
    if left.get("loai_van_ban") == right.get("loai_van_ban"):
        score += 1
    return score


def build_candidate_pairs(documents: list[dict[str, Any]], max_pairs: int) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    candidates: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for idx, left in enumerate(documents):
        for right in documents[idx + 1:]:
            score = title_overlap_score(left, right)
            if score > 0:
                candidates.append((score, left, right))
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[:max_pairs]


def build_prompt(left: dict[str, Any], right: dict[str, Any]) -> str:
    left_snippet = left.get("content_text", "")[:1000]
    right_snippet = right.get("content_text", "")[:1000]
    return f"""
Bạn là chuyên gia phân tích văn bản pháp luật tiếng Việt.

Nhiệm vụ: dự đoán xem hai văn bản pháp luật dưới đây có quan hệ pháp lý nào không, và nếu có thì xác định loại quan hệ tốt nhất.

Chỉ trả về một đối tượng JSON hợp lệ với các khóa sau:
- "has_relation": true hoặc false
- "relation_type": một trong {"CAN_CU", "THAY_THE", "SUA_DOI_BO_SUNG", "HOP_NHAT", "GIAI_THE", "LIEN_QUAN", "KHONG_CO"}
- "confidence": số từ 0 đến 1
- "reason": lý do ngắn gọn bằng tiếng Việt

Quy tắc:
1. Dựa trên tiêu đề, mối quan hệ, thời gian, cơ quan ban hành, phạm vi, và nội dung.
2. Nếu không chắc chắn, hãy trả về "has_relation": false và "relation_type": "KHONG_CO".
3. Không suy đoán vượt quá dữ liệu được cung cấp.
4. Trả về đúng định dạng JSON, không thêm văn bản ngoài JSON.

Văn bản A:
- id: {left.get('id')}
- title: {left.get('title')}
- loại văn bản: {left.get('loai_van_ban')}
- kỳ hiệu: {left.get('so_ky_hieu')}
- ngành: {left.get('nganh')}
- lĩnh vực: {left.get('linh_vuc')}
- cơ quan ban hành: {left.get('co_quan_ban_hanh')}
- nội dung: {left_snippet}

Văn bản B:
- id: {right.get('id')}
- title: {right.get('title')}
- loại văn bản: {right.get('loai_van_ban')}
- kỳ hiệu: {right.get('so_ky_hieu')}
- ngành: {right.get('nganh')}
- lĩnh vực: {right.get('linh_vuc')}
- cơ quan ban hành: {right.get('co_quan_ban_hanh')}
- nội dung: {right_snippet}
""".strip()


def require_gemini_sdk():
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency google-generativeai. Install it with: pip install google-generativeai"
        ) from exc
    return genai


def parse_prediction(response_text: str) -> dict[str, Any]:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("Gemini response is not a JSON object.")

    relation_type = str(payload.get("relation_type", "KHONG_CO")).upper()
    if relation_type not in VALID_RELATION_TYPES:
        relation_type = "KHONG_CO"

    has_relation = bool(payload.get("has_relation", relation_type != "KHONG_CO"))
    confidence = float(payload.get("confidence", 0.0))
    reason = str(payload.get("reason", "")).strip()

    return {
        "has_relation": has_relation,
        "relationship_type": relation_type,
        "confidence": max(0.0, min(1.0, confidence)),
        "relationship": reason,
    }


def ask_gemini(api_key: str, prompt: str) -> dict[str, Any]:
    genai = require_gemini_sdk()
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-flash-latest")
    response = model.generate_content(prompt, generation_config={"temperature": 0.1})
    return parse_prediction(response.text or "{}")


def write_predictions_csv(output_path: Path, predictions: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["doc_id", "other_doc_id", "relationship", "relationship_type", "confidence", "has_relation"]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in predictions:
            writer.writerow(row)


def is_rate_limit_error(error: Exception) -> bool:
    return error.__class__.__name__ == "ResourceExhausted"


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict legal relationships among documents using Gemini.")
    parser.add_argument("--data-dir", default="ner_kb", help="Directory containing metadata.csv and content.csv.")
    parser.add_argument("--max-pairs", type=int, default=20, help="Maximum candidate pairs to send to Gemini.")
    parser.add_argument("--output", default="ner_kb/predicted_relationships.csv", help="CSV file to write predicted relationships.")
    parser.add_argument("--api-key", default="", help="Optional Gemini API key. Defaults to GEMINI_API_KEY env var.")
    parser.add_argument("--dry-run", action="store_true", help="Only print top candidate pairs without calling the LLM.")
    parser.add_argument("--max-retries", type=int, default=10, help="Retries per pair after a Gemini rate limit response.")
    parser.add_argument("--retry-delay", type=int, default=60, help="Seconds to wait before retrying a rate-limited Gemini request.")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    metadata_path = data_dir / "metadata.csv"
    content_path = data_dir / "content.csv"

    if not metadata_path.exists() or not content_path.exists():
        raise FileNotFoundError(f"Missing required files in {data_dir}. Expected metadata.csv and content.csv.")

    metadata_rows = load_metadata(metadata_path)
    content_map = load_contents(content_path)
    documents = merge_documents(metadata_rows, content_map)
    candidates = build_candidate_pairs(documents, max_pairs=max(args.max_pairs, 1))

    if args.dry_run:
        print(f"Found {len(candidates)} candidate pairs to evaluate.")
        for score, left, right in candidates[:10]:
            print(f"[{score}] {left['id']} <-> {right['id']} | {left['title']} | {right['title']}")
        return

    api_key = (args.api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not api_key:
        raise RuntimeError("Missing Gemini API key. Pass --api-key or set GEMINI_API_KEY.")

    predictions: list[dict[str, Any]] = []
    output_path = Path(args.output)
    for score, left, right in candidates:
        prompt = build_prompt(left, right)
        for attempt in range(args.max_retries + 1):
            try:
                prediction = ask_gemini(api_key=api_key, prompt=prompt)
                break
            except Exception as error:
                if not is_rate_limit_error(error) or attempt == args.max_retries:
                    raise
                print(
                    f"Gemini rate limit reached for {left['id']} <-> {right['id']}. "
                    f"Retrying in {args.retry_delay} seconds ({attempt + 1}/{args.max_retries})."
                )
                time.sleep(args.retry_delay)
        result = {
            "doc_id": left["id"],
            "other_doc_id": right["id"],
            "relationship": prediction.get("relationship", ""),
            "relationship_type": prediction.get("relationship_type", "KHONG_CO"),
            "confidence": round(float(prediction.get("confidence", 0.0)), 3),
            "has_relation": bool(prediction.get("has_relation", False)),
        }
        predictions.append(result)
        write_predictions_csv(output_path, predictions)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    print(f"Wrote {len(predictions)} predictions to {output_path}")


if __name__ == "__main__":
    main()
