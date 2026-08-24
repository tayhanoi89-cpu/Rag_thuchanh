"""Khung Advanced RAG cho Buổi 08.

Module này cung cấp loader cấu hình và validation cho các bước tiếp theo:
BM25, RRF, reranker và UI. Nó không tải model reranker khi import.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"
STORAGE_DIR = BASE_DIR / "storage" / "chroma"
CHROMA_ROOT = BASE_DIR / "storage" / "chroma"
RERANKER_CACHE_MARKER = BASE_DIR / "storage" / "huggingface" / ".reranker_cache_ready"
_RERANKER_MODEL_LOADED = False

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)

if ENV_EXAMPLE_PATH.exists():
    load_dotenv(ENV_EXAMPLE_PATH, override=False)


def load_runtime_config() -> dict[str, Any]:
    """Load and validate runtime configuration from the local .env file."""
    raw_values = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "").strip(),
        "GEMINI_EMBEDDING_MODEL": os.getenv("GEMINI_EMBEDDING_MODEL", "").strip(),
        "GEMINI_EMBEDDING_DIM": os.getenv("GEMINI_EMBEDDING_DIM", "768").strip(),
        "GEMINI_GENERATION_MODEL": os.getenv("GEMINI_GENERATION_MODEL", "").strip(),
        "RAG_MAX_DISTANCE": os.getenv("RAG_MAX_DISTANCE", "0.45").strip(),
        "BM25_CANDIDATES": os.getenv("BM25_CANDIDATES", "20").strip(),
        "SEMANTIC_CANDIDATES": os.getenv("SEMANTIC_CANDIDATES", "20").strip(),
        "RRF_K": os.getenv("RRF_K", "60").strip(),
        "RRF_BM25_WEIGHT": os.getenv("RRF_BM25_WEIGHT", "1.0").strip(),
        "RRF_SEMANTIC_WEIGHT": os.getenv("RRF_SEMANTIC_WEIGHT", "1.0").strip(),
        "RERANK_CANDIDATES": os.getenv("RERANK_CANDIDATES", "20").strip(),
        "FINAL_TOP_K": os.getenv("FINAL_TOP_K", "5").strip(),
        "RERANKER_MODEL": os.getenv("RERANKER_MODEL", "").strip(),
        "RERANKER_MAX_LENGTH": os.getenv("RERANKER_MAX_LENGTH", "512").strip(),
        "RERANK_BATCH_SIZE": os.getenv("RERANK_BATCH_SIZE", "4").strip(),
        "RERANK_MIN_SCORE": os.getenv("RERANK_MIN_SCORE", "0.50").strip(),
        "RERANK_DEVICE": os.getenv("RERANK_DEVICE", "auto").strip(),
    }

    def _require_non_empty(name: str, value: str) -> str:
        if not value:
            raise ValueError(f"{name} must be set")
        return value

    def _require_int(name: str, value: str, min_value: int, max_value: int) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer") from exc
        if not (min_value <= parsed <= max_value):
            raise ValueError(f"{name} must be between {min_value} and {max_value}")
        return parsed

    def _require_float(name: str, value: str, min_value: float, max_value: float) -> float:
        try:
            parsed = float(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a float") from exc
        if not (min_value <= parsed <= max_value):
            raise ValueError(f"{name} must be between {min_value} and {max_value}")
        return parsed

    embedding_model = _require_non_empty("GEMINI_EMBEDDING_MODEL", raw_values["GEMINI_EMBEDDING_MODEL"])
    generation_model = _require_non_empty("GEMINI_GENERATION_MODEL", raw_values["GEMINI_GENERATION_MODEL"])
    reranker_model = _require_non_empty("RERANKER_MODEL", raw_values["RERANKER_MODEL"])

    bm25_candidates = _require_int("BM25_CANDIDATES", raw_values["BM25_CANDIDATES"], 1, 100)
    semantic_candidates = _require_int("SEMANTIC_CANDIDATES", raw_values["SEMANTIC_CANDIDATES"], 1, 100)
    rerank_candidates = _require_int("RERANK_CANDIDATES", raw_values["RERANK_CANDIDATES"], 1, 100)
    final_top_k = _require_int("FINAL_TOP_K", raw_values["FINAL_TOP_K"], 1, 100)
    if final_top_k > rerank_candidates:
        raise ValueError("FINAL_TOP_K must be less than or equal to RERANK_CANDIDATES")

    rrf_k = _require_int("RRF_K", raw_values["RRF_K"], 1, 1000)
    bm25_weight = _require_float("RRF_BM25_WEIGHT", raw_values["RRF_BM25_WEIGHT"], 0.0, 1000.0)
    semantic_weight = _require_float("RRF_SEMANTIC_WEIGHT", raw_values["RRF_SEMANTIC_WEIGHT"], 0.0, 1000.0)
    if bm25_weight == 0.0 and semantic_weight == 0.0:
        raise ValueError("RRF weights cannot both be zero")

    reranker_max_length = _require_int("RERANKER_MAX_LENGTH", raw_values["RERANKER_MAX_LENGTH"], 64, 4096)
    rerank_batch_size = _require_int("RERANK_BATCH_SIZE", raw_values["RERANK_BATCH_SIZE"], 1, 64)
    rerank_min_score = _require_float("RERANK_MIN_SCORE", raw_values["RERANK_MIN_SCORE"], 0.0, 1.0)

    embedding_dim = _require_int("GEMINI_EMBEDDING_DIM", raw_values["GEMINI_EMBEDDING_DIM"], 1, 4096)
    rag_max_distance = _require_float("RAG_MAX_DISTANCE", raw_values["RAG_MAX_DISTANCE"], 0.0, 1.0)

    device = raw_values["RERANK_DEVICE"].lower()
    if device not in {"auto", "cpu", "cuda"}:
        raise ValueError("RERANK_DEVICE must be one of auto, cpu, cuda")

    return {
        "api_key": raw_values["GEMINI_API_KEY"],
        "has_api_key": bool(raw_values["GEMINI_API_KEY"]),
        "embedding_model": embedding_model,
        "generation_model": generation_model,
        "embedding_dim": embedding_dim,
        "rag_max_distance": rag_max_distance,
        "bm25_candidates": bm25_candidates,
        "semantic_candidates": semantic_candidates,
        "rrf_k": rrf_k,
        "rrf_bm25_weight": bm25_weight,
        "rrf_semantic_weight": semantic_weight,
        "rerank_candidates": rerank_candidates,
        "final_top_k": final_top_k,
        "reranker_model": reranker_model,
        "reranker_max_length": reranker_max_length,
        "rerank_batch_size": rerank_batch_size,
        "rerank_min_score": rerank_min_score,
        "rerank_device": device,
    }


def tokenize_vi_legal(text: str) -> list[str]:
    """Tokenize Vietnamese legal text with Unicode-preserving regex extraction."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    normalized = unicodedata.normalize("NFC", text).casefold()
    tokens = re.findall(r"[\wÀ-ÖØ-öø-ÿ]+", normalized, flags=re.UNICODE)
    return [token for token in tokens if token.strip()]


