# BÁO CÁO CATALOGING VÀ CHUẨN BỊ DỮ LIỆU BUỔI 18
## Hệ thống AI Compliance Checker (UC3) & AI Audit Checklist Generator (UC4)

**Ngày thực hiện:** 2026-08-24  
**Nguồn dữ liệu:** `data/agribank_internal_policies.csv` & `data/chunks_combined_secure.csv`

---
### 1. Tổng quan dữ liệu & Phân loại văn bản

- **Tổng số chunks trong hệ thống hợp nhất (`chunks_combined_secure.csv`):** `811` chunks
  - **Văn bản Pháp luật / Nhà nước:** `787` chunks
    - Nghị định: `300` chunks
    - Thông tư: `257` chunks
    - Luật: `184` chunks
    - Văn bản hợp nhất: `46` chunks
  - **Văn bản Quy định nội bộ Agribank:** `24` chunks (tương ứng với 10 quy định/quy chế trọng yếu)

---
### 2. Danh mục chi tiết các Văn bản Quy định Nội bộ Agribank

| STT | Số Ký Hiệu | Tiêu đề văn bản | Loại văn bản | Cơ quan ban hành | Ngày ban hành | Domain / Nghiệp vụ | Số Chunks |
|---|---|---|---|---|---|---|---|
| 1 | `100/QĐ-NHNO-AT` | Quy định nội bộ số 100/QĐ-NHNO-AT về Giao nhận, bảo quản, vận chuyển tiền mặt và tài sản quý Agribank | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 15/03/2024 | **An toàn kho quỹ & Vận chuyển tiền mặt** | 4 |
| 2 | `180/QĐ-NHNO-BH` | Quy định nội bộ số 180/QĐ-NHNO-BH về Mua bảo hiểm rủi ro nghiệp vụ và tài sản Agribank | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 14/02/2024 | **CAR & Quản lý rủi ro** | 2 |
| 3 | `250/QĐ-NHNO-QLRR` | Quy định nội bộ số 250/QĐ-NHNO-QLRR về Quản lý tỷ lệ an toàn vốn và định mức rủi ro Agribank | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 20/06/2024 | **CAR & Quản lý rủi ro** | 3 |
| 4 | `315/QC-NHNO-TD` | Quy chế tín dụng nội bộ số 315/QC-NHNO-TD về Phán quyết và Phân cấp ủy quyền cho vay tại Agribank | Quy chế nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 10/01/2024 | **Tín dụng & Thẩm quyền phê duyệt cho vay** | 3 |
| 5 | `390/QĐ-NHNO-XLN` | Quy định nội bộ số 390/QĐ-NHNO-XLN về Phân loại nợ và Xử lý nợ xấu tại Agribank | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 22/07/2024 | **Phân loại nợ & Xử lý nợ xấu** | 2 |
| 6 | `410/QĐ-NHNO-TTNH` | Quy định nội bộ số 410/QĐ-NHNO-TTNH về Quản lý trạng thái ngoại tệ và giao dịch ngoại hối Agribank | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 05/09/2024 | **Ngoại hối & Quản lý trạng thái ngoại tệ** | 2 |
| 7 | `520/QC-NHNO-MANGLUOI` | Quy chế số 520/QC-NHNO-MANGLUOI về Mở rộng mạng lưới chi nhánh và phòng giao dịch Agribank | Quy chế nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 18/11/2024 | **Mạng lưới & Phát triển chi nhánh / PGD** | 2 |
| 8 | `600/QC-NHNO-CNTT` | Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT về An toàn thông tin và Quản trị dữ liệu AI Agribank | Quy chế nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 01/03/2025 | **Bảo mật CNTT & Quản trị AI** | 2 |
| 9 | `720/QC-NHNO-TC` | Quy chế tài chính số 720/QC-NHNO-TC về Chế độ chi tiêu và mua sắm tài sản nội bộ Agribank | Quy chế nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 05/12/2024 | **Tài chính & Mua sắm nội bộ** | 2 |
| 10 | `88/QĐ-NHNO-NS` | Quy định nội bộ số 88/QĐ-NHNO-NS về Quy hoạch, bổ nhiệm và quản lý nhân sự Agribank | Quy định nội bộ | Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam (Agribank) | 10/01/2025 | **Quản trị nhân sự & Đào tạo** | 2 |

