# Báo cáo Kiểm tra và Tái sử dụng RBAC cho Buổi 17

## 1. Kiểm tra trường `allowed_roles` trong tập dữ liệu

Dữ liệu nguồn: `../buoi_14/data/processed/chunks_secure.csv` (15 chunks).

### 1.1. Danh sách các vai trò (Roles) trong Corpus
- Danh sách 5 vai trò phân quyền độc lập:
  1. `Admin`
  2. `HR_Manager` (tương ứng vai trò `HR`)
  3. `Risk_Officer` (tương ứng vai trò `Risk_Manager`)
  4. `Employee` (tương ứng vai trò `Staff`)
  5. `Guest`

### 1.2. Phân bố số lượng chunk theo từng Role

| Role | Số chunk được phép truy cập | Tỷ lệ phủ | Ghi chú |
| :--- | :---: | :---: | :--- |
| **Admin** | 15/15 chunks | 100% | Toàn quyền truy cập mọi tài liệu |
| **Risk_Officer** (`Risk_Manager`) | 15/15 chunks | 100% | Được quyền truy cập các văn bản Rủi ro & Chung |
| **Employee** (`Staff`) | 15/15 chunks | 100% | Được quyền truy cập các văn bản Rủi ro & Chung |
| **HR_Manager** (`HR`) | 5/15 chunks | 33.3% | Chỉ truy cập nhóm tài liệu Chung (`General`) |
| **Guest** | 5/15 chunks | 33.3% | Chỉ truy cập nhóm tài liệu Chung (`General`) |

### 1.3. Phân loại tài liệu theo mức độ hạn chế quyền

1. **Nhóm tài liệu mở rộng (`General` - 5 chunks)**:
   - Phân quyền: Cả 5 roles (`Admin`, `HR_Manager`, `Risk_Officer`, `Employee`, `Guest`) đều được xem.
   - Danh sách:
     - `112025__full` | NĐ 73/2016/NĐ-CP (Kinh doanh bảo hiểm)
     - `169221__full` | TT 43/2024/TT-NHNN (Dự trữ ngoại hối nhà nước)
     - `163441__full` | NĐ 46/2023/NĐ-CP (Kinh doanh bảo hiểm)
     - `112924__full` | TT 105/2016/TT-BTC (Đầu tư gián tiếp ra nước ngoài)
     - `166269__full` | Luật 17/2023/QH15 (Hợp tác xã)

2. **Nhóm tài liệu hạn chế quyền (`Risk` - 10 chunks)**:
   - Phân quyền: **Chỉ cho phép `Admin`, `Risk_Officer`, `Employee`** (Chặn hoàn toàn `HR_Manager` và `Guest`).
   - Danh sách:
     - `44209__full` | TT 01/2014/TT-NHNN (Giao nhận, bảo quản tiền mặt)
     - `177271__full` | TT 01/2025/TT-NHNN (Cấp phép quỹ tín dụng nhân dân)
     - `168220__full` | TT 27/2024/TT-NHNN (Quỹ bảo đảm an toàn hệ thống QTDND)
     - `174218__full` | TT 62/2024/TT-NHNN (Tổ chức lại NHTM, TCTD phi ngân hàng)
     - `117310__full` | TT 41/2016/TT-NHNN (Tỷ lệ an toàn vốn ngân hàng)
     - `6e689cd0-6f81-11f1-94d6-fd5d6d5ff793__full` | VBHN 52/VBHN-NHNN (Cấp phép lần đầu NHTM)
     - `185630__full` | TT 63/2025/TT-NHNN (Sửa đổi Thông tư về QTDND)
     - `173695__full` | TT 56/2024/TT-NHNN (Hồ sơ thủ tục cấp phép NHTM)
     - `95652__full` | NĐ 135/2015/NĐ-CP (Đầu tư gián tiếp ra nước ngoài)
     - `25692__full` | Luật 46/2010/QH12 (Ngân hàng Nhà nước Việt Nam)

### 1.4. Tính ổn định khi parse và cơ chế Unknown Role
- **Parse format**: 100% dữ liệu trường `allowed_roles` được lưu trữ dưới dạng JSON List chuỗi (`["Admin", "Risk_Officer", "Employee"]`), parse hoàn toàn chuẩn xác và ổn định qua `json.loads`.
- **Unknown Role**: Được xử lý chặt chẽ theo nguyên tắc **Default Deny** qua hàm `validate_roles` (ném `ValueError: Unknown roles: ...` khi nhận role chưa được đăng ký trong hệ thống).

---

## 2. Kiểm tra `SecureRetriever` của Buổi 16

### 2.1. Đọc và lọc quyền
- Module: `buoi_14/src/secure_retriever.py`
- Lớp `SecureRetriever` nạp toàn bộ danh sách `allowed_roles` và thực hiện **Pre-filtering** tại hàm `self._filter(user_roles)`.
- Các chunk không có quyền bị loại bỏ **trước** khi đưa vào BM25, Dense Embedding, Reranking hay Context của LLM.

### 2.2. Kết quả thực nghiệm với cùng một Query: *"Quy định về an toàn vốn và quản lý tiền mặt"*

| Role Test | Mapped Role | Tổng số chunk | Chunk được phép | Chunk bị loại | Top 1 kết quả truy xuất |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Admin** | `Admin` | 15 | **15** | **0** | TT 41/2016/TT-NHNN (Tỷ lệ an toàn vốn) |
| **HR** | `HR_Manager` | 15 | **5** | **10** | TT 43/2024/TT-NHNN (Dự trữ ngoại hối) |
| **Risk_Manager** | `Risk_Officer` | 15 | **15** | **0** | TT 41/2016/TT-NHNN (Tỷ lệ an toàn vốn) |
| **Staff** | `Employee` | 15 | **15** | **0** | TT 41/2016/TT-NHNN (Tỷ lệ an toàn vốn) |
| **Guest** | `Guest` | 15 | **5** | **10** | TT 43/2024/TT-NHNN (Dự trữ ngoại hối) |

**Nhận xét**: Đối với `HR` và `Guest`, 10 văn bản nghiệp vụ Rủi ro (`Risk`) bị lọc bỏ hoàn toàn, không xuất hiện trong danh sách kết quả, đảm bảo nguyên tắc bảo mật thông tin tuyệt đối.

---

```text
RBAC REUSED: YES
FILTER BEFORE RETRIEVAL: PASS
UNKNOWN ROLE DEFAULT DENY: PASS
```
