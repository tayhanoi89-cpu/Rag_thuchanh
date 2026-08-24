"""Deterministic hierarchy builder for Buổi 09.

This module builds a parent-child hierarchy from hierarchical chunks, writes a
parent store to disk, and exposes read-only status/audit helpers.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
RAG_ROOT = BASE_DIR.parent.parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"
DEFAULT_INPUT_DIR = RAG_ROOT / "rag_foundation" / "buoi_05" / "output" / "chunks"
DEFAULT_STORE_DIR = BASE_DIR / "storage" / "hierarchy"
VALID_STRATEGIES = {"hierarchical"}

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)
if ENV_EXAMPLE_PATH.exists():
    load_dotenv(ENV_EXAMPLE_PATH, override=False)

try:  # pragma: no cover - package import vs direct script execution
    from .rag import load_chunks
except ImportError:  # pragma: no cover
    from rag import load_chunks


QUERY_CACHE: dict[str, dict[str, Any]] = {}


def resolve_input_path(input_path: str | Path | None = None) -> Path:
    """Resolve an input path without depending on the current working directory."""
    if input_path is None:
        return DEFAULT_INPUT_DIR
    candidate = Path(input_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    cwd_candidate = (Path.cwd() / candidate).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (BASE_DIR / candidate).resolve()


def load_runtime_config() -> dict[str, Any]:
    """Load and validate runtime configuration from the local .env files."""
    raw_values = {
        "MULTI_QUERY_COUNT": os.getenv("MULTI_QUERY_COUNT", "3").strip(),
        "MULTI_QUERY_MAX_CHARS": os.getenv("MULTI_QUERY_MAX_CHARS", "300").strip(),
        "MULTI_QUERY_TEMPERATURE": os.getenv("MULTI_QUERY_TEMPERATURE", "0.2").strip(),
        "MULTI_QUERY_ORIGINAL_WEIGHT": os.getenv("MULTI_QUERY_ORIGINAL_WEIGHT", "1.5").strip(),
        "MULTI_QUERY_VARIANT_WEIGHT": os.getenv("MULTI_QUERY_VARIANT_WEIGHT", "1.0").strip(),
        "MULTI_QUERY_RRF_K": os.getenv("MULTI_QUERY_RRF_K", "60").strip(),
        "PER_QUERY_CANDIDATES": os.getenv("PER_QUERY_CANDIDATES", "12").strip(),
        "PARENT_MAX_CHARS": os.getenv("PARENT_MAX_CHARS", "6000").strip(),
        "PARENT_SCORE_CHILD_LIMIT": os.getenv("PARENT_SCORE_CHILD_LIMIT", "3").strip(),
        "PARENT_RRF_K": os.getenv("PARENT_RRF_K", "60").strip(),
        "PARENT_CANDIDATES": os.getenv("PARENT_CANDIDATES", "10").strip(),
        "FINAL_PARENT_TOP_K": os.getenv("FINAL_PARENT_TOP_K", "3").strip(),
        "TOTAL_CONTEXT_MAX_CHARS": os.getenv("TOTAL_CONTEXT_MAX_CHARS", "16000").strip(),
    }

    config = {
        "MULTI_QUERY_COUNT": int(raw_values["MULTI_QUERY_COUNT"]),
        "MULTI_QUERY_MAX_CHARS": int(raw_values["MULTI_QUERY_MAX_CHARS"]),
        "MULTI_QUERY_TEMPERATURE": float(raw_values["MULTI_QUERY_TEMPERATURE"]),
        "MULTI_QUERY_ORIGINAL_WEIGHT": float(raw_values["MULTI_QUERY_ORIGINAL_WEIGHT"]),
        "MULTI_QUERY_VARIANT_WEIGHT": float(raw_values["MULTI_QUERY_VARIANT_WEIGHT"]),
        "MULTI_QUERY_RRF_K": int(raw_values["MULTI_QUERY_RRF_K"]),
        "PER_QUERY_CANDIDATES": int(raw_values["PER_QUERY_CANDIDATES"]),
        "PARENT_MAX_CHARS": int(raw_values["PARENT_MAX_CHARS"]),
        "PARENT_SCORE_CHILD_LIMIT": int(raw_values["PARENT_SCORE_CHILD_LIMIT"]),
        "PARENT_RRF_K": int(raw_values["PARENT_RRF_K"]),
        "PARENT_CANDIDATES": int(raw_values["PARENT_CANDIDATES"]),
        "FINAL_PARENT_TOP_K": int(raw_values["FINAL_PARENT_TOP_K"]),
        "TOTAL_CONTEXT_MAX_CHARS": int(raw_values["TOTAL_CONTEXT_MAX_CHARS"]),
    }

    validate_runtime_config(config)
    return config


def validate_runtime_config(config: dict[str, Any]) -> None:
    """Validate the hierarchy runtime configuration."""
    if not 1 <= int(config.get("MULTI_QUERY_COUNT", 0)) <= 5:
        raise ValueError("MULTI_QUERY_COUNT must be between 1 and 5")
    if not 50 <= int(config.get("MULTI_QUERY_MAX_CHARS", 0)) <= 1000:
        raise ValueError("MULTI_QUERY_MAX_CHARS must be between 50 and 1000")
    temperature = float(config.get("MULTI_QUERY_TEMPERATURE", -1))
    if not 0.0 <= temperature <= 1.0:
        raise ValueError("MULTI_QUERY_TEMPERATURE must be between 0 and 1")
    for key in ("MULTI_QUERY_ORIGINAL_WEIGHT", "MULTI_QUERY_VARIANT_WEIGHT"):
        value = float(config.get(key, -1))
        if value < 0:
            raise ValueError(f"{key} must be non-negative")
    if float(config.get("MULTI_QUERY_ORIGINAL_WEIGHT", 0)) == 0 and float(config.get("MULTI_QUERY_VARIANT_WEIGHT", 0)) == 0:
        raise ValueError("query weights cannot both be zero")
    if int(config.get("MULTI_QUERY_RRF_K", 0)) <= 0:
        raise ValueError("MULTI_QUERY_RRF_K must be positive")
    for key in ("PER_QUERY_CANDIDATES", "PARENT_CANDIDATES"):
        value = int(config.get(key, 0))
        if value <= 0 or value > 100:
            raise ValueError(f"{key} must be between 1 and 100")
    if not 100 <= int(config.get("PARENT_MAX_CHARS", 0)) <= 20000:
        raise ValueError("PARENT_MAX_CHARS must be between 100 and 20000")
    if not 1 <= int(config.get("PARENT_SCORE_CHILD_LIMIT", 0)) <= 20:
        raise ValueError("PARENT_SCORE_CHILD_LIMIT must be between 1 and 20")
    if int(config.get("FINAL_PARENT_TOP_K", 0)) > int(config.get("PARENT_CANDIDATES", 0)):
        raise ValueError("FINAL_PARENT_TOP_K must not exceed PARENT_CANDIDATES")
    if int(config.get("TOTAL_CONTEXT_MAX_CHARS", 0)) < int(config.get("PARENT_MAX_CHARS", 0)):
        raise ValueError("TOTAL_CONTEXT_MAX_CHARS must be at least PARENT_MAX_CHARS")
    for name in ("GEMINI_GENERATION_MODEL", "GEMINI_EMBEDDING_MODEL"):
        value = os.getenv(name, "").strip()
        if not value:
            raise ValueError(f"{name} must not be empty")


def _extract_sequence(chunk_id: str) -> int:
    match = re.search(r"(\d+)$", chunk_id)
    return int(match.group(1)) if match else 0


def _config_matches(config_a: dict[str, Any], config_b: dict[str, Any]) -> bool:
    common_keys = set(config_a.keys()) & set(config_b.keys())
    if not common_keys:
        return False
    return all(str(config_a.get(key)) == str(config_b.get(key)) for key in sorted(common_keys))


def _extract_heading_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:5]:
        match = re.match(r"^(?:#{1,6}\s*)?(Điều|Khoản|Điểm)\s+(\d+)(?:\.)?\s*(.*)$", line)
        if not match:
            continue
        remainder = match.group(3).strip()
        if remainder:
            words = [word for word in re.split(r"\s+", remainder) if word]
            if len(words) > 6:
                continue
            if re.search(r"[?.,;:]", remainder):
                pass
        candidates.append(f"{match.group(1)} {match.group(2)}")
    return candidates


def _normalize_structure(structure: Any, record_name: str) -> dict[str, str | None]:
    if structure is None:
        return {"chapter": None, "article": None, "clause": None, "point": None}
    if not isinstance(structure, dict):
        raise ValueError(f"Invalid structure for {record_name}: expected an object")
    normalized = {}
    for key in ("chapter", "article", "clause", "point"):
        value = structure.get(key)
        if value is None:
            normalized[key] = None
        elif isinstance(value, str) and value.strip():
            normalized[key] = value.strip()
        else:
            raise ValueError(f"Invalid structure value for {record_name}.{key}")
    return normalized


def _materialize_child_record(record: dict[str, Any], record_name: str, source_state: dict[str, Any]) -> dict[str, Any]:
    source = str(record.get("source", "")).strip()
    if not source:
        raise ValueError(f"Invalid source for {record_name}")
    chunk_id = str(record.get("chunk_id", "")).strip()
    if not chunk_id:
        raise ValueError(f"Invalid chunk_id for {record_name}")
    page_start = record.get("page_start")
    page_end = record.get("page_end")
    if not isinstance(page_start, int) or page_start <= 0:
        raise ValueError(f"Invalid page_start for {record_name}")
    if not isinstance(page_end, int) or page_end < page_start:
        raise ValueError(f"Invalid page_end for {record_name}")
    text = record.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"Invalid text for {record_name}")

    structure = _normalize_structure(record.get("structure"), record_name)
    structural_path = {"chapter": None, "article": None, "clause": None, "point": None}
    resolution_method = "document_fallback"
    warnings: list[str] = []
    ambiguous = False

    metadata_article = structure.get("article")
    metadata_chapter = structure.get("chapter")
    heading_candidates = _extract_heading_candidates(text)

    if metadata_article:
        structural_path["article"] = metadata_article
        structural_path["chapter"] = metadata_chapter
        resolution_method = "metadata"
        if heading_candidates and heading_candidates[0] != metadata_article:
            ambiguous = True
            warnings.append("conflict:metadata_vs_heading")
        elif len(heading_candidates) > 1:
            ambiguous = True
            warnings.append("conflict:multiple_headings")
    elif len(heading_candidates) == 1:
        structural_path["article"] = heading_candidates[0]
        resolution_method = "heading_inferred"
        if metadata_chapter:
            structural_path["chapter"] = metadata_chapter
    elif len(heading_candidates) > 1:
        ambiguous = True
        warnings.append("conflict:multiple_headings")
    elif metadata_chapter:
        structural_path["chapter"] = metadata_chapter
        resolution_method = "document_fallback"
    else:
        if source_state.get("previous_article") and not re.search(r"\bĐiều\s+\d+\b", text):
            structural_path["article"] = source_state["previous_article"]
            resolution_method = "carried_forward"
        elif source_state.get("previous_article"):
            resolution_method = "document_fallback"
        else:
            resolution_method = "document_fallback"

    if structure and any(structure.get(key) for key in ("clause", "point")):
        structural_path["clause"] = structure.get("clause")
        structural_path["point"] = structure.get("point")

    if source_state.get("previous_article") and resolution_method == "document_fallback" and not structural_path.get("article") and not structural_path.get("chapter") and not re.search(r"\bĐiều\s+\d+\b", text):
        structural_path["article"] = source_state["previous_article"]
        resolution_method = "carried_forward"

    if structural_path.get("article") and source_state.get("previous_article") and structural_path["article"] != source_state["previous_article"]:
        ambiguous = True
        warnings.append("conflict:carry_forward")

    if not structural_path.get("article") and not structural_path.get("chapter") and re.search(r"\bĐiều\s+\d+\b", text):
        if re.search(r"^\s*(Điều|Khoản|Điểm)\s+\d+", text):
            warnings.append("inline_legal_reference_not_heading")
            ambiguous = True
        else:
            warnings.append("inline_legal_reference_not_heading")
            ambiguous = True

    if not structural_path.get("article") and not structural_path.get("chapter") and source_state.get("previous_article"):
        previous_article = source_state["previous_article"]
        inline_reference = re.search(r"\b(Điều|Khoản|Điểm)\s+(\d+)\b", text)
        if inline_reference and previous_article != f"{inline_reference.group(1)} {inline_reference.group(2)}":
            resolution_method = "document_fallback"
        else:
            structural_path["article"] = previous_article
            resolution_method = "carried_forward"

    child = {
        "child_id": chunk_id,
        "parent_id": "",
        "source": source,
        "page_start": page_start,
        "page_end": page_end,
        "text": text,
        "structural_path": structural_path,
        "resolution_method": resolution_method,
        "ambiguous": ambiguous,
        "warnings": warnings,
        "chapter_label": structural_path.get("chapter"),
        "article_label": structural_path.get("article"),
        "clause_label": structural_path.get("clause"),
        "point_label": structural_path.get("point"),
    }

    if structural_path.get("article") and resolution_method in {"metadata", "heading_inferred", "carried_forward"}:
        source_state["previous_article"] = structural_path["article"]
    return child


def _normalize_query_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", (text or "").strip())
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _normalize_for_dedup(text: str) -> str:
    normalized = _normalize_query_text(text).casefold()
    normalized = re.sub(r"[^\w\sÀ-ỹ]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _extract_legal_reference(text: str) -> str | None:
    match = re.search(r"\b(Điều|Khoản|Điểm)\s+\d+\b", text)
    return match.group(0) if match else None


def _build_generated_query_from_model(question: str, config: dict[str, Any], model: str, query_generator_fn: Any) -> dict[str, Any]:
    if query_generator_fn is not None:
        payload = query_generator_fn(question, config, model)
        if not isinstance(payload, dict):
            raise ValueError("query_generator_fn must return a dictionary")
        return payload

    try:
        from google import genai  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("google.genai is not installed; provide query_generator_fn in tests or install the dependency") from exc

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=api_key)
    prompt = (
        "Bạn là trợ lý tạo các biến thể truy vấn tìm kiếm tiếng Việt cho văn bản pháp luật. "
        "Chỉ trả về JSON với schema tối thiểu {\"queries\": [{\"text\": \"...\", \"focus\": \"...\"}]}. "
        f"Câu hỏi gốc: {question}"
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "temperature": float(config.get("MULTI_QUERY_TEMPERATURE", 0.2)),
            "response_mime_type": "application/json",
        },
    )
    if not hasattr(response, "text"):
        raise RuntimeError("Gemini returned no text payload")
    payload = json.loads(response.text)
    if not isinstance(payload, dict):
        raise RuntimeError("Gemini returned invalid JSON payload")
    return payload


def generate_query_set(
    question: str,
    config: dict[str, Any] | None = None,
    query_generator_fn: Any = None,
    bypass_cache: bool = False,
) -> dict[str, Any]:
    """Create a validated multi-query set with Q0 plus generated variants."""
    runtime_config = load_runtime_config() if config is None else {**load_runtime_config(), **config}
    validate_runtime_config(runtime_config)

    original_question = _normalize_query_text(question)
    if not original_question:
        return {
            "original_question": "",
            "queries": [],
            "model": os.getenv("GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite"),
            "generation_latency_ms": 0.0,
            "status": "query_generation_unavailable",
            "error": "question must not be empty",
        }

    if len(original_question) > 5000:
        return {
            "original_question": original_question,
            "queries": [],
            "model": os.getenv("GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite"),
            "generation_latency_ms": 0.0,
            "status": "query_generation_unavailable",
            "error": "question exceeds reasonable length",
        }

    model_name = os.getenv("GEMINI_GENERATION_MODEL", "gemini-3.5-flash-lite").strip() or "gemini-3.5-flash-lite"
    cache_key = hashlib.sha256(
        json.dumps(
            {
                "question": original_question,
                "config": runtime_config,
                "model": model_name,
            },
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if not bypass_cache and cache_key in QUERY_CACHE:
        cached = copy.deepcopy(QUERY_CACHE[cache_key])
        cached["cache_hit"] = True
        return cached

    start_time = time.perf_counter()
    try:
        payload = _build_generated_query_from_model(original_question, runtime_config, model_name, query_generator_fn)
    except Exception as exc:  # pragma: no cover - runtime path
        return {
            "original_question": original_question,
            "queries": [],
            "model": model_name,
            "generation_latency_ms": round((time.perf_counter() - start_time) * 1000.0, 3),
            "status": "query_generation_unavailable",
            "error": str(exc),
        }

    generation_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 3)
    generated_items = payload.get("queries") if isinstance(payload, dict) else None
    if not isinstance(generated_items, list):
        return {
            "original_question": original_question,
            "queries": [],
            "model": model_name,
            "generation_latency_ms": generation_latency_ms,
            "status": "query_generation_unavailable",
            "error": "model response must include a queries array",
        }

    max_generated = int(runtime_config.get("MULTI_QUERY_COUNT", 3))
    max_chars = int(runtime_config.get("MULTI_QUERY_MAX_CHARS", 300))
    allowed_focus = {"exact_legal_terms", "paraphrase", "missing_aspect"}

    seen = {_normalize_for_dedup(original_question)}
    valid_generated: list[dict[str, Any]] = []
    dropped_duplicate_count = 0

    for item in generated_items:
        if not isinstance(item, dict):
            continue
        text = _normalize_query_text(item.get("text", ""))
        if not text or len(text) > max_chars:
            continue
        focus = (item.get("focus") or "paraphrase").strip()
        if focus not in allowed_focus:
            focus = "paraphrase"
        dedup_key = _normalize_for_dedup(text)
        if dedup_key in seen:
            dropped_duplicate_count += 1
            continue
        seen.add(dedup_key)
        valid_generated.append({"text": text, "focus": focus})
        if len(valid_generated) >= max_generated:
            break

    if not valid_generated:
        reference = _extract_legal_reference(original_question)
        if reference:
            fallback_text = f"{reference} {original_question}"
            fallback_text = _normalize_query_text(fallback_text)
            if len(fallback_text) <= max_chars:
                valid_generated.append({"text": fallback_text, "focus": "exact_legal_terms"})

    if not valid_generated:
        return {
            "original_question": original_question,
            "queries": [],
            "model": model_name,
            "generation_latency_ms": generation_latency_ms,
            "status": "query_generation_unavailable",
            "error": "model returned no valid generated queries",
        }

    if len(valid_generated) < max_generated:
        reference = _extract_legal_reference(original_question)
        if reference and not any(_extract_legal_reference(item["text"]) for item in valid_generated):
            fallback_text = f"{reference} {original_question}"
            fallback_text = _normalize_query_text(fallback_text)
            if len(fallback_text) <= max_chars:
                valid_generated.append({"text": fallback_text, "focus": "exact_legal_terms"})

    queries = [
        {
            "query_id": "Q0",
            "text": original_question,
            "origin": "original",
            "focus": "original_intent",
        }
    ]
    for index, item in enumerate(valid_generated[:max_generated], start=1):
        queries.append(
            {
                "query_id": f"Q{index}",
                "text": item["text"],
                "origin": "generated",
                "focus": item["focus"],
            }
        )

    result = {
        "original_question": original_question,
        "queries": queries,
        "model": model_name,
        "generation_latency_ms": generation_latency_ms,
        "status": "ready",
        "dropped_duplicate_count": dropped_duplicate_count,
        "cache_hit": False,
    }
    QUERY_CACHE[cache_key] = copy.deepcopy(result)
    return result


def multi_child_retrieval(
    query_set: dict[str, Any],
    config: dict[str, Any] | None = None,
    hybrid_retriever_fn: Any = None,
) -> dict[str, Any]:
    """Run per-query hybrid retrieval and fuse results with cross-query RRF."""
    runtime_config = load_runtime_config() if config is None else {**load_runtime_config(), **config}
    validate_runtime_config(runtime_config)

    queries = query_set.get("queries", []) if isinstance(query_set, dict) else []
    if not queries:
        return {
            "status": "retrieval_unavailable",
            "error": "query set is empty",
            "query_count_requested": 0,
            "query_count_executed": 0,
            "query_count_failed": 0,
            "merged_children": [],
            "query_results": [],
            "trace": {},
        }

    if not isinstance(query_set.get("queries"), list):
        return {
            "status": "retrieval_unavailable",
            "error": "query set must contain a queries list",
            "query_count_requested": 0,
            "query_count_executed": 0,
            "query_count_failed": 0,
            "merged_children": [],
            "query_results": [],
            "trace": {},
        }

    max_candidates = int(runtime_config.get("PER_QUERY_CANDIDATES", 12))
    k = int(runtime_config.get("MULTI_QUERY_RRF_K", 60))
    original_weight = float(runtime_config.get("MULTI_QUERY_ORIGINAL_WEIGHT", 1.5))
    variant_weight = float(runtime_config.get("MULTI_QUERY_VARIANT_WEIGHT", 1.0))

    per_query_results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    executed = 0
    failed = 0

    for query in queries:
        query_id = query.get("query_id", "")
        text = query.get("text", "")
        if not text:
            continue
        if not query_id:
            continue
        if query_id == "Q0":
            weight = original_weight
        else:
            weight = variant_weight
        try:
            if hybrid_retriever_fn is None:
                raise RuntimeError("hybrid_retriever_fn is required")
            result = hybrid_retriever_fn(text, runtime_config, query_id, strategy="hierarchical")
            if not isinstance(result, list):
                raise RuntimeError("hybrid_retriever_fn must return a list")
            trimmed = []
            for item in result[:max_candidates]:
                if not isinstance(item, dict):
                    continue
                child_id = str(item.get("child_id", "")).strip()
                if not child_id:
                    continue
                normalized = dict(item)
                normalized["query_id"] = query_id
                normalized["weight"] = weight
                normalized["inner_rrf_rank"] = int(item.get("inner_rrf_rank", 0) or 0)
                normalized["trace"] = {"query_id": query_id, "query_text": text, "inner_rrf_rank": normalized["inner_rrf_rank"]}
                trimmed.append(normalized)
            per_query_results.append({"query_id": query_id, "weight": weight, "hits": trimmed, "status": "executed"})
            executed += 1
        except Exception as exc:  # pragma: no cover - runtime path
            failed += 1
            errors.append({"query_id": query_id, "error": str(exc)})

    if len(per_query_results) == 0 and failed == 0:
        return {
            "status": "retrieval_unavailable",
            "error": "no valid queries were executed",
            "query_count_requested": len(queries),
            "query_count_executed": executed,
            "query_count_failed": failed,
            "merged_children": [],
            "query_results": per_query_results,
            "errors": errors,
            "trace": {},
        }

    if not any(item["query_id"] == "Q0" for item in per_query_results):
        return {
            "status": "retrieval_unavailable",
            "error": "Q0 retrieval failed",
            "query_count_requested": len(queries),
            "query_count_executed": executed,
            "query_count_failed": failed,
            "merged_children": [],
            "query_results": per_query_results,
            "errors": errors,
            "trace": {},
        }

    merged_by_child: dict[str, dict[str, Any]] = {}
    for query_result in per_query_results:
        for hit in query_result.get("hits", []):
            child_id = str(hit.get("child_id", "")).strip()
            if not child_id:
                continue
            existing = merged_by_child.get(child_id)
            if existing is None:
                existing = {
                    "child_id": child_id,
                    "text": hit.get("text", ""),
                    "source": hit.get("source", ""),
                    "page_start": hit.get("page_start"),
                    "page_end": hit.get("page_end"),
                    "multi_query_rrf_score": 0.0,
                    "multi_query_rank": 0,
                    "support_query_count": 0,
                    "support_query_ids": [],
                    "per_query_ranks": {},
                    "per_query_trace": {},
                }
                merged_by_child[child_id] = existing
            if existing.get("source") and hit.get("source") and str(existing.get("source")) != str(hit.get("source")):
                return {
                    "status": "retrieval_unavailable",
                    "error": f"metadata mismatch for child {child_id}",
                    "query_count_requested": len(queries),
                    "query_count_executed": executed,
                    "query_count_failed": failed,
                    "merged_children": [],
                    "query_results": per_query_results,
                    "errors": errors,
                    "trace": {},
                }
            if existing.get("text") and hit.get("text") and str(existing.get("text")) != str(hit.get("text")):
                return {
                    "status": "retrieval_unavailable",
                    "error": f"metadata mismatch for child {child_id}",
                    "query_count_requested": len(queries),
                    "query_count_executed": executed,
                    "query_count_failed": failed,
                    "merged_children": [],
                    "query_results": per_query_results,
                    "errors": errors,
                    "trace": {},
                }
            rank = int(hit.get("inner_rrf_rank", 0) or 0)
            if rank <= 0:
                rank = 999999
            score = query_result["weight"] / float(k + rank)
            existing["multi_query_rrf_score"] += score
            existing["support_query_count"] += 1
            existing["support_query_ids"].append(query_result["query_id"])
            existing["per_query_ranks"][query_result["query_id"]] = rank
            existing["per_query_trace"][query_result["query_id"]] = hit.get("trace", {})

    merged_children = list(merged_by_child.values())
    for child in merged_children:
        child["support_query_ids"] = [qid for qid in [query.get("query_id") for query in queries if query.get("query_id")] if qid in child["support_query_ids"]]
        child["support_query_count"] = len(child["support_query_ids"])
        child["best_query_rank"] = min(child["per_query_ranks"].values()) if child["per_query_ranks"] else 0
        child["multi_query_rank"] = 0

    merged_children.sort(key=lambda item: (-item["multi_query_rrf_score"], item["support_query_count"], item["best_query_rank"], item["child_id"]))
    for index, child in enumerate(merged_children, start=1):
        child["multi_query_rank"] = index

    overlap_distribution = {}
    for child in merged_children:
        count = child["support_query_count"]
        overlap_distribution[count] = overlap_distribution.get(count, 0) + 1

    status = "ready"
    if errors and executed > 0:
        status = "partial"
    elif errors:
        status = "retrieval_unavailable"

    trace = {
        "query_count_requested": len(queries),
        "query_count_valid": len([query for query in queries if query.get("text")]),
        "query_count_executed": executed,
        "query_count_failed": failed,
        "generated_query_latency_ms": {},
        "retrieval_latency_ms": {},
        "result_count_per_query": {item["query_id"]: len(item["hits"]) for item in per_query_results},
        "union_child_count": len(merged_children),
        "overlap_distribution": overlap_distribution,
        "fusion_latency_ms": 0.0,
        "gemini_expansion_call_count": 0,
        "semantic_embedding_call_count": 0,
    }

    return {
        "status": status,
        "query_count_requested": len(queries),
        "query_count_executed": executed,
        "query_count_failed": failed,
        "merged_children": merged_children,
        "query_results": per_query_results,
        "errors": errors,
        "trace": trace,
    }


def build_hierarchy(input_path: str | Path | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a deterministic hierarchy registry from the input chunks."""
    runtime_config = load_runtime_config() if config is None else {**load_runtime_config(), **config}
    validate_runtime_config(runtime_config)

    input_location = resolve_input_path(input_path)
    payload = load_chunks(input_location, strategy="hierarchical")
    records = payload.get("chunks", [])
    if not records:
        raise ValueError("No hierarchical chunks were found")

    records_by_source: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        source = str(record.get("source", "")).strip()
        if not source:
            raise ValueError(f"Missing source in record {record.get('chunk_id', '<unknown>')}")
        records_by_source.setdefault(source, []).append(record)

    ordered_children: list[dict[str, Any]] = []
    for source in sorted(records_by_source):
        source_records = sorted(records_by_source[source], key=lambda item: _extract_sequence(str(item.get("chunk_id", ""))))
        source_state = {"previous_article": None}
        for record in source_records:
            child = _materialize_child_record(record, f"{record.get('chunk_id', '<unknown>')}", source_state)
            ordered_children.append(child)

    ordered_children = sorted(ordered_children, key=lambda item: (_extract_sequence(str(item.get("child_id", ""))), item.get("source", "")))

    parents: list[dict[str, Any]] = []
    child_groups: list[tuple[str, list[dict[str, Any]]]] = []
    for source in sorted({child["source"] for child in ordered_children}):
        source_children = [child for child in ordered_children if child["source"] == source]
        current_group_key = None
        current_group_children: list[dict[str, Any]] = []
        for child in source_children:
            article_key = child.get("article_label") or "document_fallback"
            group_key = f"{source}|{article_key}"
            if current_group_key is None or group_key != current_group_key:
                if current_group_children:
                    child_groups.append((current_group_key, current_group_children))
                current_group_key = group_key
                current_group_children = []
            current_group_children.append(child)
        if current_group_children:
            child_groups.append((current_group_key, current_group_children))

    parent_counter = 0
    for _, group_children in child_groups:
        window_children: list[dict[str, Any]] = []
        window_texts: list[str] = []
        windows: list[list[dict[str, Any]]] = []
        for child in group_children:
            child_text = child["text"].strip()
            if len(child_text) > int(runtime_config.get("PARENT_MAX_CHARS", 6000)):
                if window_children:
                    windows.append(window_children)
                    window_children = []
                windows.append([child])
                continue
            if window_children and sum(len(item["text"].strip()) for item in window_children) + len(child_text) + 2 > int(runtime_config.get("PARENT_MAX_CHARS", 6000)):
                windows.append(window_children)
                window_children = []
            window_children.append(child)
        if window_children:
            windows.append(window_children)

        for index, window in enumerate(windows, start=1):
            parent_counter += 1
            window_text = "\n\n".join(item["text"].strip() for item in window)
            article_key = window[0].get("article_label") or "document_fallback"
            parent_id = hashlib.sha256(f"{window[0]['source']}|{article_key}|{parent_counter}".encode("utf-8")).hexdigest()[:16]
            parent = {
                "parent_id": parent_id,
                "source": window[0]["source"],
                "page_start": min(item["page_start"] for item in window),
                "page_end": max(item["page_end"] for item in window),
                "article_key": article_key,
                "window_index": index,
                "child_ids": [item["child_id"] for item in window],
                "text": window_text,
                "char_count": len(window_text),
                "ambiguous_child_count": sum(1 for item in window if item.get("ambiguous")),
                "warnings": [],
                "structural_path": {
                    "chapter": window[0].get("structural_path", {}).get("chapter"),
                    "article": window[0].get("structural_path", {}).get("article"),
                    "clause": window[0].get("structural_path", {}).get("clause"),
                    "point": window[0].get("structural_path", {}).get("point"),
                },
            }
            for item in window:
                item["parent_id"] = parent_id
            parents.append(parent)

    children = ordered_children
    for child in children:
        if not child.get("parent_id"):
            child["parent_id"] = ""

    return {
        "children": children,
        "parents": parents,
        "config": runtime_config,
    }


