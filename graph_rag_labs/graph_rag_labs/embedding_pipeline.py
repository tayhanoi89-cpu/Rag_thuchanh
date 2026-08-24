from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from chunking_pipeline import build_chunks_from_csv


MODEL_NAME = "thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5"
BATCH_SIZE = 16


def collect_texts(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    def walk(node: dict[str, Any]) -> None:
        if node.get("type") in {"chapter", "article", "muc", "clause"}:
            chunks.append(node)
        for child in node.get("children", []):
            walk(child)

    for document in documents:
        walk(document)

    return chunks


def embed_chunks(chunks: list[dict[str, Any]], batch_size: int = BATCH_SIZE) -> list[dict[str, Any]]:
    model = SentenceTransformer(MODEL_NAME, device="cpu")
    texts = [chunk.get("text", "") for chunk in chunks]

    embeddings = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        batch_embeddings = model.encode(batch, normalize_embeddings=True, convert_to_numpy=True)
        embeddings.extend(batch_embeddings)

    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding.tolist()
        chunk["embedding_dim"] = len(embedding)

    return chunks


def print_embedding_preview(chunks: list[dict[str, Any]], limit: int = 3) -> None:
    print("Embedding preview:")
    for chunk in chunks[:limit]:
        embedding = chunk.get("embedding") or []
        print(f"- {chunk['type']}: {chunk['title']}")
        print(f"  dimension={chunk.get('embedding_dim', len(embedding))}")
        print(f"  sample={embedding[:8]}")


def main() -> None:
    data_dir = Path(__file__).resolve().parent / "kb+hops"
    documents = build_chunks_from_csv(data_dir)
    chunks = collect_texts(documents)
    embedded_chunks = embed_chunks(chunks)
    print_embedding_preview(embedded_chunks)
    print(f"Embedded {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    main()
