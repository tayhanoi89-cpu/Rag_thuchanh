# Buoi 14 Final Validation Report

## Result

```text
READY FOR DEMO: YES
```

## Checklist

- PASS: All new Buoi 14 code and outputs are under `RAG/rag_advance/buoi_14/`.
- PASS: The prior source project was not edited by this workflow.
- PASS: Corpus normalized to 15 full-document records in `data/processed/chunks_normalized.csv`.
- PASS: BM25 retrieval runs with `rank-bm25`.
- PASS: Dense retrieval runs with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- PASS: Hybrid retrieval uses both rank lists and RRF; raw BM25 and cosine scores are not added.
- PASS: Reranker processes Hybrid candidates only and ran as `NEURAL_CROSS_ENCODER`.
- PASS: Before/After reranking was observed for exact, semantic, and mixed queries.
- PASS: Citations remain in baseline, Hybrid, reranked, unified CLI, and Streamlit output.
- PASS: Evaluation compares BM25, Dense, Hybrid, and Hybrid + Rerank with Hit@1/3/5 and MRR.
- PASS: Streamlit app imports and serves `RAG Hybrid Search - Buoi 14` at `http://localhost:8501`.
- PASS: Streamlit uses the unified retrieval API and displays results, citations, reranking comparison, and graph hints.
- PASS: Mini KG contains only source-backed relationship types.
- PASS: Neo4j data is scoped with `lab_session = "buoi_14"`; no whole-database delete was run.
- PASS: Mini KG report shows 15 `VanBan`, 15 `DieuKhoan`, 15 `CONTAINS`, 8 source relationships, and 0 orphan nodes.
- PASS: Python compilation and required imports succeed.

## Known Limitations

- The documented `../kb+hops/` path is absent in this workspace. The scripts use the verified read-only fallback at `graph_rag_labs/graph_rag_labs/kb+hops/` and report that choice.
- The corpus currently contains full-document records, so no `NEXT` relationships are created.
- Evaluation has three verified questions and is not evidence for production quality.
- `RR`/source output in some PowerShell pipelines can display Vietnamese text as mojibake if the shell decodes UTF-8 incorrectly; the Python CLI itself is configured for UTF-8 and the retrieval contract passes.