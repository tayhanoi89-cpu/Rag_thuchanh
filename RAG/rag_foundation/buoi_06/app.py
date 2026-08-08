"""Simple Streamlit RAG demo for the workshop project."""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

import rag


load_dotenv()


st.set_page_config(page_title="RAG Demo", page_icon="🧠", layout="wide")


def _sidebar_status() -> None:
    st.sidebar.title("RAG Status")
    conn, mode = rag._get_storage_connection()
    conn.close()
    pg_status = "Connected" if mode == "postgres" else "Fallback SQLite"
    st.sidebar.write(f"- PostgreSQL: {pg_status}")

    collection = rag._get_chroma_collection()
    chroma_status = "Ready" if collection is not None else "Not ready"
    st.sidebar.write(f"- ChromaDB: {chroma_status}")

    gemini_status = "Available" if os.getenv("GEMINI_API_KEY") else "Missing"
    st.sidebar.write(f"- Gemini API Key: {gemini_status}")


def _run_index() -> None:
    result = rag.index()
    st.session_state["index_result"] = result
    st.success(f"Index xong: {result['chunks']} chunks, {result['documents']} documents")


def _run_query(question: str, k: int = 3) -> tuple[list[dict], str]:
    return rag.retrieve(question, k)


def main() -> None:
    _sidebar_status()

    st.title("RAG Demo")
    st.caption("Question → Top-k → Gemini → Answer")

    if st.button("Index"):
        _run_index()

    if "index_result" in st.session_state:
        result = st.session_state["index_result"]
        st.info(f"Documents: {result['documents']} | Chunks: {result['chunks']}")

    question = st.text_area("Question", placeholder="Enter your question...")
    if st.button("Ask") and question.strip():
        top_k, answer = _run_query(question)

        st.subheader("Top-k")
        if top_k:
            for idx, item in enumerate(top_k, start=1):
                with st.expander(f"{idx}. {item['chunk_id']}"):
                    st.write(item["text"][:2500])
        else:
            st.write(answer)

        st.subheader("Answer")
        st.write(answer)


if __name__ == "__main__":
    main()
