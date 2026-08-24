"""Snapshot baseline from Buổi 08: rag.py.

This module is copied from the Buổi 08 runtime for skeleton purposes only.
It intentionally avoids importing Buổi 08 runtime modules directly and keeps
logic unchanged in this step.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
RAG_ROOT = BASE_DIR.parent.parent
DEFAULT_INPUT_DIR = RAG_ROOT / "rag_foundation" / "buoi_05" / "output" / "chunks"
STORAGE_DIR = BASE_DIR / "storage" / "chroma"
VALID_STRATEGIES = {"fixed-size", "semantic", "hierarchical"}

if (BASE_DIR / ".env").exists():
    load_dotenv(BASE_DIR / ".env", override=False)


def resolve_input_path(input_path: str | None = None) -> Path:
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


def _list_json_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".json":
            raise ValueError(f"Input file is not a JSON file: {input_path}")
        return [input_path]
    if input_path.is_dir():
        files = sorted([path for path in input_path.glob("*.json") if path.is_file()])
        if not files:
            raise ValueError(f"No JSON files found in input directory: {input_path}")
        return files
    raise FileNotFoundError(f"Input path does not exist: {input_path}")


def _load_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_chunks(input_path: str | Path | None = None, strategy: str = "hierarchical") -> dict[str, Any]:
    """Load and validate chunk records from one file or a directory of JSON files."""
    input_location = resolve_input_path(None if input_path is None else str(input_path))
    if not input_location.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_location}")

    strategy_name = strategy.strip().lower() if isinstance(strategy, str) else ""
    if not strategy_name:
        strategy_name = "hierarchical"
    if strategy_name not in VALID_STRATEGIES:
        raise ValueError(f"Unsupported strategy '{strategy}'. Allowed values: {', '.join(sorted(VALID_STRATEGIES))}")

    files = _list_json_files(input_location)
    chunks: list[dict[str, Any]] = []
    seen_chunk_ids: dict[str, tuple[str, int]] = {}

    for path in files:
        payload = _load_json_file(path)
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict) and isinstance(payload.get("chunks"), list):
            records = payload["chunks"]
        else:
            raise ValueError(f"Unsupported JSON structure in {path.name}: expected a list or an object with a 'chunks' list")

        for record_index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                raise ValueError(f"Record at {path.name}[{record_index}] is not a JSON object")
            if record.get("strategy") != strategy_name:
                continue
            missing_fields = [field for field in ("chunk_id", "strategy", "source", "page_start", "page_end", "text") if field not in record]
            if missing_fields:
                raise ValueError(f"Missing required field(s) {', '.join(missing_fields)} in {path.name}[{record_index}]")
            chunk_id = record.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                raise ValueError(f"chunk_id must be a non-empty string in {path.name}[{record_index}]")
            if chunk_id.strip() in seen_chunk_ids:
                raise ValueError(f"Duplicate chunk_id '{chunk_id.strip()}' found in {path.name}[{record_index}]")
            seen_chunk_ids[chunk_id.strip()] = (path.name, record_index)
            normalized_chunk = dict(record)
            normalized_chunk["chunk_id"] = chunk_id.strip()
            normalized_chunk["text"] = str(record.get("text", "")).strip()
            chunks.append(normalized_chunk)

    return {"chunks": chunks, "files_read": len(files), "total_records": len(chunks)}


def load_runtime_config() -> dict[str, Any]:
    """Load and validate runtime configuration from the local .env file."""
    embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "").strip()
    generation_model = os.getenv("GEMINI_GENERATION_MODEL", "").strip()
    if not embedding_model:
        raise ValueError("GEMINI_EMBEDDING_MODEL must be set")
    if not generation_model:
        raise ValueError("GEMINI_GENERATION_MODEL must be set")
    return {
        "api_key": os.getenv("GEMINI_API_KEY", "").strip(),
        "embedding_model": embedding_model,
        "generation_model": generation_model,
        "embedding_dim": int(os.getenv("GEMINI_EMBEDDING_DIM", "768")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Buổi 09 skeleton baseline")
    parser.add_argument("--strategy", default="hierarchical")
    parser.add_argument("--input", default=None)
    args = parser.parse_args()
    payload = load_chunks(input_path=args.input, strategy=args.strategy)
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    main()