def build_store(input_path: str | Path | None = None, output_dir: str | Path | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the hierarchy store and write children/parents/manifest atomically."""
    output_location = Path(output_dir or DEFAULT_STORE_DIR).resolve()
    output_location.mkdir(parents=True, exist_ok=True)

    hierarchy = build_hierarchy(input_path=input_path, config=config)
    children = hierarchy["children"]
    parents = hierarchy["parents"]

    payloads = {
        "children.json": children,
        "parents.json": parents,
    }

    for file_name, payload in payloads.items():
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(output_location), delete=False) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                tmp_path = Path(handle.name)
            os.replace(tmp_path, output_location / file_name)
        finally:
            if tmp_path is not None and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    manifest = {
        "schema_version": 1,
        "strategy": "hierarchical",
        "input_file_fingerprints": {},
        "config_identity": hierarchy["config"],
        "counts": {
            "child_count": len(children),
            "parent_count": len(parents),
            "warning_count": sum(len(child.get("warnings", [])) for child in children),
        },
        "warning_counts": {},
        "build_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    input_location = resolve_input_path(input_path)
    if input_location.is_file():
        manifest["input_file_fingerprints"][input_location.name] = hashlib.sha256(input_location.read_bytes()).hexdigest()
    elif input_location.is_dir():
        for path in sorted(input_location.glob("*.json")):
            manifest["input_file_fingerprints"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()

    tmp_manifest = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(output_location), delete=False) as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            tmp_manifest = Path(handle.name)
        os.replace(tmp_manifest, output_location / "manifest.json")
    finally:
        if tmp_manifest is not None and tmp_manifest.exists():
            tmp_manifest.unlink(missing_ok=True)

    return {"children": children, "parents": parents, "manifest": manifest}


def hierarchy_status(store_dir: str | Path | None = None) -> dict[str, Any]:
    """Return a read-only status payload for the hierarchy store."""
    store_location = Path(store_dir or DEFAULT_STORE_DIR).resolve()
    children_path = store_location / "children.json"
    parents_path = store_location / "parents.json"
    manifest_path = store_location / "manifest.json"
    children = []
    parents = []
    manifest = {}
    if children_path.exists():
        children = json.loads(children_path.read_text(encoding="utf-8"))
    if parents_path.exists():
        parents = json.loads(parents_path.read_text(encoding="utf-8"))
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    return {
        "status": "ready" if children_path.exists() and parents_path.exists() and manifest_path.exists() else "not_ready",
        "store_dir": str(store_location),
        "children_exists": children_path.exists(),
        "parents_exists": parents_path.exists(),
        "manifest_exists": manifest_path.exists(),
        "child_count": len(children),
        "parent_count": len(parents),
        "ambiguous_child_count": sum(1 for child in children if child.get("ambiguous")),
        "manifest": manifest,
    }


def hierarchy_audit(input_path: str | Path | None = None) -> dict[str, Any]:
    """Return a summary of the hierarchy input without writing a store."""
    input_location = resolve_input_path(input_path)
    payload = load_chunks(input_location, strategy="hierarchical")
    records = payload.get("chunks", [])
    return {
        "input_path": str(input_location),
        "record_count": len(records),
        "source_count": len({str(record.get("source", "")).strip() for record in records}),
    }


def _load_hierarchy_store_payload(store_dir: str | Path | None = None, config: dict[str, Any] | None = None, input_path: str | Path | None = None) -> dict[str, Any]:
    runtime_config = load_runtime_config() if config is None else {**load_runtime_config(), **config}
    validate_runtime_config(runtime_config)

    store_location = Path(store_dir or DEFAULT_STORE_DIR).resolve()
    children_path = store_location / "children.json"
    parents_path = store_location / "parents.json"
    manifest_path = store_location / "manifest.json"

    if not children_path.exists() or not parents_path.exists() or not manifest_path.exists():
        return {
            "status": "hierarchy_not_ready",
            "error": "hierarchy store files are missing",
            "store_dir": str(store_location),
        }

    try:
        children = json.loads(children_path.read_text(encoding="utf-8"))
        parents = json.loads(parents_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - malformed store
        return {
            "status": "hierarchy_not_ready",
            "error": f"unable to read hierarchy store: {exc}",
            "store_dir": str(store_location),
        }

    config_identity = manifest.get("config_identity")
    relevant_keys = {
        "PARENT_MAX_CHARS",
        "PARENT_SCORE_CHILD_LIMIT",
        "PARENT_RRF_K",
        "PARENT_CANDIDATES",
        "FINAL_PARENT_TOP_K",
    }
    if not isinstance(config_identity, dict):
        return {
            "status": "hierarchy_not_ready",
            "error": "hierarchy manifest config does not match the current runtime config",
            "store_dir": str(store_location),
        }

    if not all(str(config_identity.get(key)) == str(runtime_config.get(key)) for key in sorted(relevant_keys)):
        return {
            "status": "hierarchy_not_ready",
            "error": "hierarchy manifest config does not match the current runtime config",
            "store_dir": str(store_location),
        }

    input_location = resolve_input_path(input_path)
    if input_path is None:
        expected_fingerprint = None
    elif input_location.is_file():
        expected_fingerprint = {input_location.name: hashlib.sha256(input_location.read_bytes()).hexdigest()}
    elif input_location.is_dir():
        expected_fingerprint = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(input_location.glob("*.json"))}
    else:
        expected_fingerprint = None

    manifest_fingerprints = manifest.get("input_file_fingerprints", {})
    if expected_fingerprint is not None and manifest_fingerprints != expected_fingerprint:
        return {
            "status": "hierarchy_not_ready",
            "error": "hierarchy manifest fingerprints do not match the current input",
            "store_dir": str(store_location),
        }

    return {
        "status": "ready",
        "store_dir": str(store_location),
        "children": children,
        "parents": parents,
        "manifest": manifest,
        "config": runtime_config,
    }


def parent_retrieval(
    fused_child_results: dict[str, Any] | list[dict[str, Any]],
    input_path: str | Path | None = None,
    store_dir: str | Path | None = None,
    config: dict[str, Any] | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Map fused child hits to parent documents and aggregate parent candidates."""
    start_time = time.perf_counter()
    runtime_config = load_runtime_config() if config is None else {**load_runtime_config(), **config}
    validate_runtime_config(runtime_config)

    store_payload = _load_hierarchy_store_payload(store_dir=store_dir, config=runtime_config, input_path=input_path)
    if store_payload.get("status") != "ready":
        return {
            "status": "hierarchy_not_ready",
            "error": store_payload.get("error", "hierarchy store is not ready"),
            "parent_candidates": [],
            "trace": {},
        }

    children = store_payload.get("children", [])
    parents = store_payload.get("parents", [])
    if not isinstance(children, list) or not isinstance(parents, list):
        return {
            "status": "hierarchy_not_ready",
            "error": "hierarchy store payloads are invalid",
            "parent_candidates": [],
            "trace": {},
        }

    if isinstance(fused_child_results, dict):
        if "merged_children" in fused_child_results and isinstance(fused_child_results.get("merged_children"), list):
            child_hits = fused_child_results["merged_children"]
        elif "children" in fused_child_results and isinstance(fused_child_results.get("children"), list):
            child_hits = fused_child_results["children"]
        else:
            child_hits = []
    else:
        child_hits = fused_child_results

    if not isinstance(child_hits, list):
        return {
            "status": "hierarchy_not_ready",
            "error": "fused child results must be a list or contain merged_children",
            "parent_candidates": [],
            "trace": {},
        }

    child_lookup: dict[str, dict[str, Any]] = {}
    for child in children:
        child_id = str(child.get("child_id", "")).strip()
        if not child_id:
            continue
        if child_id in child_lookup:
            return {
                "status": "hierarchy_not_ready",
                "error": f"duplicate child_id in hierarchy store: {child_id}",
                "parent_candidates": [],
                "trace": {},
            }
        child_lookup[child_id] = child

    parent_lookup: dict[str, dict[str, Any]] = {}
    for parent in parents:
        parent_id = str(parent.get("parent_id", "")).strip()
        if not parent_id:
            continue
        parent_lookup[parent_id] = parent

    groups: dict[str, list[dict[str, Any]]] = {}
    child_to_parent_mapping: list[dict[str, Any]] = []
    seen_child_ids: set[str] = set()
    seen_texts: dict[str, str] = {}

    for raw_hit in child_hits:
        if not isinstance(raw_hit, dict):
            continue
        child_id = str(raw_hit.get("child_id", "")).strip()
        if not child_id:
            continue
        if child_id in seen_child_ids:
            continue
        seen_child_ids.add(child_id)

        child_record = child_lookup.get(child_id)
        if child_record is None:
            return {
                "status": "hierarchy_not_ready",
                "error": f"child lookup failed for child_id {child_id}",
                "parent_candidates": [],
                "trace": {},
            }

        parent_id = str(child_record.get("parent_id", "")).strip()
        if not parent_id:
            return {
                "status": "hierarchy_not_ready",
                "error": f"parent lookup failed for child_id {child_id}",
                "parent_candidates": [],
                "trace": {},
            }

        parent_record = parent_lookup.get(parent_id)
        if parent_record is None:
            return {
                "status": "hierarchy_not_ready",
                "error": f"parent lookup failed for parent_id {parent_id}",
                "parent_candidates": [],
                "trace": {},
            }

        text_key = (str(raw_hit.get("text", "")).strip() or str(child_record.get("text", "")).strip()).casefold()
        if text_key and text_key in seen_texts and seen_texts[text_key] != parent_id:
            return {
                "status": "hierarchy_not_ready",
                "error": "duplicate child text detected across parents",
                "parent_candidates": [],
                "trace": {},
            }
        if text_key:
            seen_texts[text_key] = parent_id

        groups.setdefault(parent_id, []).append({**raw_hit, "child_record": child_record, "parent_record": parent_record})
        child_to_parent_mapping.append({
            "child_id": child_id,
            "parent_id": parent_id,
            "query_ids": list(raw_hit.get("support_query_ids", [])) if isinstance(raw_hit.get("support_query_ids", []), list) else [],
            "multi_query_rank": int(raw_hit.get("multi_query_rank", 0) or 0),
        })

    if not groups:
        return {
            "status": "ready",
            "mode": mode or "single_parent",
            "parent_candidates": [],
            "trace": {
                "input_child_hit_count": len(child_hits),
                "unique_parent_count": 0,
                "mapping_table": [],
                "child_chars": 0,
                "expanded_parent_chars": 0,
                "context_expansion_factor": 0.0,
                "dropped_by_candidate_limit": [],
                "dropped_by_context_budget": [],
                "mapping_latency_ms": round((time.perf_counter() - start_time) * 1000.0, 3),
            },
        }

    scoring_limit = int(runtime_config.get("PARENT_SCORE_CHILD_LIMIT", 3))
    candidate_limit = int(runtime_config.get("PARENT_CANDIDATES", 10))
    rrf_k = int(runtime_config.get("PARENT_RRF_K", 60))
    total_context_limit = int(runtime_config.get("TOTAL_CONTEXT_MAX_CHARS", 16000))

    parent_candidates: list[dict[str, Any]] = []
    dropped_by_candidate_limit: list[dict[str, Any]] = []
    dropped_by_context_budget: list[dict[str, Any]] = []
    parent_score_components: dict[str, list[dict[str, Any]]] = {}

    for parent_id, hits in groups.items():
        parent_record = parent_lookup[parent_id]
        support_query_ids: list[str] = []
        for hit in hits:
            for query_id in hit.get("support_query_ids", []) or []:
                if query_id not in support_query_ids:
                    support_query_ids.append(query_id)

        ordered_hits = sorted(hits, key=lambda item: (int(item.get("multi_query_rank", 0) or 0), str(item.get("child_id", ""))))
        scoring_hits = ordered_hits[:scoring_limit]
        parent_rrf_score = sum(1.0 / float(rrf_k + int(hit.get("multi_query_rank", 0) or 0)) for hit in scoring_hits)

        parent_score_components[parent_id] = [
            {
                "child_id": hit.get("child_id"),
                "rank": int(hit.get("multi_query_rank", 0) or 0),
                "component": round(1.0 / float(rrf_k + int(hit.get("multi_query_rank", 0) or 0)), 6),
            }
            for hit in scoring_hits
        ]

        candidate = {
            "parent_id": parent_id,
            "source": parent_record.get("source", ""),
            "page_start": parent_record.get("page_start"),
            "page_end": parent_record.get("page_end"),
            "structural_path": parent_record.get("structural_path") or {"chapter": None, "article": None, "clause": None, "point": None},
            "text": parent_record.get("text", ""),
            "parent_rrf_score": round(parent_rrf_score, 6),
            "parent_rank": 0,
            "anchor_child_id": ordered_hits[0].get("child_id") if ordered_hits else "",
            "scoring_child_ids": [hit.get("child_id") for hit in scoring_hits],
            "supporting_child_ids": [hit.get("child_id") for hit in hits],
            "support_query_ids": support_query_ids,
            "best_child_rank": int(ordered_hits[0].get("multi_query_rank", 0) or 0) if ordered_hits else 0,
            "ambiguous": bool(parent_record.get("ambiguous_child_count", 0) > 0 or any(hit.get("ambiguous") for hit in hits)),
            "warnings": list(parent_record.get("warnings", [])) + [warning for warning in [hit.get("warning") for hit in hits if hit.get("warning")] if warning],
        }
        parent_candidates.append(candidate)

    parent_candidates.sort(key=lambda item: (-item["parent_rrf_score"], len(item["support_query_ids"]), item["best_child_rank"], item["parent_id"]))
    if len(parent_candidates) > candidate_limit:
        dropped_by_candidate_limit = parent_candidates[candidate_limit:]
        parent_candidates = parent_candidates[:candidate_limit]

    selected_candidates: list[dict[str, Any]] = []
    selected_chars = 0
    for candidate in parent_candidates:
        parent_text = str(candidate.get("text", "") or "")
        parent_chars = len(parent_text)
        if not selected_candidates and parent_chars > total_context_limit:
            candidate.setdefault("warnings", []).append("oversized_parent_kept")
            selected_candidates.append(candidate)
            selected_chars += parent_chars
            continue
        if selected_chars + parent_chars <= total_context_limit:
            selected_candidates.append(candidate)
            selected_chars += parent_chars
        else:
            dropped_by_context_budget.append(candidate)

    for index, candidate in enumerate(selected_candidates, start=1):
        candidate["parent_rank"] = index

    child_chars = sum(len(str(hit.get("text", "") or "")) for hit in child_hits if isinstance(hit, dict))
    expanded_parent_chars = sum(len(str(candidate.get("text", "") or "")) for candidate in selected_candidates)
    context_expansion_factor = round(expanded_parent_chars / child_chars, 3) if child_chars else 0.0

    trace = {
        "input_child_hit_count": len(child_hits),
        "unique_parent_count": len(groups),
        "child_count_per_parent": {parent_id: len(hits) for parent_id, hits in groups.items()},
        "mapping_table": child_to_parent_mapping,
        "parent_score_components": parent_score_components,
        "parents_dropped_by_candidate_limit": dropped_by_candidate_limit,
        "parents_dropped_by_context_budget": dropped_by_context_budget,
        "child_chars": child_chars,
        "expanded_parent_chars": expanded_parent_chars,
        "context_expansion_factor": context_expansion_factor,
        "ambiguous_warning_count": sum(1 for candidate in selected_candidates if candidate.get("ambiguous") or candidate.get("warnings")),
        "mapping_latency_ms": round((time.perf_counter() - start_time) * 1000.0, 3),
    }

    return {
        "status": "ready",
        "mode": mode or ("single_parent" if len(child_hits) <= 1 else "multi_parent"),
        "parent_candidates": selected_candidates,
        "trace": trace,
    }


def _sigmoid(value: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-value))
    except OverflowError:
        return 0.0 if value < 0 else 1.0


