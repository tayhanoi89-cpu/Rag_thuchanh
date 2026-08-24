# Buoi 14

## Prepare Corpus

The corpus preparation script reads the read-only `metadata.csv`, `content.csv`, and `relationships.csv` source files, cleans HTML text, and writes:

```text
data/processed/chunks_normalized.csv
```

Run from the Buoi 14 directory with its virtual environment:

```powershell
& ".venv\Scripts\python.exe" scripts\prepare_corpus.py
```

The current workspace stores the source data at `graph_rag_labs/graph_rag_labs/kb+hops/`; the script reports this fallback because the documented sibling `../kb+hops/` directory is not present.

## Mini Knowledge Graph

The loader reads the same source data and writes only Buoi 14-scoped Neo4j nodes and relationships with `lab_session="buoi_14"`:

```powershell
& ".venv\Scripts\python.exe" scripts\load_mini_kg.py
```

It does not delete existing Neo4j data. The build summary is written to `outputs/kg_build_report.md`, and the Cypher examples are in `cypher/demo_queries.cypher`.

## Unified Query Demo

Run retrieval with one of `bm25`, `dense`, `hybrid`, or `hybrid_rerank`:

```powershell
& ".venv\Scripts\python.exe" scripts\query_demo.py --query "01/2014/TT-NHNN" --method hybrid_rerank --top-k 5
```

The command prints standardized results with citation, then direct Buoi 14 Neo4j graph hints. Retrieval still works when Neo4j is unavailable; only the hints section reports the connection issue.

## Streamlit Demo

Run from the Buoi 14 directory:

```powershell
& ".venv\Scripts\python.exe" -m streamlit run app.py
```

Choose `BM25`, `Dense`, `Hybrid`, or `Hybrid + Rerank`, then set `Top-k` and select `Tìm kiếm`. Stop the server with `Ctrl+C` in the terminal. Results retain `chunk_id`, `document_id`, score, retrieval method, citation, and text; Hybrid + Rerank also shows the before/after ranking table. Graph hints are direct Buoi 14 relationships only.