---
### 3. Phân bổ Domains / Nghiệp vụ trọng yếu phục vụ UC3 & UC4

| STT | Domain / Nghiệp vụ | Số điều khoản (Chunks) | Mã văn bản nội bộ | Quyền truy cập (Allowed Roles) |
|---|---|---|---|---|
| 1 | **CAR & Quản lý rủi ro** | 5 | `250/QĐ-NHNO-QLRR`, `180/QĐ-NHNO-BH` | `Admin`, `Risk_Manager`, `Staff` |
| 2 | **An toàn kho quỹ & Vận chuyển tiền mặt** | 4 | `100/QĐ-NHNO-AT` | `Admin`, `Risk_Manager`, `Staff` |
| 3 | **Tín dụng & Thẩm quyền phê duyệt cho vay** | 3 | `315/QC-NHNO-TD` | `Admin`, `Risk_Manager`, `Staff` |
| 4 | **Ngoại hối & Quản lý trạng thái ngoại tệ** | 2 | `410/QĐ-NHNO-TTNH` | `Admin`, `Risk_Manager` |
| 5 | **Mạng lưới & Phát triển chi nhánh / PGD** | 2 | `520/QC-NHNO-MANGLUOI` | `Admin`, `Risk_Manager`, `Staff` |
| 6 | **Bảo mật CNTT & Quản trị AI** | 2 | `600/QC-NHNO-CNTT` | `Admin`, `Risk_Manager` |
| 7 | **Quản trị nhân sự & Đào tạo** | 2 | `88/QĐ-NHNO-NS` | `Admin`, `HR` |
| 8 | **Tài chính & Mua sắm nội bộ** | 2 | `720/QC-NHNO-TC` | `Admin`, `Risk_Manager`, `Staff` |
| 9 | **Phân loại nợ & Xử lý nợ xấu** | 2 | `390/QĐ-NHNO-XLN` | `Admin`, `Risk_Manager` |

---
### 4. Kiểm tra tính đầy đủ của 14 trường Metadata

Đánh giá sự hiện diện và tính hợp lệ của 14 cột metadata trên cả 2 tệp dữ liệu:

| STT | Tên trường Metadata | Trạng thái ở `agribank_internal_policies` | Trạng thái ở `chunks_combined_secure` | Ý nghĩa nghiệp vụ |
|---|---|---|---|---|
| 1 | `chunk_id` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Mã định danh duy nhất của từng đoạn văn bản |
| 2 | `document_id` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Mã định danh của toàn bộ tài liệu gốc |
| 3 | `text` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Nội dung trích đoạn quy định / điều khoản |
| 4 | `source_file` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Tên file gốc chứa tài liệu |
| 5 | `title` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Tên / Trích yếu văn bản |
| 6 | `so_ky_hieu` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Số hiệu văn bản pháp lý hoặc nội bộ |
| 7 | `loai_van_ban` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Loại hình văn bản (Thông tư, Nghị định, Quy định nội bộ...) |
| 8 | `co_quan_ban_hanh` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Cơ quan hoặc đơn vị ban hành |
| 9 | `ngay_ban_hanh` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Ngày ban hành văn bản |
| 10 | `chapter` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Chương trong văn bản (nếu có) |
| 11 | `section` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Mục trong văn bản (nếu có) |
| 12 | `article` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Tên điều khoản cụ thể (phục vụ đối chiếu chính xác) |
| 13 | `citation` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Trích dẫn chuẩn để AI xuất citation / link nguồn |
| 14 | `allowed_roles` | ✅ Đầy đủ (100%) | ✅ Đầy đủ (100%) | Danh sách Role được phép xem (RBAC Security) |

> **Đặc biệt kiểm tra 3 trường bắt buộc:**
- `article`: 100% chunks nội bộ có tên điều rõ ràng (ví dụ: `Điều 12. Xe bọc thép...`, `Điều 8. Hạn mức duyệt vay...`).
- `citation`: 100% chunks có cấu trúc trích dẫn đầy đủ (Văn bản - Điều - Khoản).
- `allowed_roles`: Đã gán nhãn JSON list RBAC (`Admin`, `Risk_Manager`, `Staff`, `HR`) chính xác.

---
### 5. Kết luận & Sẵn sàng cho UC3 & UC4

```plaintext
DATA CATALOGING: PASS
DOMAINS DETECTED: 9
READY FOR UC3 & UC4: YES
```