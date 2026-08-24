# Báo cáo Đánh giá Vai trò của Knowledge Graph trong Compliance Gap Analysis

## 1. Mục tiêu Đánh giá
Kiểm tra cấu trúc và các loại quan hệ (Relationship Types) thực tế trong Knowledge Graph (Neo4j) để xác định xem đồ thị tri thức có hỗ trợ được quy trình **AI Compliance Gap Checker** hay không.

### Nguyên tắc phân định vai trò:
- **Hybrid Retrieval (Dense + BM25)**: Tìm kiếm nội dung ngữ nghĩa và từ khóa liên quan giữa yêu cầu pháp luật và tài liệu đối chiếu.
- **Knowledge Graph (KG)**: Mở rộng ứng viên (Candidate Expansion) dựa trên các quan hệ đã được cấu trúc hóa sẵn trong cơ sở dữ liệu.
- **Gap Checker**: So sánh, đối chiếu bằng chứng (Evidence package) để phân loại mức độ đáp ứng (DAP_UNG, THIEU, CHENH_LECH, CHUA_DU_BANG_CHUNG).

---

## 2. Kiểm tra Cấu trúc Thực tế trong Knowledge Graph (Neo4j)

Căn cứ vào mã nguồn nạp đồ thị `buoi_14/scripts/load_secure_kg.py` và lược đồ Neo4j hiện có:
- **Node Labels**: `(:VanBan)`, `(:DieuKhoan)`
- **Relationship Types tồn tại**: Duy nhất quan hệ `[:CONTAINS]` giữa một Văn bản và các Điều khoản/Chunk con của chính văn bản đó:
  ```cypher
  (document:VanBan)-[:CONTAINS]->(clause:DieuKhoan)
  ```

### Phân tích chi tiết các loại quan hệ:
1. **Quan hệ nối văn bản / điều khoản xuyên tài liệu (`[:REFERENCES]`, `[:SUPERSEDES]`, `[:IMPLEMENTS]`)**:
   - **Thực tế**: **KHÔNG TỒN TẠI** trong cơ sở dữ liệu đồ thị hiện tại.
   - **Tác động**: Không có cạnh nối tri thức nào thể hiện mối liên hệ giữa một Thông tư NHNN với một Quy định nội bộ ngân hàng hay giữa các văn bản khác nhau.
2. **Quan hệ cấu trúc phân cấp (`[:CONTAINS]`, `[:NEXT]`)**:
   - **Thực tế**: Chỉ có `[:CONTAINS]` liên kết cha-con nội bộ trong cùng 1 văn bản.
   - **Tác động**: Quan hệ này chỉ có ý nghĩa khi cần lấy ngữ cảnh toàn bài của chính văn bản đó, không giúp ích gì cho việc tìm kiếm bằng chứng đối chiếu giữa 2 hệ thống văn bản độc lập (External vs Internal).
3. **Quan hệ không liên quan**:
   - Các thuộc tính phân quyền RBAC (`allowed_roles`) gắn trên node dùng để lọc quyền, không phải quan hệ ngữ nghĩa phục vụ gap analysis.

---

## 3. Quyết định Tích hợp & Kiến trúc Đề xuất

1. **Không bịa đặt cạnh (No Artificial Edges)**: Tuân thủ quy tắc trung thực khoa học, hệ thống không tự tạo ra các quan hệ giả định giữa các văn bản khi dữ liệu thực tế không có.
2. **Quyết định sử dụng**:
   - **KHÔNG sử dụng Knowledge Graph cho Gap Matching** trong kịch bản hiện tại.
   - Tiếp tục duy trì cơ chế tìm kiếm **Hybrid Retrieval (Dense + Lexical) + Reranking** để thu thập bằng chứng.
   - Ghi nhận trạng thái: `GRAPH NOT USED FOR GAP MATCHING`.

---

## 4. Kết luận Đánh giá

| Tiêu chí | Hiện trạng | Kết luận |
| :--- | :--- | :---: |
| **Quan hệ liên kết văn bản** | Không có quan hệ nối liên văn bản | **FAIL (Không đủ)** |
| **Quan hệ cấu trúc** | Chỉ có `[:CONTAINS]` nội bộ văn bản | **Không hữu ích cho Gap** |
| **Candidate Expansion qua KG** | Không thể thực hiện vì thiếu edge thực | **DISABLED** |
| **Phương thức truy xuất Gap** | Giữ nguyên Hybrid Search + Reranking | **PASS** |

---

```text
GRAPH USED: NO
REASON: GRAPH NOT USED FOR GAP MATCHING (Chỉ có quan hệ CONTAINS nội bộ tài liệu, không có quan hệ liên văn bản giữa External Requirement và Internal Policy)
```
