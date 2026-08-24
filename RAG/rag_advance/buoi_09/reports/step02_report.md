# Buổi 09 — Step 02 report

## Files created
- .env.example
- .gitignore
- requirements.txt
- rag.py
- advanced_rag.py
- hierarchical_rag.py
- evaluate.py
- app.py
- README.md
- SPEC_buoi_09.md
- eval/questions.json
- reports/.gitkeep
- storage/chroma/.gitkeep
- storage/hierarchy/.gitkeep
- storage/huggingface/.gitkeep
- tests/__init__.py
- tests/fixtures/hierarchical_sample.json

## Baseline snapshot hashes
- source_rag: d2285f74b3cd7caf928a6d1813910313d5a7819d4c800cbc5cb6940fbea74758
- source_advanced: fb0d78c3a9e0d5a6ef14a3c4921b50efd5bc093e97a80119d722023911c87d54
- copy_rag: 5694dde03c0319efd08bad1122b6a5df8a549e49ca943af450ecf7423083d369
- copy_advanced: df3cad6d402b55391a292dca156b6be1683e90874d5bb8dbdd3fce75bdeb7ca8

## Validation
- Compile: passed via `python -m compileall rag_advance/buoi_09`
- Import check: passed (`import-check-ok`)
- Scope: only new Buổi 09 files were created; no Buổi 05–08 runtime files were modified by this step.

## Limitations for this step
- No hierarchy builder implemented yet.
- No multi-query retrieval implemented yet.
- No UI implemented yet.
- No semantic store or Chroma collection is built during this step.
