# Retrieval Evaluation Report

- Questions: 3
- Methods: bm25, dense, hybrid, hybrid_rerank
- Gold policy: expected IDs were selected only where the source title/code/content directly verified the target chunk.

## Aggregate Metrics

| Method | Hit@1 | Hit@3 | Hit@5 | MRR |
| --- | ---: | ---: | ---: | ---: |
| bm25 | 0.333 | 1.000 | 1.000 | 0.611 |
| dense | 0.000 | 1.000 | 1.000 | 0.389 |
| hybrid | 0.333 | 1.000 | 1.000 | 0.556 |
| hybrid_rerank | 1.000 | 1.000 | 1.000 | 1.000 |

## Observations

- BM25 is expected to be strongest for exact document codes and identifiers.
- Dense retrieval is evaluated for semantic similarity, but a small three-question set cannot establish general superiority.
- Hybrid uses both rank lists through RRF; it does not add raw BM25 and cosine scores.
- Reranker mode observed: `NEURAL_CROSS_ENCODER`.
- Ranking changes are visible in `retrieval_examples.md`; metric changes should be interpreted only on this small verified set.

## Failure Cases

- No Hit@5 failures in this evaluation set.

## Limitations

- The corpus contains 15 full-document records, not article-level chunks.
- The evaluation has three questions and one verified target per question.
- No claim about production retrieval quality should be made from these metrics alone.
