# BÁO CÁO ĐÁNH GIÁ HIỆU NĂNG HỆ THỐNG RAG (RAGAS EVALUATION REPORT)

- **Tổng số câu hỏi đánh giá (Golden Dataset)**: 20 câu hỏi
- **Mô hình Pipeline (Generator)**: `Qwen/Qwen3.5-9B:deepinfra`
- **Mô hình Trọng tài (Judger Evaluator)**: `openai/gpt-oss-20b:deepinfra`
- **Hạ tầng API**: Hugging Face Router API (`https://router.huggingface.co/v1`)
- **Phương pháp tìm kiếm**: `Hybrid (BM25 + Dense Search)` kết hợp `Cross-Encoder Reranker`

---

## 1. Bảng tổng hợp điểm số trung bình 4 Metrics Ragas

| Chỉ số Ragas | Điểm trung bình | Mức chuẩn khuyến nghị | Đánh giá trạng thái |
| :--- | :---: | :---: | :--- |
| **Context Precision** (Độ chuẩn xác ngữ cảnh) | **0.875** | ≥ 0.70 | Đạt chuẩn |
| **Context Recall** (Độ phủ ngữ cảnh) | **0.993** | ≥ 0.70 | Đạt chuẩn |
| **Faithfulness** (Độ trung thực / Không ảo tưởng) | **0.993** | ≥ 0.80 | Đạt chuẩn |
| **Answer Relevancy** (Độ phù hợp của câu trả lời) | **0.844** | ≥ 0.80 | Đạt chuẩn |

---

## 2. Phân tích chi tiết các trường hợp điểm số thấp (< 0.70)

| Question ID | Usecase | Độ khó | Câu hỏi | Vấn đề ghi nhận |
| :--- | :--- | :--- | :--- | :--- |
| `Q01` | Common | easy | Thông tư số 01/2014/TT-NHNN quy định về những nội dung gì trong h... | Context Precision (0.50), Answer Relevancy (0.78) |
| `Q04` | HR | medium | Theo Thông tư số 01/2025/TT-NHNN, tiêu chuẩn đối với Chủ tịch Hội... | Context Precision (0.50) |
| `Q05` | HR | hard | Những trường hợp nào không được giữ chức vụ thành viên Ban kiểm s... | Context Precision (0.50) |
| `Q06` | Risk | easy | Mức vốn điều lệ tối thiểu khi thành lập và cấp giấy phép lần đầu ... | Context Precision (0.50) |
| `Q14` | HR | hard | Điều kiện để một cá nhân được bầu làm Giám đốc (Tổng giám đốc) đi... | Context Precision (0.50) |
| `Q20` | Common | hard | Điều kiện để một tổ chức kinh doanh chứng khoán được cấp Giấy chứ... | Answer Relevancy (0.78) |

> [!NOTE]
> Các câu hỏi thuộc mức độ `hard` và nhóm điều kiện liên thông nhiều quy định thường yêu cầu truy xuất sâu hơn và xếp hạng rerank tinh chỉnh hơn.

---

## 3. Đề xuất giải pháp kỹ thuật tối ưu hóa hệ thống RAG

Dựa trên kết quả đo đạc từ Ragas, các giải pháp kỹ thuật được đề xuất áp dụng theo từng chỉ số:

### 3.1. Tối ưu Context Recall (Độ phủ ngữ cảnh)
- **Tăng số lượng văn bản truy xuất (`top_k`)**: Mở rộng `top_k` từ 5 lên 8 hoặc 10 để bao phủ các điều khoản liên quan.
- **Bổ sung Query Expansion**: Sử dụng LLM để sinh các câu truy vấn mở rộng có chứa từ đồng nghĩa và cụm từ viết tắt chuyên ngành.
- **Mở rộng Graph Retrieval (Multi-hop)**: Sử dụng các mối quan hệ đồ thị Neo4j (`[:CONTAINS]`, `[:NEXT]`, `[:REFERS_TO]`) để thu thập các điều khoản liên quan kế cận.

### 3.2. Tối ưu Context Precision (Độ chuẩn xác ngữ cảnh)
- **Tinh chỉnh tham số RRF (Reciprocal Rank Fusion)**: Điều chỉnh tham số làm trơn $k=60$ và cân đối trọng số giữa BM25 và Dense Search.
- **Nâng cấp Cross-Encoder Reranker**: Áp dụng mô hình reranker đa ngôn ngữ mạnh mẽ như `BAAI/bge-reranker-v2-m3` để lọc nhiễu trước khi nạp vào context.

### 3.3. Tối ưu Faithfulness (Độ trung thực / Chống ảo tưởng)
- **Thắt chặt System Prompt**: Yêu cầu LLM chỉ trả lời dựa trên context được cung cấp; từ chối trả lời nếu thiếu cơ sở dữ liệu.
- **Rút gọn độ dài đoạn ngữ cảnh**: Phân đoạn chunk nhỏ gọn (256-512 tokens) giúp Generator không bị nhiễu thông tin (Lost in the Middle).

### 3.4. Tối ưu Answer Relevancy (Độ phù hợp của câu trả lời)
- **Few-shot Prompting**: Cung cấp các ví dụ mẫu hỏi - đáp chuẩn súc tích trong prompt của Generator.
- **Tối ưu cấu trúc câu trả lời**: Hướng dẫn mô hình đưa ra câu trả lời trực diện ngay từ câu đầu tiên trước khi trích dẫn cơ sở pháp lý.

---

## 4. Tổng kết
- Hệ thống đã hoàn thành đánh giá tự động trên toàn bộ 20 câu hỏi của Golden Dataset.
- Báo cáo chi tiết đã được lưu trữ tại: `C:\Users\ngocngothi\Desktop\Rag_thuchanh\RAG\rag_advance\buoi_14\outputs\ragas_evaluation_report.md`
- Bảng kết quả từng câu hỏi đã được lưu tại: `C:\Users\ngocngothi\Desktop\Rag_thuchanh\RAG\rag_advance\buoi_14\data\eval\evaluation_results.csv`