def rerank_parent_candidates(
    candidates: list[dict[str, Any]],
    original_question: str,
    config: dict[str, Any] | None = None,
    reranker_fn: Any = None,
) -> dict[str, Any]:
    runtime_config = load_runtime_config() if config is None else {**load_runtime_config(), **config}
    validate_runtime_config(runtime_config)
    model_name = os.getenv("RERANKER_MODEL", "").strip()
    if not model_name:
        return {
            "status": "reranker_unavailable",
            "error": "RERANKER_MODEL is not configured",
            "reranked_candidates": [],
            "trace": {"reranker_call_count": 0},
        }

    try:
        if reranker_fn is None:
            try:
                from google import genai  # type: ignore
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("google.genai is not installed; provide reranker_fn in tests or install the dependency") from exc

            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not configured")
            client = genai.Client(api_key=api_key)
            reranker_fn = lambda question, text, cfg, model: client.models.score(
                model=model,
                text=text,
                prompt=question,
            )

        trimmed_candidates = candidates[: int(runtime_config.get("PARENT_CANDIDATES", 10))]
        reranked: list[dict[str, Any]] = []
        for candidate in trimmed_candidates:
            raw = reranker_fn(original_question, str(candidate.get("text", "")), runtime_config, model_name)
            if not isinstance(raw, dict) or "raw_score" not in raw:
                raise RuntimeError("reranker_fn must return a dictionary containing raw_score")
            raw_score = float(raw["raw_score"])
            score = _sigmoid(raw_score)
            candidate_copy = dict(candidate)
            candidate_copy["parent_rerank_raw_score"] = raw_score
            candidate_copy["parent_rerank_score"] = round(score, 6)
            candidate_copy["parent_rerank_rank"] = 0
            candidate_copy["parent_rank_change"] = 0
            reranked.append(candidate_copy)

        reranked.sort(key=lambda item: (-item["parent_rerank_score"], item.get("parent_rank", 0), item.get("parent_id", "")))
        for index, candidate in enumerate(reranked, start=1):
            candidate["parent_rerank_rank"] = index
            candidate["parent_rank_change"] = int(candidate.get("parent_rank", 0)) - index

        return {
            "status": "ready",
            "reranked_candidates": reranked,
            "trace": {"reranker_call_count": len(reranked)},
        }
    except Exception as exc:  # pragma: no cover
        return {
            "status": "reranker_unavailable",
            "error": str(exc),
            "reranked_candidates": [],
            "trace": {"reranker_call_count": 0},
        }


