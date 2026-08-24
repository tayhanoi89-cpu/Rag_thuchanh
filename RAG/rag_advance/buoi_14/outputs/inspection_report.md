# Buoi 14 Project Pre-Check

## PROJECT PRE-CHECK

- Working root: `RAG/rag_advance/buoi_14`
- Python: 3.14.6
- Virtual environment: `buoi_14/.venv` exists and runs successfully.
- pandas: missing from `buoi_14/.venv`.
- requirements.txt: not present.

## Source Path Check

The documented source path does not exist:

```text
RAG/rag_advance/kb+hops/
```

The source files found in the workspace are instead located at:

```text
graph_rag_labs/graph_rag_labs/kb+hops/
```

The three source files were read only. They were not copied, moved, modified, or overwritten.

## Source CSV Inspection

### metadata.csv

- Rows: 15
- Columns: `id`, `title`, `so_ky_hieu`, `ngay_ban_hanh`, `loai_van_ban`, `ngay_co_hieu_luc`, `ngay_het_hieu_luc`, `nguon_thu_thap`, `ngay_dang_cong_bao`, `nganh`, `linh_vuc`, `co_quan_ban_hanh`, `chuc_danh`, `nguoi_ky`, `pham_vi`, `thong_tin_ap_dung`, `tinh_trang_hieu_luc`
- Encoding: UTF-8 compatible; no UTF-8 BOM detected.
- Key candidate: `id`.
- Duplicate `id`: none.
- Null/empty values: `ngay_co_hieu_luc` 1, `ngay_het_hieu_luc` 14, `nguon_thu_thap` 5, `ngay_dang_cong_bao` 11, `nganh` 3, `linh_vuc` 2, `thong_tin_ap_dung` 15.
- Retrieval/citation metadata: `title`, `so_ky_hieu`, `loai_van_ban`, `ngay_ban_hanh`, `ngay_co_hieu_luc`, `tinh_trang_hieu_luc`, and `id`.

### content.csv

- Rows: 15
- Columns: `id`, `content_html`.
- Encoding: UTF-8 compatible; no UTF-8 BOM detected.
- Key candidate: `id`, matching `metadata.csv`.
- Duplicate `id`: none.
- Null/empty values: none detected.
- Retrieval text candidate: `content_html`; it must be cleaned from HTML in a later corpus-preparation step without removing article numbers or document codes.

### relationships.csv

- Rows: 8
- Columns: `doc_id`, `other_doc_id`, `relationship`, `relationship_type`.
- Encoding: UTF-8 compatible; no UTF-8 BOM detected.
- Key candidates: composite edge `(doc_id, other_doc_id, relationship_type)`.
- Empty values: none detected.
- Relationship types actually present:
  - `CAN_CU`: 4
  - `SUA_DOI_BO_SUNG`: 1
  - `VAN_BAN_BO_SUNG`: 1
  - `THAY_THE`: 1
  - `HOP_NHAT`: 1
- Repeated endpoint values are valid for multiple edges; no duplicate full edge was identified.
- These are the only relationship types that may be used for the mini Knowledge Graph.

## Existing Code and Safety Scan

- No Python pipeline files exist in `buoi_14/` yet.
- No `requirements.txt`, JSON, CSV, or `.env` project files exist in `buoi_14/` yet.
- The destructive-operation strings in `buoi14.md` are instructional text, not executable code.
- No executable `os.remove`, `shutil.rmtree`, `DELETE`, `DROP`, or `DETACH DELETE` operation was found in Buoi 14 code, because no Buoi 14 code exists yet.
- No retrieval or Knowledge Graph operation was run.

## Potential Risks / Blockers

1. The documented `../kb+hops/` path is missing. The actual source is in `graph_rag_labs/graph_rag_labs/kb+hops/`.
2. `pandas` is not installed in `buoi_14/.venv`.
3. BM25, dense embedding, reranking, and Neo4j dependencies are not installed in `buoi_14/.venv`.

Suggested dependencies for a later setup step:

```text
pandas
rank-bm25
sentence-transformers
transformers
neo4j
```

LangChain and LlamaIndex are not required by the current design.

## Decision

```text
Safe to continue: NO
```

Resolve the source path and install only the required dependencies in `buoi_14/.venv` before Prompt 1.