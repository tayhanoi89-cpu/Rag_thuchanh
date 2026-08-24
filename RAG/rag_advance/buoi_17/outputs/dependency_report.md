# Báo cáo Kiểm tra Phụ thuộc và Khả năng Tái sử dụng Buổi 16 cho Buổi 17

## 1. Kiểm tra tập dữ liệu nguồn Buổi 16

### 1.1. Thông số chi tiết các tệp dữ liệu
- **Đường dẫn tệp Secure**: `../buoi_14/data/processed/chunks_secure.csv` (tương ứng nguồn Buổi 16).
- **Đường dẫn tệp Normalized**: `../buoi_14/data/processed/chunks_normalized.csv`.

| Tiêu chí | `chunks_normalized.csv` | `chunks_secure.csv` |
| :--- | :--- | :--- |
| **Số dòng dữ liệu** | **15 dòng** (16 dòng tính cả header) | **15 dòng** (16 dòng tính cả header) |
| **Số lượng cột** | **11 cột** | **13 cột** |
| **Danh sách cột** | `chunk_id`, `document_id`, `text`, `source_file`, `title`, `document_type`, `effective_date`, `status`, `citation_code`, `issued_date`, `source_document_id` | `chunk_id`, `document_id`, `text`, `source_file`, `title`, `document_type`, `effective_date`, `status`, `citation_code`, `issued_date`, `source_document_id`, `security_class`, `allowed_roles` |

### 1.2. Chi tiết các trường thông tin kiểm tra
1. **`chunk_id`**: Khóa chính xác định từng chunk (gồm 15 chunks, ví dụ: `44209__full`, `177271__full`, `112025__full`, ..., `6e689cd0-6f81-11f1-94d6-fd5d6d5ff793__full`).
2. **`document_id`**: Mã định danh văn bản gốc (ví dụ: `44209`, `177271`, `112025`, `169221`, ...).
3. **`citation`** (tên cột: `citation_code`): Số hiệu văn bản pháp lý (ví dụ: `01/2014/TT-NHNN`, `01/2025/TT-NHNN`, `73/2016/NĐ-CP`, `17/2023/QH15`, `52/VBHN-NHNN`, ...).
4. **`title`**: Tiêu đề / trích yếu đầy đủ của văn bản quy phạm.
5. **`loai_van_ban`** (tên cột: `document_type`): Phân loại hình thức gồm `Thông tư` (9), `Nghị định` (3), `Luật` (2), `Văn bản hợp nhất` (1).
6. **`co_quan_ban_hanh`**: Không có cột riêng `co_quan_ban_hanh` trong file CSV; thông tin này được thể hiện qua ký hiệu cơ quan ở `citation_code` (`NHNN`, `BTC`, `NĐ-CP`, `QH15`) và nội dung `title`/`text`.
7. **`ngay_ban_hanh`** (tên cột: `issued_date`): Ngày ban hành định dạng `DD/MM/YYYY` (ví dụ: `06/01/2014`, `01/07/2016`, `20/06/2023`, `21/05/2026`, ...).
8. **`allowed_roles`**: Danh sách quyền truy cập dạng JSON array gồm các vai trò được phân quyền:
   - Nhóm `Risk`: `["Admin", "Risk_Officer", "Employee"]` (10 chunks)
   - Nhóm `General`: `["Admin", "HR_Manager", "Risk_Officer", "Employee", "Guest"]` (5 chunks)

---

## 2. So sánh hai file CSV

- **Công thức quan hệ thực tế**:
  $$\text{chunks\_secure.csv} = \text{chunks\_normalized.csv} + \mathbf{security\_class} + \mathbf{allowed\_roles}$$
- **Khác biệt về cột**: `chunks_secure.csv` có thêm 2 cột: `security_class` (phân loại bảo mật: `Risk`, `General`) và `allowed_roles` (danh sách quyền truy cập).
- **Khác biệt về nội dung**: Không có sự sai lệch dữ liệu ở 11 cột dùng chung (`equals == True`). Cả 15 dòng dữ liệu hoàn toàn tương thích và khớp nối 1-1.

---

## 3. Đánh giá Module `SecureRetriever` của Buổi 16

- **File / Module**: [`buoi_14/src/secure_retriever.py`](file:///c:/Users/ngocngothi/Desktop/Rag_thuchanh/RAG/rag_advance/buoi_14/src/secure_retriever.py).
- **Hàm / Class chính**:
  - Class `SecureRetriever(rows=None)`
  - Phương thức: `retrieve(query: str, user_roles: list[str] | tuple[str, ...], method: str = "hybrid", top_k: int = 5, candidate_k: int = 20) -> list[dict[str, Any]]`
  - Hàm module: `retrieve(...)` và `load_secure_corpus(...)`
- **Input role**: `user_roles: list[str] | tuple[str, ...]` (các vai trò hợp lệ: `Admin`, `HR_Manager`, `Risk_Officer`, `Employee`, `Guest`).
- **Output**: `list[dict[str, Any]]` chứa các trường tiêu chuẩn:
  `rank`, `chunk_id`, `document_id`, `text`, `score`, `citation`, `retrieval_method`, `allowed_roles` (kèm `hybrid_score`, `hybrid_rank`, `rerank_score` khi sử dụng phương thức hybrid/rerank).
- **Thời điểm filter `allowed_roles`**: **Pre-filtering (Lọc TRƯỚC khi truy xuất)**:
  - Gọi `self._filter(user_roles)` để loại bỏ triệt để các chunk người dùng không có quyền truy cập trước khi đưa danh sách tài liệu hợp lệ vào `BM25Retriever`, `DenseRetriever`, hoặc `HybridRetriever`.
  - Với truy vấn đồ thị Cypher (`graph`), điều kiện phân quyền được áp dụng trực tiếp trong mệnh đề `WHERE` của Cypher query trên Neo4j.
- **Bảo toàn định danh và trích dẫn**: `chunk_id`, `document_id`, `citation` được chuẩn hóa và bảo toàn nguyên vẹn trong toàn bộ pipeline truy xuất.

---

## 4. Kết luận và Kế hoạch tái sử dụng

```text
SOURCE DATA: PASS
RBAC DATA AVAILABLE: YES
SECURE RETRIEVER REUSABLE: YES
REUSE PLAN:
1. Tái sử dụng trực tiếp cấu hình RBAC và trường `allowed_roles` từ `chunks_secure.csv` làm chuẩn phân quyền cho Buổi 17, không tạo thêm policy mới.
2. Tái sử dụng module `SecureRetriever` từ `buoi_14/src/secure_retriever.py` để đảm bảo nguyên tắc Pre-filtering (tài liệu không có quyền bị loại bỏ trước khi đưa vào context).
3. Tích hợp `SecureRetriever` vào luồng tra cứu có kiểm soát (Use Case 1) và AI Compliance Gap Checker (Use Case 2), bổ sung thêm Audit Trail Logger và Streamlit UI theo yêu cầu Buổi 17.
```
