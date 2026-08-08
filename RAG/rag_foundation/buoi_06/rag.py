"""Simple RAG workflow for the workshop project."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

try:
    import psycopg
except Exception:  # pragma: no cover - fallback when psycopg is unavailable
    psycopg = None

try:
    import chromadb
except Exception:  # pragma: no cover - fallback when ChromaDB is unavailable
    chromadb = None

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - fallback for environments without the SDK
    genai = None
    types = None


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHUNKS_DIR = BASE_DIR.parent / "buoi_05" / "output" / "chunks"
LOCAL_DB = BASE_DIR / "rag_local.db"
TABLE_NAME = "rag_chunks"
EMBEDDING_DIM = 384
DEFAULT_K = 3


def index() -> dict:
    """Read chunk JSON files, create embeddings, and store them."""
    rows = []
    for path in sorted(CHUNKS_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        for item in data:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            chunk_id = item.get("chunk_id") or f"chunk-{len(rows) + 1}"
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": path.stem,
                    "source": item.get("source") or path.stem,
                    "text": text,
                    "embedding": _embed_text(text),
                }
            )

    conn, mode = _get_storage_connection()
    try:
        _reset_storage(conn, mode)
        _save_rows(conn, mode, rows)
        count_result = _count_rows(conn, mode)
    finally:
        conn.close()

    client = _get_chroma_client()
    if client is not None:
        try:
            client.delete_collection(name="rag_chunks")
        except Exception:
            pass
        collection = client.create_collection(name="rag_chunks", metadata={"hnsw:space": "cosine"})
        if rows:
            collection.add(
                ids=[row["chunk_id"] for row in rows],
                embeddings=[row["embedding"] for row in rows],
                documents=[row["text"] for row in rows],
                metadatas=[
                    {"chunk_id": row["chunk_id"], "source": row["source"], "document_id": row["document_id"]}
                    for row in rows
                ],
            )
    return {"documents": int(count_result[0] or 0), "chunks": int(count_result[1] or 0)}


def ask(question: str, k: int = DEFAULT_K) -> str:
    """Retrieve relevant chunks and answer the question."""
    if not question.strip():
        return "Câu hỏi trống."

    top_k = _collect_top_k(question, k)
    if not top_k:
        return "Chưa có dữ liệu phù hợp để trả lời câu hỏi này."

    return _build_answer(question, top_k)


def retrieve(question: str, k: int = DEFAULT_K) -> tuple[list[dict], str]:
    """Retrieve top-k results and an answer for the given question."""
    if not question.strip():
        return [], "Câu hỏi trống."

    top_k = _collect_top_k(question, k)
    if not top_k:
        return [], "Chưa có dữ liệu phù hợp để trả lời câu hỏi này."

    return top_k, _build_answer(question, top_k)


def status() -> dict:
    """Return document and chunk counts."""
    conn, mode = _get_storage_connection()
    try:
        row = _count_rows(conn, mode)
        if row:
            return {"documents": int(row[0] or 0), "chunks": int(row[1] or 0)}
    except Exception:
        return {"documents": 0, "chunks": 0}
    finally:
        conn.close()
    return {"documents": 0, "chunks": 0}


def answer_question(question: str) -> str:
    """Compatibility wrapper for the demo app."""
    return ask(question)


def _collect_top_k(question: str, k: int) -> list[dict]:
    collection = _get_chroma_collection()
    if collection is not None:
        embedding = _embed_text(question)
        result = collection.query(query_embeddings=[embedding], n_results=max(1, k))
        ids = result.get("ids", [[]])[0]
        if ids:
            conn, mode = _get_storage_connection()
            try:
                texts = [_get_text(conn, mode, chunk_id) for chunk_id in ids]
            finally:
                conn.close()
            top_k = []
            for chunk_id, text in zip(ids, texts):
                if text:
                    top_k.append({"chunk_id": chunk_id, "text": text})
            if top_k:
                return top_k

    return _fallback_retrieve(question, k)


def _fallback_retrieve(question: str, k: int) -> list[dict]:
    conn, mode = _get_storage_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT chunk_id, text FROM {TABLE_NAME}")
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    question_embedding = _embed_text(question)
    scored_rows = []
    for chunk_id, text in rows:
        if not text:
            continue
        chunk_embedding = _fallback_embedding(text)
        score = _cosine_similarity(question_embedding, chunk_embedding)
        scored_rows.append((score, chunk_id, text))

    scored_rows.sort(key=lambda item: item[0], reverse=True)
    return [
        {"chunk_id": chunk_id, "text": text, "score": round(score, 4)}
        for score, chunk_id, text in scored_rows[: max(1, k)]
    ]


def _build_answer(question: str, top_k: list[dict]) -> str:
    context = "\n\n---\n\n".join(item["text"] for item in top_k if item.get("text"))
    if not context:
        return "Chưa có dữ liệu phù hợp để trả lời câu hỏi này."

    if not os.getenv("GEMINI_API_KEY") or genai is None or types is None:
        return "Không có GEMINI_API_KEY hoặc SDK Gemini không khả dụng nên tôi chỉ trả lời dựa trên các đoạn liên quan:\n\n" + context[:2500]

    prompt = (
        "Bạn là trợ lý trả lời câu hỏi dựa trên ngữ cảnh dưới đây. "
        "Trả lời bằng tiếng Việt, ngắn gọn và chính xác.\n\n"
        f"Câu hỏi: {question}\n\nNgữ cảnh:\n{context}"
    )
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt,
        )
        return getattr(response, "text", "") or "Không có câu trả lời."
    except Exception:
        return "Không thể tạo câu trả lời lúc này."


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _embed_text(text: str) -> List[float]:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and genai is not None and types is not None:
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model="gemini-embedding-2",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
            )
            values = getattr(getattr(response, "embeddings", [None])[0], "values", None)
            if values:
                return [float(v) for v in values]
        except Exception:
            pass
    return _fallback_embedding(text)


def _fallback_embedding(text: str) -> List[float]:
    vector = [0.0] * EMBEDDING_DIM
    if not text:
        return vector
    tokens = re.findall(r"\w+", text.lower())
    for token in tokens:
        index = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16) % EMBEDDING_DIM
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def _get_storage_connection():
    if psycopg is not None:
        try:
            conn = psycopg.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=os.getenv("POSTGRES_DB", "postgres"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            )
            conn.autocommit = True
            return conn, "postgres"
        except Exception:
            pass
    conn = sqlite3.connect(LOCAL_DB)
    return conn, "sqlite"


def _reset_storage(conn, mode: str) -> None:
    if mode == "postgres":
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
            cur.execute(
                f"CREATE TABLE {TABLE_NAME} (chunk_id TEXT PRIMARY KEY, document_id TEXT, source TEXT, text TEXT)"
            )
    else:
        cur = conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        cur.execute(
            f"CREATE TABLE {TABLE_NAME} (chunk_id TEXT PRIMARY KEY, document_id TEXT, source TEXT, text TEXT)"
        )
        cur.close()
        conn.commit()


def _save_rows(conn, mode: str, rows: List[dict]) -> None:
    if not rows:
        return
    if mode == "postgres":
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    f"INSERT INTO {TABLE_NAME} (chunk_id, document_id, source, text) VALUES (%s, %s, %s, %s)",
                    (row["chunk_id"], row["document_id"], row["source"], row["text"]),
                )
    else:
        cur = conn.cursor()
        for row in rows:
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (chunk_id, document_id, source, text) VALUES (?, ?, ?, ?)",
                (row["chunk_id"], row["document_id"], row["source"], row["text"]),
            )
        cur.close()
        conn.commit()


def _get_text(conn, mode: str, chunk_id: str) -> Optional[str]:
    if mode == "postgres":
        with conn.cursor() as cur:
            cur.execute(f"SELECT text FROM {TABLE_NAME} WHERE chunk_id = %s", (chunk_id,))
            row = cur.fetchone()
            return row[0] if row else None
    cur = conn.cursor()
    cur.execute(f"SELECT text FROM {TABLE_NAME} WHERE chunk_id = ?", (chunk_id,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def _count_rows(conn, mode: str):
    if mode == "postgres":
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(DISTINCT source), COUNT(*) FROM {TABLE_NAME}")
            return cur.fetchone()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(DISTINCT source), COUNT(*) FROM {TABLE_NAME}")
    row = cur.fetchone()
    cur.close()
    return row


def _get_chroma_client():
    if chromadb is None:
        return None
    return chromadb.PersistentClient(path=str(BASE_DIR / "chroma_db"))


def _get_chroma_collection():
    try:
        client = _get_chroma_client()
        if client is None:
            return None
        return client.get_collection(name="rag_chunks")
    except Exception:
        return None
