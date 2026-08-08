# Agent Specification - Buổi 07

## Workspace
- Read-only areas:
  - rag_foundation/buoi_05/output/chunks/
  - rag_foundation/buoi_05/.venv/
  - rag_foundation/buoi_06/
  - rag_foundation/buoi_07/
- Writeable area:
  - rag_foundation/buoi_07/
- Do not modify Buổi 05 or Buổi 06.

## Python
- Use the Buổi 05 virtual environment.
- Do not create a new virtual environment.
- Use Path(__file__).resolve() for all filesystem paths.

## Input
- Use JSON files from buoi_05/output/chunks/.
- Buổi 05 is the prepared source of truth.
- Do not OCR, parse PDFs, or re-chunk input data.

## Packages
- Use only the packages listed in requirements.txt.
- Keep versions compatible and patch-friendly.

## Pipeline
1. Validate input JSON.
2. Create embeddings.
3. Store vectors in Chroma persistent storage.
4. Retrieve top evidence.
5. Apply confidence gate.
6. Generate an answer.
7. Add citations.
8. Expose the workflow via Streamlit.
9. Use unittest for offline tests.

## Data Contract
Each chunk must have:
- chunk_id
- strategy
- source
- page_start
- page_end
- text

## Index Contract
- One strategy per collection.
- Model and dimension of index/query must match.
- Use real embeddings, not fake vectors.
- Reject NaN, Infinity, booleans, and zero vectors.
- Use Chroma cosine similarity with embedding_function=None.
- Make indexing idempotent.
- Keep status endpoints read-only.
- Validate embeddings before reset/upsert.

## Retrieval Contract
- Return real evidence.
- Include distance information.
- Only pass evidence above the threshold to generation.
- If evidence is weak, skip generation.

## Citation Contract
- Use metadata from real stored records.
- Do not fabricate source/page/chunk_id values from the LLM.
- Results must include citations and warnings.
- Replace labels with valid citations from stored metadata.

## Security
- Do not expose secrets or API keys.

## Testing
- Use unittest.
- Mock API responses where needed.
- Use temporary storage.
- Keep tests offline and free of real keys.

## Coding Style
- Keep the implementation small and simple.
- Use a minimal number of files, classes, and functions.
- Avoid over-engineering.
