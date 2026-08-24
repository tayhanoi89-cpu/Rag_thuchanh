# Báo cáo Kiểm thử Secure Retrieval Adapter Buổi 17

## 1. Mục tiêu kiểm thử
Xác thực việc tái sử dụng `SecureRetriever` từ Buổi 16 thông qua `SecureRetrievalAdapter` tại Buổi 17, đảm bảo:
1. **Quyền hợp lệ**: Role được phép truy cập (`Staff` / `Employee`) nhận được đúng tài liệu liên quan.
2. **Loại trừ truy cập trái phép**: Role không có quyền (`Guest` / `HR`) bị loại trừ tuyệt đối toàn bộ 10 chunk hạn chế nghiệp vụ rủi ro.
3. **Không rò rỉ ngữ cảnh (Zero Leakage Context)**: Ngữ cảnh (Context) sinh ra cho LLM hoàn toàn không chứa bất kỳ chunk hoặc nội dung tài liệu trái phép nào.
4. **Bảo toàn siêu dữ liệu**: Chuẩn hóa và giữ nguyên vẹn 100% các trường định danh (`rank`, `chunk_id`, `document_id`, `title`, `article`, `citation`, `allowed_roles`, `access_decision`, `retrieval_method`).

---

## 2. Kết quả 4 kịch bản kiểm thử chi tiết

### Kịch bản 1: Role được phép nhận được chunk (`Staff` / `Employee`)
- **Truy vấn**: `"vận chuyển và bảo quản tiền mặt ngân hàng"`
- **Target chunk**: `44209__full` (Thông tư 01/2014/TT-NHNN - Quản lý tiền mặt, nhóm `Risk`)
- **Kết quả trả về**:
  - Danh sách chunk IDs: `['44209__full', '117310__full', '25692__full', '168220__full', '174218__full']`
  - Target chunk `44209__full` xuất hiện ở vị trí Top 1: **Có**
- **Trạng thái**: **PASS**

### Kịch bản 2: Role không được phép KHÔNG nhận được chunk (`Guest`)
- **Truy vấn**: `"vận chuyển và bảo quản tiền mặt ngân hàng"`
- **Kết quả trả về**:
  - Danh sách chunk IDs: `['169221__full', '112924__full', '163441__full', '112025__full', '166269__full']`
  - Target chunk `44209__full` xuất hiện trong kết quả: **Không (Được lọc an toàn)**
  - Số lượng chunk hạn chế (`Risk`) bị rò rỉ: **0**
  - 100% chunk trả về đều có quyền `'Guest'`: **ĐÚNG**
- **Trạng thái**: **PASS**

### Kịch bản 3: Ngữ cảnh LLM không chứa thông tin trái phép (Zero Leakage Context)
- **Kiểm tra Context sinh cho Guest**:
  - Độ dài Context: 705,185 ký tự.
  - Số chunk thuộc danh sách 10 tài liệu hạn chế xuất hiện trong context: **0**.
  - Không có bất kỳ chunk ID hoặc nội dung tài liệu hạn chế nào lọt vào Context: **ĐÚNG**.
- **Trạng thái**: **PASS**

### Kịch bản 4: Tính toàn vẹn siêu dữ liệu trích dẫn (Citation & IDs Preservation)
- Kiểm tra các trường chuẩn hóa trên toàn bộ kết quả của Adapter:
  - `rank`: int
  - `chunk_id`: str (Đầy đủ)
  - `document_id`: str (Đầy đủ)
  - `title`: str (Đầy đủ trích yếu)
  - `article`: str (Loại văn bản)
  - `citation`: str (Mã hiệu văn bản chuẩn)
  - `allowed_roles`: list[str] (Danh sách role được phép)
  - `access_decision`: `"ALLOW"`
  - `retrieval_method`: `"hybrid"`
  - `score`: float
  - `text`: str
- **Trạng thái**: **PASS**

---

## 3. Mẫu kết quả chuẩn hóa từ Adapter

```json
{
  "rank": 1,
  "chunk_id": "44209__full",
  "document_id": "44209",
  "title": "Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá",
  "article": "Thông tư",
  "citation": "01/2014/TT-NHNN",
  "citation_code": "01/2014/TT-NHNN",
  "allowed_roles": [
    "Admin",
    "Risk_Officer",
    "Employee"
  ],
  "access_decision": "ALLOW",
  "retrieval_method": "hybrid",
  "score": 0.03252247488101534,
  "text": "NGÂN HÀNG NHÀ NƯỚC\nVIỆT NAM\n-------\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n---------------\nSố: 01/2014/TT-NHNN\nHà Nội, ngày 06 tháng 01 năm 2014\nTHÔNG TƯ\nQuy định về giao nhận,...",
  "hybrid_score": 0.03252247488101534
}
```

---

```text
SECURE RETRIEVAL REUSE: PASS
NO UNAUTHORIZED CONTEXT: PASS
CITATION PRESERVED: PASS
```