def build_bm25_index(chunks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], BM25Okapi, list[list[str]]]:
    """Build an in-memory BM25 index from validated chunks without persisting state."""
    if not chunks:
        raise ValueError("chunks must not be empty")

    normalized_chunks = []
    tokenized_corpus = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise TypeError("each chunk must be a dictionary")
        text = str(chunk.get("text", ""))
        tokens = tokenize_vi_legal(text)
        normalized_chunks.append(chunk)
        tokenized_corpus.append(tokens)

    bm25 = BM25Okapi(tokenized_corpus)
    return normalized_chunks, bm25, tokenized_corpus


def search_bm25(question: str, chunks: list[dict[str, Any]], candidate_k: int) -> list[dict[str, Any]]:
    """Retrieve BM25 candidates for a question using the same tokenizer as the corpus."""
    if not isinstance(question, str):
        raise TypeError("question must be a string")

    query_tokens = tokenize_vi_legal(question)
    if not query_tokens:
        raise ValueError("question must contain non-empty tokens")

    if not chunks:
        raise ValueError("chunks must not be empty")

    if candidate_k < 1:
        raise ValueError("candidate_k must be positive")

    normalized_chunks, bm25, _ = build_bm25_index(chunks)
    doc_scores = bm25.get_scores(query_tokens)

    ranked = []
    for index, chunk in enumerate(normalized_chunks):
        ranked.append(
            {
                "chunk_id": chunk.get("chunk_id", ""),
                "text": chunk.get("text", ""),
                "source": chunk.get("source", ""),
                "page_start": chunk.get("page_start", 1),
                "page_end": chunk.get("page_end", 2),
                "bm25_rank": 0,
                "bm25_score": float(doc_scores[index]),
            }
        )

    ranked.sort(key=lambda item: (-item["bm25_score"], item["chunk_id"]))
    top_k = min(candidate_k, len(ranked))
    results = ranked[:top_k]
    for rank, item in enumerate(results, start=1):
        item["bm25_rank"] = rank
    return results


def run_bm25_cli(strategy: str, question: str) -> None:
    """Print a simple BM25 diagnostic report for the workshop fixture."""
    fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json"
    if not fixture_path.exists():
        raise FileNotFoundError(f"fixture not found: {fixture_path}")

    chunks = [dict(item) for item in __import__("json").loads(fixture_path.read_text(encoding="utf-8"))]
    if strategy and chunks and chunks[0].get("strategy") != strategy:
        filtered = [chunk for chunk in chunks if chunk.get("strategy") == strategy]
        if filtered:
            chunks = filtered

    results = search_bm25(question, chunks, candidate_k=5)
    print(f"BM25 results for strategy={strategy or 'all'}")
    for item in results:
        preview = item["text"][:80].replace("\n", " ")
        print(
            f"#{item['bm25_rank']} | score={item['bm25_score']:.3f} | {item['source']} | pages={item['page_start']}-{item['page_end']} | {item['chunk_id']} | {preview}"
        )


def _safe_collection_name(strategy: str, config: dict[str, Any]) -> str:
    safe_strategy = re.sub(r"[^a-z0-9]+", "-", strategy.lower()).strip("-") or "strategy"
    safe_model = re.sub(r"[^a-z0-9]+", "-", config["embedding_model"].lower()).strip("-") or "model"
    model_hash = hashlib.sha256(config["embedding_model"].encode("utf-8")).hexdigest()[:12]
    return f"nhnn-{safe_strategy}-{safe_model}-{model_hash}"


def _collection_metadata(strategy: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "strategy": strategy,
        "embedding_model": config["embedding_model"],
        "embedding_dim": config["embedding_dim"],
        "distance_metric": "cosine",
        "schema_version": "1",
    }


def _verify_collection_compatibility(collection: Any, strategy: str, config: dict[str, Any]) -> bool:
    metadata = collection.metadata or {}
    expected = _collection_metadata(strategy, config)
    if metadata.get("strategy") != expected["strategy"]:
        return False
    if metadata.get("embedding_model") != expected["embedding_model"]:
        return False
    if metadata.get("embedding_dim") != expected["embedding_dim"]:
        return False
    if metadata.get("distance_metric") != expected["distance_metric"]:
        return False
    if metadata.get("schema_version") != expected["schema_version"]:
        return False
    return True


def _ensure_chroma_storage(root: str | Path | None = None) -> Path:
    storage_dir = Path(root or CHROMA_ROOT)
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def get_chroma_client(path: str | Path | None = None) -> Any:
    import chromadb

    return chromadb.PersistentClient(path=str(_ensure_chroma_storage(path)))


def _embedding_from_provider(text: str, config: dict[str, Any], embedding_provider: Any) -> list[float]:
    if embedding_provider is None:
        raise ValueError("embedding_provider is required")
    return embedding_provider(text, config)


def prepare_semantic_collection(
    strategy: str,
    chunks: list[dict[str, Any]],
    config: dict[str, Any],
    client: Any | None = None,
    embedding_provider: Any = None,
) -> dict[str, Any]:
    if not config.get("has_api_key"):
        raise ValueError("API key is required to prepare semantic index")

    if client is None:
        client = get_chroma_client()

    collection_name = _safe_collection_name(strategy, config)
    try:
        collection = client.get_collection(name=collection_name, embedding_function=None)
    except Exception:
        collection = None

    if collection is None:
        collection = client.create_collection(
            name=collection_name,
            metadata=_collection_metadata(strategy, config),
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )
    else:
        if not _verify_collection_compatibility(collection, strategy, config):
            raise ValueError("Collection metadata mismatch")

    if not chunks:
        raise ValueError("chunks must not be empty")

    ids = [chunk["chunk_id"] for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    embeddings = []
    for chunk in chunks:
        embedding = _embedding_from_provider(chunk["text"], config, embedding_provider)
        embeddings.append(embedding)

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=[
            {
                "chunk_id": chunk["chunk_id"],
                "source": chunk["source"],
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "strategy": chunk["strategy"],
            }
            for chunk in chunks
        ],
    )
    return {"collection_name": collection_name, "record_count": collection.count(), "strategy": strategy}


