# Specification Buổi 09

## 1. Mục tiêu

Buổi 09 mở rộng pipeline Buổi 08 bằng hai tầng bổ sung:

1. Multi-query retrieval: một câu hỏi gốc tạo Q0 plus nhiều query variants.
2. Parent–child retrieval: child hits được mở rộng về parent context để cung cấp ngữ cảnh pháp lý đầy đủ hơn.

## 2. Pipeline mong đợi

Q0 + variants → per-query hybrid retrieval → cross-query RRF → child-to-parent mapping → parent aggregation → parent rerank → generation.

## 3. Các mode bắt buộc

- single_flat
- multi_flat
- single_parent
- multi_parent

## 4. Schema và validation

- QueryVariant: `query_id`, `text`, `origin`, `focus`.
- Hierarchy registry: `child_id`, `parent_id`, `source`, `page_start`, `page_end`, `structural_path`, `resolution_method`, `ambiguous`, `warnings`.
- ParentDocument: `parent_id`, `source`, `page_start`, `page_end`, `article_key`, `window_index`, `child_ids`, `text`, `char_count`, `warnings`.
- MultiQueryChildHit và ParentCandidate sẽ được định nghĩa ở các bước sau.

## 5. Quy tắc hierarchy

- Hierarchy phải được resolve từ metadata hoặc heading, không tự suy đoán.
- Nếu không chắc chắn, phải ghi `ambiguous=true` và warning.
- Parent được ghép từ text gốc, không dùng LLM tóm tắt.

## 6. RRF và aggregation

- Inner RRF dùng BM25 + semantic rank cho từng query.
- Cross-query RRF dùng rank của từng query, không cộng raw score.
- Parent aggregation dùng parent-level RRF trên các child hits đã map.

## 7. Status và failure contract

- Status phải rõ ràng cho `hierarchy_not_ready`, `collection_not_ready`, `query_generation_unavailable`, `multi_query_partial`, `reranker_unavailable`, `insufficient_evidence` và `generation_error`.
- Không silent fallback khi model hoặc hierarchy không sẵn sàng.

## 8. Testability

- Tất cả chức năng chính phải hỗ trợ dependency injection cho unit test.
- Offline test không gọi Gemini, không tải model và không sửa storage Buổi 05–08.

## 9. Acceptance criteria cho bước này

- Project Buổi 09 độc lập với runtime Buổi 08.
- Baseline được snapshot đúng.
- Import compile được mà không tạo collection hoặc store.
- Specification mô tả đúng hai tầng fusion và parent expansion.
