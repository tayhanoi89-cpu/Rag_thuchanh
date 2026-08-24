# Buổi 09 — Multi-query và Parent–Child Retrieval

Buổi 09 triển khai một pipeline retrieval-only với hai tầng chính:

1. Multi-query fan-out: sinh Q0 + query variants.
2. Parent–child retrieval: map child hits vào parent documents để mở rộng ngữ cảnh.

## Mục tiêu bước này

- Triển khai hierarchy builder và store cho parent–child retrieval.
- Thêm multi-query query set generation và cross-query fusion.
- Thêm parent aggregation, reranking và offline evaluator.
- Cung cấp Streamlit UI helper support và acceptance-ready README.

## Files chính

- `hierarchical_rag.py`: pipeline Buổi 09, hierarchy builder, query generation, multi-query fusion, parent retrieval, rerank và compare modes.
- `evaluate.py`: offline evaluator với report JSON tạo được từ `eval/questions.json`.
- `app.py`: Streamlit UI shell hiển thị query fan-out, parent candidates và evaluation report.
- `eval/questions.json`: bộ dữ liệu evaluation placeholder cho Buổi 09.
- `reports/latest_report.json`: evaluation report target.
- `tests/`: unit tests cho hierarchy, query pipeline và UI helper.

## Runtime và cấu hình

- Sử dụng `hierarchical` chunks từ `rag_foundation/buoi_05/output/chunks` nếu không truyền `--input`.
- Runtime config được load từ `.env` và `.env.example`.
- Không cần model tải khi chạy offline tests hoặc evaluator mặc định.

## Chạy toàn bộ tests

```bash
python -m unittest discover -s rag_advance/buoi_09/tests -v
```

## Build hierarchy store

```bash
python -m rag_advance.buoi_09.hierarchical_rag build-hierarchy --input tests/fixtures/hierarchical_sample.json --output-dir storage/hierarchy
```

## Chạy evaluator offline

```bash
python -m rag_advance.buoi_09.evaluate --questions eval/questions.json --output reports/latest_report.json --input tests/fixtures/hierarchical_sample.json --store-dir storage/hierarchy --compare
```

## Quy trình Buổi 09

1. `build_hierarchy()` đọc hierarchical chunks và tạo `children.json` + `parents.json`.
2. `generate_query_set()` tạo 1 query gốc và các variant, hỗ trợ dependency injection để test offline.
3. `multi_child_retrieval()` lấy child hits cho mỗi query và hợp nhất bằng cross-query RRF.
4. `parent_retrieval()` map child hits vào parent documents, tổng hợp score, và chọn parent candidates theo budget.
5. `rerank_parent_candidates()` chạy reranker stub/model để sắp xếp lại parent candidates.
6. `evaluate.py` chạy retrieval-only với câu hỏi evaluation và ghi report JSON.

## Acceptance note

- Buổi 09 không sửa storage Buổi 05–08.
- All Buổi 09 modules compile and support offline unit tests.
- `evaluate.py` chạy offline without Gemini or live model calls by default.