def _build_answer_prompt(question: str, accepted_parents: list[dict[str, Any]]) -> str:
    pieces = [f"Câu hỏi: {question}", "Dựa trên bằng chứng sau:"]
    for index, parent in enumerate(accepted_parents, start=1):
        pieces.append(
            f"[P{index}] Parent ID: {parent.get('parent_id')} | Source: {parent.get('source')} | Pages: {parent.get('page_start')}-{parent.get('page_end')} | Text: {parent.get('text')}"
        )
    pieces.append("Chỉ trả lời từ bằng chứng trên và không thêm thông tin ngoài phạm vi.")
    return "\n\n".join(pieces)


def _generate_answer(
    question: str,
    accepted_parents: list[dict[str, Any]],
    config: dict[str, Any],
    answer_generator_fn: Any = None,
) -> dict[str, Any]:
    if not accepted_parents:
        return {
            "status": "insufficient_evidence",
            "answer": "",
            "citations": [],
            "trace": {"answer_generation_call_count": 0},
        }
    if answer_generator_fn is None:
        try:
            from google import genai  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("google.genai is not installed; provide answer_generator_fn in tests or install the dependency") from exc
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        model_name = os.getenv("GEMINI_GENERATION_MODEL", "").strip()
        prompt = _build_answer_prompt(question, accepted_parents)
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={"temperature": float(config.get("MULTI_QUERY_TEMPERATURE", 0.2)), "response_mime_type": "application/json"},
        )
        payload = json.loads(response.text)
        if not isinstance(payload, dict):
            raise RuntimeError("Answer generator returned invalid payload")
        return {
            "status": "ready",
            "answer": str(payload.get("answer", "")),
            "citations": payload.get("citations", []),
            "trace": {"answer_generation_call_count": 1},
        }

    output = answer_generator_fn(question, accepted_parents, config, os.getenv("GEMINI_GENERATION_MODEL", ""))
    if not isinstance(output, dict) or "answer" not in output or "citations" not in output:
        raise RuntimeError("answer_generator_fn must return a dictionary containing answer and citations")
    return {"status": "ready", "answer": str(output["answer"]), "citations": output["citations"], "trace": {"answer_generation_call_count": 1}}


