# SPEC Buổi 08 - Advanced RAG

## 1. Workspace và security
- Chỉ ghi trong rag_advance/buoi_08/.
- Không sửa Buổi 05-07.
- Không in secret, không đẩy .env hoặc storage thật.

## 2. Quan hệ với Buổi 05 và Buổi 07
- Buổi 05 cung cấp chunks JSON thực.
- Buổi 07 là semantic baseline và source reference.
- Buổi 08 sẽ xây thêm BM25, RRF và reranker trên top của baseline.

## 3. Data contract
- Dữ liệu đầu vào là list chunk validate từ Buổi 07.
- Mỗi chunk cần có chunk_id, strategy, source, page_start, page_end, text.

## 4. BM25 tokenizer/retrieval contract
- Dùng tokenize_vi_legal cho corpus và query.
- Dùng rank_bm25.BM25Okapi ở memory.
- Output phải có bm25_rank và bm25_score.

## 5. Semantic candidate contract
- Tái sử dụng loader/config/collection naming từ baseline.
- Output phải có semantic_rank và semantic_distance.

## 6. RRF fusion contract
- Hợp nhất các ranking bằng Reciprocal Rank Fusion, không cộng raw score.
- Output phải có rrf_score và fused_rank.

## 7. Cross-encoder reranker contract
- Lazy-load reranker khi mode hybrid_rerank được yêu cầu.
- Không tải model khi import/status/test.

## 8. Final evidence và citation contract
- Dùng evidence metadata thật cho citation.
- Không bịa label.

## 9. Pipeline trace contract
- Trace phải ghi latency và counts cho từng tầng.

## 10. Evaluation metrics contract
- Đánh giá bằng Recall@K, MRR@K và nDCG@K.
- Gold labels ban đầu có needs_human_review=true.

## 11. Offline testing contract
- Unit tests không gọi Gemini, không tải model và không dùng storage thật.

## 12. UI comparison contract
- Giao diện cho thấy so sánh BM25 / semantic / hybrid / hybrid_rerank.