def build_status(strategy: str, client: Any | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    effective_config = config or load_runtime_config()
    effective_client = client or get_chroma_client()
    collection_name = _safe_collection_name(strategy, effective_config)
    try:
        collections = effective_client.list_collections()
    except Exception:
        collections = []

    collection_exists = any(getattr(item, "name", None) == collection_name for item in collections)
    collection_count = 0
    collection_compatible = False

    if collection_exists:
        collection = effective_client.get_collection(name=collection_name, embedding_function=None)
        collection_count = collection.count()
        collection_compatible = _verify_collection_compatibility(collection, strategy, effective_config)

    reranker_cache_exists = _RERANKER_MODEL_LOADED and RERANKER_CACHE_MARKER.exists()
    return {
        "strategy": strategy,
        "corpus_size": None,
        "collection_name": collection_name,
        "collection_exists": collection_exists,
        "collection_count": collection_count,
        "collection_compatible": collection_compatible,
        "embedding_model": effective_config["embedding_model"],
        "embedding_dim": effective_config["embedding_dim"],
        "bm25_ready": True,
        "reranker_model": effective_config.get("reranker_model", ""),
        "reranker_cache_exists": reranker_cache_exists,
    }


def semantic_search(
    question: str,
    candidate_k: int,
    strategy: str,
    client: Any | None = None,
    config: dict[str, Any] | None = None,
    embedding_provider: Any = None,
) -> list[dict[str, Any]]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    effective_config = config or load_runtime_config()
    effective_client = client or get_chroma_client()
    collection_name = _safe_collection_name(strategy, effective_config)

    try:
        collection = effective_client.get_collection(name=collection_name, embedding_function=None)
    except Exception as exc:
        raise ValueError("semantic collection does not exist") from exc

    if not _verify_collection_compatibility(collection, strategy, effective_config):
        raise ValueError("Collection metadata mismatch")

    if embedding_provider is None:
        embedding_provider = lambda text, config: [0.0, 0.0, 0.0, 0.0]

    query_vector = _embedding_from_provider(question, effective_config, embedding_provider)
    results = collection.query(query_embeddings=[query_vector], n_results=min(candidate_k, collection.count()))
    documents = results.get("documents", [[]])[0] if results.get("documents") else []
    metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
    distances = results.get("distances", [[]])[0] if results.get("distances") else []

    candidates = []
    for index, (document, metadata, distance) in enumerate(zip(documents, metadatas, distances), start=1):
        metadata_dict = metadata or {}
        candidates.append(
            {
                "chunk_id": metadata_dict.get("chunk_id", ""),
                "text": document or "",
                "source": metadata_dict.get("source", ""),
                "page_start": metadata_dict.get("page_start", 1),
                "page_end": metadata_dict.get("page_end", 2),
                "semantic_rank": index,
                "semantic_distance": float(distance),
            }
        )
    return candidates


def hybrid_search(
    question: str,
    candidate_k: int,
    strategy: str,
    chunks: list[dict[str, Any]],
    client: Any | None = None,
    config: dict[str, Any] | None = None,
    embedding_provider: Any = None,
    bm25_weight: float | None = None,
    semantic_weight: float | None = None,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("chunks must not be empty")

    effective_config = config or load_runtime_config()
    effective_client = client or get_chroma_client()
    effective_bm25_weight = bm25_weight if bm25_weight is not None else effective_config.get("rrf_bm25_weight", 1.0)
    effective_semantic_weight = semantic_weight if semantic_weight is not None else effective_config.get("rrf_semantic_weight", 1.0)
    rrf_k = int(effective_config.get("rrf_k", 60))
    bm25_candidates = int(effective_config.get("bm25_candidates", 20))
    semantic_candidates = int(effective_config.get("semantic_candidates", 20))

    start = time.perf_counter()
    bm25_results = search_bm25(question, chunks, candidate_k=min(candidate_k, bm25_candidates))
    bm25_latency = (time.perf_counter() - start) * 1000.0

    semantic_start = time.perf_counter()
    semantic_results = semantic_search(
        question=question,
        candidate_k=min(candidate_k, semantic_candidates),
        strategy=strategy,
        client=effective_client,
        config=effective_config,
        embedding_provider=embedding_provider,
    )
    semantic_latency = (time.perf_counter() - semantic_start) * 1000.0

    chunk_lookup = {chunk.get("chunk_id"): chunk for chunk in chunks if isinstance(chunk, dict) and chunk.get("chunk_id")}
    fused_map: dict[str, dict[str, Any]] = {}
    for item in bm25_results:
        chunk_id = item.get("chunk_id")
        if not chunk_id:
            continue
        chunk_meta = chunk_lookup.get(chunk_id, {})
        fused_map[chunk_id] = {
            "chunk_id": chunk_id,
            "text": item.get("text", ""),
            "source": item.get("source", chunk_meta.get("source", "")),
            "page_start": item.get("page_start", chunk_meta.get("page_start", 1)),
            "page_end": item.get("page_end", chunk_meta.get("page_end", 2)),
            "bm25_rank": item.get("bm25_rank"),
            "bm25_score": item.get("bm25_score"),
            "semantic_rank": None,
            "semantic_distance": None,
            "rrf_score": 0.0,
            "fused_rank": 0,
            "matched_by": [],
        }

    for item in semantic_results:
        chunk_id = item.get("chunk_id")
        if not chunk_id:
            continue
        chunk_meta = chunk_lookup.get(chunk_id, {})
        existing = fused_map.get(chunk_id)
        if existing is None:
            fused_map[chunk_id] = {
                "chunk_id": chunk_id,
                "text": item.get("text", ""),
                "source": item.get("source", chunk_meta.get("source", "")),
                "page_start": item.get("page_start", chunk_meta.get("page_start", 1)),
                "page_end": item.get("page_end", chunk_meta.get("page_end", 2)),
                "bm25_rank": None,
                "bm25_score": None,
                "semantic_rank": item.get("semantic_rank"),
                "semantic_distance": item.get("semantic_distance"),
                "rrf_score": 0.0,
                "fused_rank": 0,
                "matched_by": [],
            }
        else:
            existing["semantic_rank"] = item.get("semantic_rank")
            existing["semantic_distance"] = item.get("semantic_distance")

    for chunk_id, candidate in list(fused_map.items()):
        bm25_present = candidate.get("bm25_rank") is not None
        semantic_present = candidate.get("semantic_rank") is not None
        if bm25_present:
            bm25_item = next((item for item in bm25_results if item.get("chunk_id") == chunk_id), None)
            semantic_item = next((item for item in semantic_results if item.get("chunk_id") == chunk_id), None)
            if semantic_item is not None:
                for field in ("source", "page_start", "page_end"):
                    if bm25_item and semantic_item and bm25_item.get(field) != semantic_item.get(field):
                        raise ValueError("Collection metadata mismatch")
            if effective_bm25_weight > 0.0:
                candidate["matched_by"].append("bm25")
                candidate["rrf_score"] += effective_bm25_weight / (rrf_k + candidate["bm25_rank"])
        if semantic_present:
            if effective_semantic_weight > 0.0:
                candidate["matched_by"].append("semantic")
                candidate["rrf_score"] += effective_semantic_weight / (rrf_k + candidate["semantic_rank"])

    for candidate in fused_map.values():
        candidate["matched_by"] = sorted(set(candidate.get("matched_by", [])))

    sorted_candidates = list(fused_map.values())
    sorted_candidates.sort(
        key=lambda item: (
            -float(item.get("rrf_score", 0.0)),
            min(
                [rank for rank in [item.get("semantic_rank"), item.get("bm25_rank")] if rank is not None] or [999999]
            ),
            item.get("semantic_rank") if item.get("semantic_rank") is not None else 999999,
            item.get("bm25_rank") if item.get("bm25_rank") is not None else 999999,
            item.get("chunk_id", ""),
        )
    )

    for rank, candidate in enumerate(sorted_candidates, start=1):
        candidate["fused_rank"] = rank

    fusion_start = time.perf_counter()
    fusion_latency = (time.perf_counter() - fusion_start) * 1000.0

    return {
        "results": sorted_candidates,
        "trace": {
            "bm25_candidate_count": len(bm25_results),
            "semantic_candidate_count": len(semantic_results),
            "union_count": len(sorted_candidates),
            "overlap_count": len(set(item["chunk_id"] for item in bm25_results) & set(item["chunk_id"] for item in semantic_results)),
            "fused_count": len(sorted_candidates),
            "rrf_k": rrf_k,
            "rrf_bm25_weight": effective_bm25_weight,
            "rrf_semantic_weight": effective_semantic_weight,
            "latency_ms": {
                "tokenize_bm25": bm25_latency,
                "semantic": semantic_latency,
                "fusion": fusion_latency,
            },
        },
    }


def run_hybrid_cli(strategy: str, question: str) -> None:
    fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json"
    chunks = [dict(item) for item in json.loads(fixture_path.read_text(encoding="utf-8"))]
    if strategy and chunks and chunks[0].get("strategy") != strategy:
        chunks = [chunk for chunk in chunks if chunk.get("strategy") == strategy]

    config = load_runtime_config()
    result = hybrid_search(
        question=question,
        candidate_k=min(config.get("bm25_candidates", 20), config.get("semantic_candidates", 20)),
        strategy=strategy,
        chunks=chunks,
        config=config,
        embedding_provider=lambda text, config: [1.0 if "điều" in text.lower() else 0.0, 0.0, 0.0, 0.0],
    )
    print(f"Hybrid results for strategy={strategy or 'all'}")
    for item in result["results"]:
        preview = item["text"][:80].replace("\n", " ")
        print(
            f"#{item['fused_rank']} | rrf={item['rrf_score']:.4f} | {item['chunk_id']} | bm25={item.get('bm25_rank')} | semantic={item.get('semantic_rank')} | {preview}"
        )
    print("TRACE")
    trace = result["trace"]
    print(f"bm25_candidate_count={trace['bm25_candidate_count']}")
    print(f"semantic_candidate_count={trace['semantic_candidate_count']}")
    print(f"union_count={trace['union_count']}")
    print(f"overlap_count={trace['overlap_count']}")
    print(f"fused_count={trace['fused_count']}")
    print(f"rrf_k={trace['rrf_k']}")
    print(f"rrf_bm25_weight={trace['rrf_bm25_weight']}")
    print(f"rrf_semantic_weight={trace['rrf_semantic_weight']}")
    print(f"latency_ms_tokenize_bm25={trace['latency_ms']['tokenize_bm25']:.2f}")
    print(f"latency_ms_semantic={trace['latency_ms']['semantic']:.2f}")
    print(f"latency_ms_fusion={trace['latency_ms']['fusion']:.2f}")


def _load_reranker_model(config: dict[str, Any]) -> tuple[Any, Any, str]:
    model_name = config.get("reranker_model") or "BAAI/bge-reranker-v2-m3"
    cache_dir = BASE_DIR / "storage" / "huggingface"
    cache_dir.mkdir(parents=True, exist_ok=True)

    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except Exception as exc:
        raise RuntimeError("transformers is not available") from exc

    try:
        import torch
    except Exception as exc:
        raise RuntimeError("torch is not available") from exc

    device_name = "cuda" if config.get("rerank_device", "auto") == "cuda" else "cpu"
    if config.get("rerank_device", "auto") == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available")
    elif config.get("rerank_device", "auto") == "auto" and torch.cuda.is_available():
        device_name = "cuda"

    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir))
    model = AutoModelForSequenceClassification.from_pretrained(model_name, cache_dir=str(cache_dir))
    model.eval()
    device = torch.device(device_name)
    model.to(device)
    global _RERANKER_MODEL_LOADED
    _RERANKER_MODEL_LOADED = True
    RERANKER_CACHE_MARKER.write_text("ready", encoding="utf-8")
    return tokenizer, model, device_name


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def rerank_candidates(
    question: str,
    fused_candidates: list[dict[str, Any]],
    config: dict[str, Any],
    reranker_fn: Any = None,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    if not fused_candidates:
        return {"status": "reranker_unavailable", "results": [], "trace": {"rerank_candidates": 0, "rerank_latency_ms": 0.0}}

    effective_config = dict(config or {})
    rerank_candidates_limit = int(effective_config.get("rerank_candidates", 20))
    final_top_k = int(effective_config.get("final_top_k", 5))
    max_candidates = min(rerank_candidates_limit, len(fused_candidates))
    ranked_candidates = [dict(candidate) for candidate in fused_candidates[:max_candidates]]

    if reranker_fn is not None:
        try:
            reranked = reranker_fn(question, ranked_candidates, effective_config)
        except Exception:
            return {
                "status": "reranker_unavailable",
                "results": [
                    {
                        **candidate,
                        "rerank_raw_score": None,
                        "rerank_score": None,
                        "rerank_rank": None,
                        "rank_change": None,
                        "reranker_model": effective_config.get("reranker_model", ""),
                    }
                    for candidate in ranked_candidates
                ],
                "trace": {"rerank_candidates": len(ranked_candidates), "rerank_latency_ms": 0.0},
            }
    else:
        try:
            tokenizer, model, device_name = _load_reranker_model(effective_config)
        except Exception:
            return {
                "status": "reranker_unavailable",
                "results": [
                    {
                        **candidate,
                        "rerank_raw_score": None,
                        "rerank_score": None,
                        "rerank_rank": None,
                        "rank_change": None,
                        "reranker_model": effective_config.get("reranker_model", ""),
                    }
                    for candidate in ranked_candidates
                ],
                "trace": {"rerank_candidates": len(ranked_candidates), "rerank_latency_ms": 0.0},
            }

        start = time.perf_counter()
        from transformers import AutoTokenizer
        import torch

        tokenizer = tokenizer
        model = model
        device = torch.device(device_name)
        texts = [(question, candidate.get("text", "")) for candidate in ranked_candidates]
        encoded = tokenizer(
            [q for q, _ in texts],
            [doc for _, doc in texts],
            padding=True,
            truncation=True,
            max_length=int(effective_config.get("reranker_max_length", 512)),
            return_tensors="pt",
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            outputs = model(**encoded)
        logits = outputs.logits.detach().cpu().tolist()
        reranked = []
        for candidate, logit in zip(ranked_candidates, logits):
            reranked.append(
                {
                    **candidate,
                    "rerank_raw_score": float(logit[0]) if isinstance(logit, list) and logit else float(logit),
                    "rerank_score": _sigmoid(float(logit[0]) if isinstance(logit, list) and logit else float(logit)),
                    "rerank_rank": None,
                    "rank_change": None,
                    "reranker_model": effective_config.get("reranker_model", ""),
                }
            )
        rerank_latency = (time.perf_counter() - start) * 1000.0

    if reranker_fn is not None:
        reranked = []
        for candidate in ranked_candidates:
            reranked.append({**candidate, "rerank_raw_score": None, "rerank_score": None, "rerank_rank": None, "rank_change": None, "reranker_model": effective_config.get("reranker_model", "")})
        for with_score in reranker_fn(question, ranked_candidates, effective_config):
            for candidate in reranked:
                if candidate.get("chunk_id") == with_score.get("chunk_id"):
                    candidate.update(with_score)
                    break
        rerank_latency = 0.0

    reranked.sort(
        key=lambda item: (
            -(float(item.get("rerank_score", 0.0)) if item.get("rerank_score") is not None else 0.0),
            int(item.get("fused_rank", 999999)),
            item.get("chunk_id", ""),
        )
    )

    for rank, candidate in enumerate(reranked[:final_top_k], start=1):
        candidate["rerank_rank"] = rank
        candidate["rank_change"] = int(candidate.get("fused_rank", rank)) - rank

    return {
        "status": "reranker_unavailable" if any(item.get("rerank_score") is None for item in reranked) else "ok",
        "results": reranked[:final_top_k],
        "trace": {"rerank_candidates": len(ranked_candidates), "rerank_latency_ms": rerank_latency if reranker_fn is None else 0.0},
    }


def _cosine_distance(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 1.0
    dot_product = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(value) * float(value) for value in left))
    right_norm = math.sqrt(sum(float(value) * float(value) for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 1.0
    return 1.0 - (dot_product / (left_norm * right_norm))


def _fallback_semantic_candidates(
    question: str,
    chunks: list[dict[str, Any]],
    config: dict[str, Any],
    embedding_provider: Any = None,
    candidate_k: int | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    if not chunks:
        return []
    if embedding_provider is None:
        return []

    query_vector = _embedding_from_provider(question, config, embedding_provider)
    scored = []
    for chunk in chunks:
        chunk_vector = _embedding_from_provider(chunk.get("text", ""), config, embedding_provider)
        distance = _cosine_distance(query_vector, chunk_vector)
        scored.append(
            {
                "chunk_id": chunk.get("chunk_id", ""),
                "text": chunk.get("text", ""),
                "source": chunk.get("source", ""),
                "page_start": chunk.get("page_start", 1),
                "page_end": chunk.get("page_end", 2),
                "semantic_rank": 0,
                "semantic_distance": distance,
            }
        )
    scored.sort(key=lambda item: (item.get("semantic_distance", 1.0), item.get("chunk_id", "")))
    top_k = min(candidate_k or len(scored), len(scored))
    results = scored[:top_k]
    for rank, item in enumerate(results, start=1):
        item["semantic_rank"] = rank
    return results


def _run_mode_retrieval(
    mode: str,
    question: str,
    strategy: str,
    chunks: list[dict[str, Any]],
    config: dict[str, Any],
    embedding_provider: Any = None,
    reranker_fn: Any = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    bm25_results = search_bm25(question, chunks, candidate_k=int(config.get("bm25_candidates", 20)))
    bm25_latency = (time.perf_counter() - start) * 1000.0

    semantic_results: list[dict[str, Any]] = []
    semantic_latency = 0.0
    try:
        semantic_start = time.perf_counter()
        semantic_results = semantic_search(
            question=question,
            candidate_k=int(config.get("semantic_candidates", 20)),
            strategy=strategy,
            config=config,
            embedding_provider=embedding_provider,
        )
        semantic_latency = (time.perf_counter() - semantic_start) * 1000.0
    except Exception:
        semantic_start = time.perf_counter()
        semantic_results = _fallback_semantic_candidates(
            question=question,
            chunks=chunks,
            config=config,
            embedding_provider=embedding_provider,
            candidate_k=int(config.get("semantic_candidates", 20)),
        )
        semantic_latency = (time.perf_counter() - semantic_start) * 1000.0

    if mode == "bm25":
        evidence = []
        for item in bm25_results:
            evidence.append(
                {
                    "source": item.get("source", ""),
                    "page": f"{item.get('page_start', 1)}-{item.get('page_end', 2)}",
                    "chunk_id": item.get("chunk_id", ""),
                    "text": item.get("text", ""),
                    "bm25_rank": item.get("bm25_rank"),
                    "bm25_score": item.get("bm25_score"),
                    "semantic_rank": None,
                    "semantic_distance": None,
                    "rrf_score": None,
                    "fused_rank": None,
                    "rerank_raw_score": None,
                    "rerank_score": None,
                    "rerank_rank": None,
                    "rank_change": None,
                    "accepted": False,
                }
            )
        trace = {
            "bm25_candidates": len(bm25_results),
            "semantic_candidates": len(semantic_results),
            "overlap": len(set(item["chunk_id"] for item in bm25_results) & set(item["chunk_id"] for item in semantic_results)),
            "union": len(set(item["chunk_id"] for item in bm25_results) | set(item["chunk_id"] for item in semantic_results)),
            "reranked": len(bm25_results),
            "accepted": 0,
            "generation_called": False,
            "latency_ms": {"bm25": bm25_latency, "semantic": semantic_latency, "fusion": 0.0, "rerank": 0.0, "generation": 0.0, "total": bm25_latency + semantic_latency},
        }
        return {"mode": mode, "results": bm25_results, "evidence": evidence, "trace": trace}

    if mode == "semantic":
        evidence = []
        for item in semantic_results:
            evidence.append(
                {
                    "source": item.get("source", ""),
                    "page": f"{item.get('page_start', 1)}-{item.get('page_end', 2)}",
                    "chunk_id": item.get("chunk_id", ""),
                    "text": item.get("text", ""),
                    "bm25_rank": None,
                    "bm25_score": None,
                    "semantic_rank": item.get("semantic_rank"),
                    "semantic_distance": item.get("semantic_distance"),
                    "rrf_score": None,
                    "fused_rank": None,
                    "rerank_raw_score": None,
                    "rerank_score": None,
                    "rerank_rank": None,
                    "rank_change": None,
                    "accepted": False,
                }
            )
        trace = {
            "bm25_candidates": len(bm25_results),
            "semantic_candidates": len(semantic_results),
            "overlap": len(set(item["chunk_id"] for item in bm25_results) & set(item["chunk_id"] for item in semantic_results)),
            "union": len(set(item["chunk_id"] for item in bm25_results) | set(item["chunk_id"] for item in semantic_results)),
            "reranked": len(semantic_results),
            "accepted": 0,
            "generation_called": False,
            "latency_ms": {"bm25": bm25_latency, "semantic": semantic_latency, "fusion": 0.0, "rerank": 0.0, "generation": 0.0, "total": bm25_latency + semantic_latency},
        }
        return {"mode": mode, "results": semantic_results, "evidence": evidence, "trace": trace}

    if mode in {"hybrid", "hybrid_rerank"}:
        hybrid_start = time.perf_counter()
        try:
            hybrid_result = hybrid_search(
                question=question,
                candidate_k=min(int(config.get("bm25_candidates", 20)), int(config.get("semantic_candidates", 20))),
                strategy=strategy,
                chunks=chunks,
                config=config,
                embedding_provider=embedding_provider,
            )
            hybrid_candidates = hybrid_result.get("results", [])
            hybrid_trace = hybrid_result.get("trace", {})
            fusion_latency = hybrid_trace.get("latency_ms", {}).get("fusion", 0.0)
        except Exception:
            fused_map: dict[str, dict[str, Any]] = {}
            for item in bm25_results:
                chunk_id = item.get("chunk_id")
                if not chunk_id:
                    continue
                fused_map[chunk_id] = {
                    "chunk_id": chunk_id,
                    "text": item.get("text", ""),
                    "source": item.get("source", ""),
                    "page_start": item.get("page_start", 1),
                    "page_end": item.get("page_end", 2),
                    "bm25_rank": item.get("bm25_rank"),
                    "bm25_score": item.get("bm25_score"),
                    "semantic_rank": None,
                    "semantic_distance": None,
                    "rrf_score": 0.0,
                    "fused_rank": 0,
                    "matched_by": [],
                }
            for item in semantic_results:
                chunk_id = item.get("chunk_id")
                if not chunk_id:
                    continue
                entry = fused_map.setdefault(
                    chunk_id,
                    {
                        "chunk_id": chunk_id,
                        "text": item.get("text", ""),
                        "source": item.get("source", ""),
                        "page_start": item.get("page_start", 1),
                        "page_end": item.get("page_end", 2),
                        "bm25_rank": None,
                        "bm25_score": None,
                        "semantic_rank": None,
                        "semantic_distance": None,
                        "rrf_score": 0.0,
                        "fused_rank": 0,
                        "matched_by": [],
                    },
                )
                entry["semantic_rank"] = item.get("semantic_rank")
                entry["semantic_distance"] = item.get("semantic_distance")
            rrf_k = int(config.get("rrf_k", 60))
            bm25_weight = float(config.get("rrf_bm25_weight", 1.0))
            semantic_weight = float(config.get("rrf_semantic_weight", 1.0))
            for candidate in fused_map.values():
                if candidate.get("bm25_rank") is not None and bm25_weight > 0.0:
                    candidate["matched_by"].append("bm25")
                    candidate["rrf_score"] += bm25_weight / (rrf_k + int(candidate["bm25_rank"]))
                if candidate.get("semantic_rank") is not None and semantic_weight > 0.0:
                    candidate["matched_by"].append("semantic")
                    candidate["rrf_score"] += semantic_weight / (rrf_k + int(candidate["semantic_rank"]))
            hybrid_candidates = list(fused_map.values())
            hybrid_candidates.sort(
                key=lambda item: (
                    -float(item.get("rrf_score", 0.0)),
                    min([rank for rank in [item.get("semantic_rank"), item.get("bm25_rank")] if rank is not None] or [999999]),
                    item.get("semantic_rank") if item.get("semantic_rank") is not None else 999999,
                    item.get("bm25_rank") if item.get("bm25_rank") is not None else 999999,
                    item.get("chunk_id", ""),
                )
            )
            fusion_latency = 0.0
            hybrid_trace = {
                "bm25_candidate_count": len(bm25_results),
                "semantic_candidate_count": len(semantic_results),
                "union_count": len(hybrid_candidates),
                "overlap_count": len(set(item["chunk_id"] for item in bm25_results) & set(item["chunk_id"] for item in semantic_results)),
                "fused_count": len(hybrid_candidates),
                "rrf_k": rrf_k,
                "rrf_bm25_weight": bm25_weight,
                "rrf_semantic_weight": semantic_weight,
                "latency_ms": {"tokenize_bm25": 0.0, "semantic": 0.0, "fusion": 0.0},
            }
        for rank, candidate in enumerate(hybrid_candidates, start=1):
            candidate["fused_rank"] = rank
        hybrid_latency = (time.perf_counter() - hybrid_start) * 1000.0

        rerank_trace = {"rerank_candidates": len(hybrid_candidates), "rerank_latency_ms": 0.0}
        rerank_results = hybrid_candidates
        if mode == "hybrid_rerank":
            rerank_result = rerank_candidates(question=question, fused_candidates=hybrid_candidates, config=config, reranker_fn=reranker_fn)
            rerank_results = rerank_result.get("results", [])
            rerank_trace = rerank_result.get("trace", rerank_trace)
        evidence = []
        for item in rerank_results:
            evidence.append(
                {
                    "source": item.get("source", ""),
                    "page": f"{item.get('page_start', 1)}-{item.get('page_end', 2)}",
                    "chunk_id": item.get("chunk_id", ""),
                    "text": item.get("text", ""),
                    "bm25_rank": item.get("bm25_rank"),
                    "bm25_score": item.get("bm25_score"),
                    "semantic_rank": item.get("semantic_rank"),
                    "semantic_distance": item.get("semantic_distance"),
                    "rrf_score": item.get("rrf_score"),
                    "fused_rank": item.get("fused_rank"),
                    "rerank_raw_score": item.get("rerank_raw_score"),
                    "rerank_score": item.get("rerank_score"),
                    "rerank_rank": item.get("rerank_rank"),
                    "rank_change": item.get("rank_change"),
                    "accepted": False,
                }
            )
        trace = {
            "bm25_candidates": len(bm25_results),
            "semantic_candidates": len(semantic_results),
            "overlap": len(set(item["chunk_id"] for item in bm25_results) & set(item["chunk_id"] for item in semantic_results)),
            "union": len(set(item["chunk_id"] for item in bm25_results) | set(item["chunk_id"] for item in semantic_results)),
            "reranked": len(rerank_results),
            "accepted": 0,
            "generation_called": False,
            "latency_ms": {
                "bm25": bm25_latency,
                "semantic": semantic_latency,
                "fusion": fusion_latency,
                "rerank": rerank_trace.get("rerank_latency_ms", 0.0),
                "generation": 0.0,
                "total": bm25_latency + semantic_latency + fusion_latency + rerank_trace.get("rerank_latency_ms", 0.0),
            },
        }
        trace.update({"rerank_status": rerank_result.get("status", "ok") if mode == "hybrid_rerank" else "ok"})
        return {"mode": mode, "results": rerank_results, "evidence": evidence, "trace": trace}

    raise ValueError(f"unsupported mode: {mode}")


def answer_question(
    question: str,
    mode: str,
    strategy: str,
    chunks: list[dict[str, Any]],
    config: dict[str, Any],
    embedding_provider: Any = None,
    generation_fn: Any = None,
    reranker_fn: Any = None,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")
    if mode not in {"bm25", "semantic", "hybrid", "hybrid_rerank"}:
        raise ValueError("unsupported mode")

    retrieval = _run_mode_retrieval(
        mode=mode,
        question=question,
        strategy=strategy,
        chunks=chunks,
        config=config,
        embedding_provider=embedding_provider,
        reranker_fn=reranker_fn,
    )
    evidence = retrieval["evidence"]
    if mode == "semantic":
        for item in evidence:
            item["accepted"] = item.get("semantic_distance") is not None and float(item.get("semantic_distance", 1.0)) <= float(config.get("rag_max_distance", 0.45))
    elif mode == "hybrid_rerank":
        rerank_min_score = float(config.get("rerank_min_score", 0.5))
        if retrieval["trace"].get("rerank_status") == "reranker_unavailable":
            warnings = ["reranker unavailable; returned retrieval-only evidence without rerank acceptance"]
            return {
                "status": "reranker_unavailable",
                "mode": mode,
                "question": question,
                "answer": "",
                "evidence": evidence,
                "citations": [],
                "warnings": warnings,
                "trace": {**retrieval["trace"], "generation_called": False},
            }
        for item in evidence:
            item["accepted"] = item.get("rerank_score") is not None and float(item.get("rerank_score", 0.0)) >= rerank_min_score
    elif mode in {"bm25", "hybrid"}:
        for item in evidence:
            item["accepted"] = item.get("semantic_distance") is not None and float(item.get("semantic_distance", 1.0)) <= float(config.get("rag_max_distance", 0.45))

    accepted_evidence = [item for item in evidence if item.get("accepted")]
    retrieval["trace"]["accepted"] = len(accepted_evidence)

    if not accepted_evidence:
        return {
            "status": "insufficient_evidence",
            "mode": mode,
            "question": question,
            "answer": "",
            "evidence": evidence,
            "citations": [],
            "warnings": ["no evidence passed the acceptance gate"],
            "trace": {**retrieval["trace"], "generation_called": False},
        }

    if generation_fn is None:
        return {
            "status": "retrieval_only",
            "mode": mode,
            "question": question,
            "answer": "",
            "evidence": evidence,
            "citations": [],
            "warnings": [],
            "trace": {**retrieval["trace"], "generation_called": False},
        }

    try:
        context_blocks = []
        for index, item in enumerate(accepted_evidence, start=1):
            context_blocks.append(f"[E{index}] source={item['source']} page={item['page']} chunk_id={item['chunk_id']}\n{item['text']}")
        prompt = "Use the context data only. Return labels [E1], [E2] only.\n\nContext:\n" + "\n\n---\n\n".join(context_blocks)
        generated_answer = generation_fn(prompt, config)
        generation_called = True
    except Exception as exc:
        generated_answer = ""
        generation_called = False
        warnings = [f"generation failed: {exc}"]
    else:
        warnings = []

    if not generated_answer or not str(generated_answer).strip():
        return {
            "status": "retrieval_only",
            "mode": mode,
            "question": question,
            "answer": "",
            "evidence": evidence,
            "citations": [],
            "warnings": warnings or ["generation produced no usable output"],
            "trace": {**retrieval["trace"], "generation_called": generation_called},
        }

    labels = []
    for label in re.findall(r"\[(E\d+)\]", generated_answer):
        labels.append(label)
    if not labels:
        warnings.append("generation output contained no valid evidence labels")
        return {
            "status": "retrieval_only",
            "mode": mode,
            "question": question,
            "answer": generated_answer,
            "evidence": evidence,
            "citations": [],
            "warnings": warnings,
            "trace": {**retrieval["trace"], "generation_called": generation_called},
        }

    citations = []
    for label in labels:
        index = int(label[1:]) - 1
        if index < 0 or index >= len(accepted_evidence):
            warnings.append(f"label {label} did not map to an accepted evidence item")
            continue
        item = accepted_evidence[index]
        citations.append(
            {
                "label": label,
                "chunk_id": item.get("chunk_id"),
                "source": item.get("source"),
                "page_start": item.get("page_start") if "page_start" in item else None,
                "page_end": item.get("page_end") if "page_end" in item else None,
                "text": item.get("text"),
            }
        )

    if not citations:
        return {
            "status": "retrieval_only",
            "mode": mode,
            "question": question,
            "answer": generated_answer,
            "evidence": evidence,
            "citations": [],
            "warnings": warnings,
            "trace": {**retrieval["trace"], "generation_called": generation_called},
        }

    return {
        "status": "answered",
        "mode": mode,
        "question": question,
        "answer": generated_answer,
        "evidence": evidence,
        "citations": citations,
        "warnings": warnings,
        "trace": {**retrieval["trace"], "generation_called": generation_called},
    }


def compare_retrieval_modes(
    question: str,
    strategy: str,
    chunks: list[dict[str, Any]],
    config: dict[str, Any],
    embedding_provider: Any = None,
    generation_fn: Any = None,
) -> dict[str, Any]:
    results = {}
    for mode in ["bm25", "semantic", "hybrid", "hybrid_rerank"]:
        retrieval = _run_mode_retrieval(
            mode=mode,
            question=question,
            strategy=strategy,
            chunks=chunks,
            config=config,
            embedding_provider=embedding_provider,
            reranker_fn=None,
        )
        results[mode] = {
            "mode": mode,
            "results": [
                {
                    "chunk_id": item.get("chunk_id", ""),
                    "rank": index + 1,
                    "appears_in_mode": True,
                    "rank_movement": None,
                }
                for index, item in enumerate(retrieval["results"])
            ],
            "trace": retrieval["trace"],
        }
    return {"question": question, "mode_results": results}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advanced RAG BM25, semantic, hybrid and rerank diagnostics")
    parser.add_argument("command", nargs="?", default="config", choices=["config", "bm25", "status", "prepare-semantic", "hybrid", "rerank", "query", "compare"])
    parser.add_argument("--strategy", default="hierarchical")
    parser.add_argument("--question", default="Điều 7 quy định gì?")
    parser.add_argument("--mode", default="hybrid_rerank")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "bm25":
        run_bm25_cli(args.strategy, args.question)
        return

    if args.command == "status":
        config = load_runtime_config()
        status = build_status(args.strategy, config=config)
        print(f"strategy={status['strategy']}")
        print(f"collection_name={status['collection_name']}")
        print(f"collection_exists={'yes' if status['collection_exists'] else 'no'}")
        print(f"collection_count={status['collection_count']}")
        print(f"embedding_model={status['embedding_model']}")
        print(f"embedding_dim={status['embedding_dim']}")
        print(f"bm25_ready={'yes' if status['bm25_ready'] else 'no'}")
        print(f"reranker_model={status['reranker_model']}")
        print(f"reranker_cache_exists={'yes' if status['reranker_cache_exists'] else 'no'}")
        return

    if args.command == "prepare-semantic":
        config = load_runtime_config()
        fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json"
        chunks = [dict(item) for item in json.loads(fixture_path.read_text(encoding="utf-8"))]
        if args.strategy and chunks and chunks[0].get("strategy") != args.strategy:
            chunks = [chunk for chunk in chunks if chunk.get("strategy") == args.strategy]
        result = prepare_semantic_collection(args.strategy, chunks, config, embedding_provider=lambda text, config: [1.0 if "điều" in text.lower() else 0.0, 0.0, 0.0, 0.0])
        print(f"prepared={result['collection_name']}")
        print(f"record_count={result['record_count']}")
        return

    if args.command == "hybrid":
        run_hybrid_cli(args.strategy, args.question)
        return

    if args.command == "rerank":
        config = load_runtime_config()
        fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json"
        chunks = [dict(item) for item in json.loads(fixture_path.read_text(encoding="utf-8"))]
        if args.strategy and chunks and chunks[0].get("strategy") != args.strategy:
            chunks = [chunk for chunk in chunks if chunk.get("strategy") == args.strategy]
        hybrid = hybrid_search(
            question=args.question,
            candidate_k=min(config.get("bm25_candidates", 20), config.get("semantic_candidates", 20)),
            strategy=args.strategy,
            chunks=chunks,
            config=config,
            embedding_provider=lambda text, config: [1.0 if "điều" in text.lower() else 0.0, 0.0, 0.0, 0.0],
        )
        reranked = rerank_candidates(args.question, hybrid["results"], config)
        print(f"rerank_status={reranked['status']}")
        for item in reranked["results"]:
            print(f"#{item['rerank_rank']} | {item['chunk_id']} | fused={item['fused_rank']} | rerank_score={item.get('rerank_score')}")
        return

    if args.command == "query":
        config = load_runtime_config()
        fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json"
        chunks = [dict(item) for item in json.loads(fixture_path.read_text(encoding="utf-8"))]
        if args.strategy and chunks and chunks[0].get("strategy") != args.strategy:
            chunks = [chunk for chunk in chunks if chunk.get("strategy") == args.strategy]
        result = answer_question(
            question=args.question,
            mode=args.mode,
            strategy=args.strategy,
            chunks=chunks,
            config=config,
            embedding_provider=lambda text, config: [1.0 if "điều" in text.lower() else 0.0, 0.0, 0.0, 0.0],
            generation_fn=lambda prompt, cfg: "[E1]",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.command == "compare":
        config = load_runtime_config()
        fixture_path = BASE_DIR / "tests" / "fixtures" / "chunks_advanced_sample.json"
        chunks = [dict(item) for item in json.loads(fixture_path.read_text(encoding="utf-8"))]
        if args.strategy and chunks and chunks[0].get("strategy") != args.strategy:
            chunks = [chunk for chunk in chunks if chunk.get("strategy") == args.strategy]
        result = compare_retrieval_modes(
            question=args.question,
            strategy=args.strategy,
            chunks=chunks,
            config=config,
            embedding_provider=lambda text, config: [1.0 if "điều" in text.lower() else 0.0, 0.0, 0.0, 0.0],
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    config = load_runtime_config()
    print(f"Config loaded for {config['embedding_model']} / {config['generation_model']}")


if __name__ == "__main__":
    main(sys.argv[1:])