def run_query_pipeline(
    question: str,
    mode: str,
    config: dict[str, Any] | None = None,
    input_path: str | Path | None = None,
    store_dir: str | Path | None = None,
    query_generator_fn: Any = None,
    hybrid_retriever_fn: Any = None,
    reranker_fn: Any = None,
    answer_generator_fn: Any = None,
) -> dict[str, Any]:
    runtime_config = load_runtime_config() if config is None else {**load_runtime_config(), **config}
    validate_runtime_config(runtime_config)
    if mode not in {"single_flat", "multi_flat", "single_parent", "multi_parent"}:
        return {"status": "invalid_mode", "error": f"unsupported mode: {mode}", "mode": mode}

    raw_question = _normalize_query_text(question)
    query_set: dict[str, Any]
    generation_api_call_count = 0
    if mode.startswith("single_"):
        query_set = {
            "original_question": raw_question,
            "queries": [{"query_id": "Q0", "text": raw_question, "origin": "original", "focus": "original_intent"}],
            "model": os.getenv("GEMINI_GENERATION_MODEL", ""),
            "generation_latency_ms": 0.0,
            "status": "ready",
        }
    else:
        query_set = generate_query_set(raw_question, config=runtime_config, query_generator_fn=query_generator_fn)
        if query_set.get("status") != "ready":
            return {
                "status": query_set.get("status", "query_generation_unavailable"),
                "mode": mode,
                "original_question": raw_question,
                "query_set": query_set,
                "child_hits": [],
                "parent_candidates": [],
                "accepted_evidence": [],
                "answer": "",
                "citations": [],
                "trace": {
                    "generation_api_call_count": 0,
                    "answer_generation_call_count": 0,
                    "reranker_call_count": 0,
                },
            }
        generation_api_call_count = 0 if query_set.get("cache_hit") else 1

    retrieval = multi_child_retrieval(query_set, config=runtime_config, hybrid_retriever_fn=hybrid_retriever_fn)
    if retrieval.get("status") == "retrieval_unavailable":
        return {
            "status": retrieval.get("status", "retrieval_unavailable"),
            "mode": mode,
            "original_question": raw_question,
            "query_set": query_set,
            "child_hits": [],
            "parent_candidates": [],
            "accepted_evidence": [],
            "answer": "",
            "citations": [],
            "trace": {
                "generation_api_call_count": generation_api_call_count,
                "answer_generation_call_count": 0,
                "reranker_call_count": 0,
            },
            "errors": retrieval.get("errors", []),
        }

    answer = ""
    citations: list[dict[str, Any]] = []
    accepted_evidence: list[dict[str, Any]] = []
    reranker_call_count = 0
    parent_candidates: list[dict[str, Any]] = []
    answer_generation_count = 0
    status = retrieval.get("status", "ready")

    if mode.endswith("_flat"):
        child_hits = retrieval.get("merged_children", [])
        parent_candidates = []
        if answer_generator_fn is not None and mode == "single_flat":
            answer = ""
            citations = []
    else:
        child_hits = retrieval.get("merged_children", [])
        parent_retrieval_result = parent_retrieval(child_hits, input_path=input_path, store_dir=store_dir, config=runtime_config, mode=mode)
        if parent_retrieval_result.get("status") != "ready":
            return {
                "status": parent_retrieval_result.get("status", "hierarchy_not_ready"),
                "mode": mode,
                "original_question": raw_question,
                "query_set": query_set,
                "child_hits": child_hits,
                "parent_candidates": [],
                "accepted_evidence": [],
                "answer": "",
                "citations": [],
                "trace": {
                    "generation_api_call_count": generation_api_call_count,
                    "answer_generation_call_count": 0,
                    "reranker_call_count": 0,
                },
                "errors": parent_retrieval_result.get("errors", []),
            }
        rerank_result = rerank_parent_candidates(parent_retrieval_result.get("parent_candidates", []), raw_question, config=runtime_config, reranker_fn=reranker_fn)
        if rerank_result.get("status") != "ready":
            return {
                "status": rerank_result.get("status", "reranker_unavailable"),
                "mode": mode,
                "original_question": raw_question,
                "query_set": query_set,
                "child_hits": child_hits,
                "parent_candidates": [],
                "accepted_evidence": [],
                "answer": "",
                "citations": [],
                "trace": {
                    "generation_api_call_count": generation_api_call_count,
                    "answer_generation_call_count": 0,
                    "reranker_call_count": rerank_result.get("trace", {}).get("reranker_call_count", 0),
                },
                "errors": rerank_result.get("error", ""),
            }
        reranker_call_count = rerank_result.get("trace", {}).get("reranker_call_count", 0)
        parent_candidates = rerank_result.get("rer-ranked_candidates", []) if False else rerank_result.get("reranked_candidates", [])
        accepted_evidence = [candidate for candidate in parent_candidates if float(candidate.get("parent_rerank_score", 0.0)) >= float(runtime_config.get("RERANK_MIN_SCORE", 0.5))]
        accepted_evidence = accepted_evidence[: int(runtime_config.get("FINAL_PARENT_TOP_K", 3))]
        answer_generation_count = 0
        if not accepted_evidence:
            status = "insufficient_evidence"
        elif answer_generator_fn is not None:
            answer_result = _generate_answer(raw_question, accepted_evidence, runtime_config, answer_generator_fn=answer_generator_fn)
            answer = answer_result.get("answer", "")
            citations = answer_result.get("citations", [])
            status = answer_result.get("status", status)
            answer_generation_count = answer_result.get("trace", {}).get("answer_generation_call_count", 0)

    trace = {
        "generation_api_call_count": generation_api_call_count + answer_generation_count,
        "answer_generation_call_count": answer_generation_count,
        "reranker_call_count": reranker_call_count,
        "child_count": len(child_hits),
        "parent_count": len(parent_candidates),
    }

    return {
        "status": status,
        "mode": mode,
        "original_question": raw_question,
        "query_set": query_set,
        "child_hits": child_hits,
        "parent_candidates": parent_candidates,
        "accepted_evidence": accepted_evidence,
        "answer": answer,
        "citations": citations,
        "trace": trace,
    }


