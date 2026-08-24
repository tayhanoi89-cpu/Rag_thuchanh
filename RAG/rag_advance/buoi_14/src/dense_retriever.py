"""Dense multilingual retriever with a Buoi 14-local embedding cache."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

from .corpus import PROJECT_ROOT, load_corpus, result


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CACHE_DIR = PROJECT_ROOT / "cache"
EMBEDDINGS_PATH = CACHE_DIR / "document_embeddings.npy"
MANIFEST_PATH = CACHE_DIR / "document_embeddings.json"


_ST_MODELS: dict[str, Any] = {}


def _get_st_model(model_name: str) -> Any:
    if SentenceTransformer is None:
        return None
    if model_name not in _ST_MODELS:
        try:
            _ST_MODELS[model_name] = SentenceTransformer(model_name)
        except Exception:
            _ST_MODELS[model_name] = None
    return _ST_MODELS[model_name]


class DenseRetriever:
    def __init__(self, rows: list[dict[str, str]] | None = None, model_name: str = MODEL_NAME) -> None:
        self.rows = rows or load_corpus()
        self.model_name = model_name
        self.model = _get_st_model(model_name)
        self.embeddings = self._load_or_encode()

    def _corpus_hash(self) -> str:
        payload = "\n".join(f"{row['chunk_id']}\t{row['text']}" for row in self.rows)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load_or_encode(self) -> np.ndarray:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        corpus_hash = self._corpus_hash()
        if EMBEDDINGS_PATH.exists() and MANIFEST_PATH.exists():
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            if manifest.get("model") == self.model_name and manifest.get("corpus_hash") == corpus_hash:
                return np.load(EMBEDDINGS_PATH)

        embeddings = self.model.encode(
            [row["text"] for row in self.rows],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        np.save(EMBEDDINGS_PATH, embeddings)
        MANIFEST_PATH.write_text(
            json.dumps({"model": self.model_name, "corpus_hash": corpus_hash}, indent=2),
            encoding="utf-8",
        )
        return embeddings

    def search(self, question: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_embedding = self.model.encode([question], convert_to_numpy=True, normalize_embeddings=True)[0]
        scores = self.embeddings @ query_embedding
        ranked = sorted(enumerate(scores), key=lambda item: (-float(item[1]), item[0]))[:top_k]
        return [result(self.rows[index], float(score), "dense", rank) for rank, (index, score) in enumerate(ranked, 1)]