def compare_modes(
    question: str,
    config: dict[str, Any] | None = None,
    input_path: str | Path | None = None,
    store_dir: str | Path | None = None,
    query_generator_fn: Any = None,
    hybrid_retriever_fn: Any = None,
    reranker_fn: Any = None,
) -> dict[str, Any]:
    runtime_config = load_runtime_config() if config is None else {**load_runtime_config(), **config}
    validate_runtime_config(runtime_config)
    modes = ["single_flat", "multi_flat", "single_parent", "multi_parent"]
    mode_results: dict[str, Any] = {}
    trace = {"generation_api_call_count": 0, "answer_generation_call_count": 0, "reranker_call_count": 0}
    for mode in modes:
        result = run_query_pipeline(
            question,
            mode,
            config=runtime_config,
            input_path=input_path,
            store_dir=store_dir,
            query_generator_fn=query_generator_fn,
            hybrid_retriever_fn=hybrid_retriever_fn,
            reranker_fn=reranker_fn,
            answer_generator_fn=None,
        )
        result = {k: v for k, v in result.items() if k not in {"answer", "citations"}}
        mode_results[mode] = result
        trace["generation_api_call_count"] += result.get("trace", {}).get("generation_api_call_count", 0)
        trace["answer_generation_call_count"] += result.get("trace", {}).get("answer_generation_call_count", 0)
        trace["reranker_call_count"] += result.get("trace", {}).get("reranker_call_count", 0)

    return {"status": "ready", "mode_results": mode_results, "trace": trace}


def main() -> None:
    parser = argparse.ArgumentParser(description="Buổi 09 hierarchy builder and query expansion")
    parser.add_argument("command", nargs="?", default="hierarchy-status", choices=["hierarchy-audit", "build-hierarchy", "hierarchy-status", "expand-query", "multi-child", "parent-retrieve", "query", "compare"])
    parser.add_argument("--input", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--question", default=None)
    parser.add_argument("--mode", default="multi_parent", choices=["single_flat", "multi_flat", "single_parent", "multi_parent"])
    args = parser.parse_args()

    if args.command == "hierarchy-audit":
        print(json.dumps(hierarchy_audit(args.input), ensure_ascii=False, indent=2))
    elif args.command == "build-hierarchy":
        print(json.dumps(build_store(input_path=args.input, output_dir=args.output_dir), ensure_ascii=False, indent=2))
    elif args.command == "expand-query":
        if not args.question:
            raise SystemExit("--question is required for expand-query")
        print(json.dumps(generate_query_set(args.question), ensure_ascii=False, indent=2))
    elif args.command == "multi-child":
        if not args.question:
            raise SystemExit("--question is required for multi-child")
        query_set = generate_query_set(args.question)
        if query_set.get("status") != "ready":
            print(json.dumps(query_set, ensure_ascii=False, indent=2))
            return

        def _default_retriever(query_text: str, config: dict[str, Any], query_id: str, strategy: str = "hierarchical") -> list[dict[str, Any]]:
            return []

        print(json.dumps(multi_child_retrieval(query_set, config=load_runtime_config(), hybrid_retriever_fn=_default_retriever), ensure_ascii=False, indent=2))
    elif args.command == "parent-retrieve":
        if not args.question:
            raise SystemExit("--question is required for parent-retrieve")
        query_set = generate_query_set(args.question)
        if query_set.get("status") != "ready":
            print(json.dumps(query_set, ensure_ascii=False, indent=2))
            return

        def _default_retriever(query_text: str, config: dict[str, Any], query_id: str, strategy: str = "hierarchical") -> list[dict[str, Any]]:
            return []

        fused = multi_child_retrieval(query_set, config=load_runtime_config(), hybrid_retriever_fn=_default_retriever)
        if fused.get("status") != "ready" and fused.get("status") != "partial":
            print(json.dumps(fused, ensure_ascii=False, indent=2))
            return
        print(json.dumps(parent_retrieval(fused, config=load_runtime_config()), ensure_ascii=False, indent=2))
    elif args.command == "query":
        if not args.question:
            raise SystemExit("--question is required for query")
        def _default_retriever(query_text: str, config: dict[str, Any], query_id: str, strategy: str = "hierarchical") -> list[dict[str, Any]]:
            return []
        result = run_query_pipeline(args.question, args.mode, config=load_runtime_config(), input_path=args.input, store_dir=args.output_dir, query_generator_fn=None, hybrid_retriever_fn=_default_retriever, reranker_fn=None, answer_generator_fn=None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "compare":
        if not args.question:
            raise SystemExit("--question is required for compare")
        def _default_retriever(query_text: str, config: dict[str, Any], query_id: str, strategy: str = "hierarchical") -> list[dict[str, Any]]:
            return []
        print(json.dumps(compare_modes(args.question, config=load_runtime_config(), input_path=args.input, store_dir=args.output_dir, query_generator_fn=None, hybrid_retriever_fn=_default_retriever, reranker_fn=None), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(hierarchy_status(args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
