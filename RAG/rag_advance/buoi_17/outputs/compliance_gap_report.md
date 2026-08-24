# Báo cáo Đánh giá AI Compliance Gap Checker

## 1. Mục tiêu và Nguyên tắc Vận hành
AI Compliance Gap Checker được thiết kế để tự động hóa quy trình rà soát tính tuân thủ giữa **Quy định pháp luật của cơ quan quản lý (NHNN/Chính phủ/Quốc hội)** và **Quy định/Quy chế nội bộ của ngân hàng**.

### Các nguyên tắc cốt lõi:
1. **Không suy diễn/bịa đặt (Anti-Hallucination)**: Tuyệt đối không kết luận `DAP_UNG` (Đáp ứng) nếu không tìm thấy văn bản quy định nội bộ chứng minh.
2. **Không quy chụp (Anti-False-Positive)**: Không gán `THIEU` (Thiếu) chỉ vì công cụ tìm kiếm chưa tìm ra, mà phải phân loại chính xác là `CHUA_DU_BANG_CHUNG` khi thiếu dữ liệu đối chiếu.
3. **Cơ chế Human-in-the-loop**: Mọi kết quả phân loại gap đều gắn cờ `review_status = NEEDS_HUMAN_REVIEW` để chuyên viên pháp chế/tuân thủ thẩm định cuối cùng.

---

## 2. Đánh giá Hiện trạng Dữ liệu (Data Gap Identification)
Căn cứ kết quả phân loại dữ liệu từ [gap_input_catalog.md](gap_input_catalog.md):
- **Tập văn bản bên ngoài (EXTERNAL_REQUIREMENT)**: 15/15 văn bản (Thông tư, Nghị định, Luật).
- **Tập quy định nội bộ (INTERNAL_POLICY)**: 0/15 văn bản.

Do nguồn dữ liệu hiện tại chỉ có một phía (Yêu cầu pháp lý bên ngoài) mà **chưa có tài liệu quy định nội bộ của ngân hàng thương mại**, hệ thống tuân thủ nghiêm ngặt chỉ thị của bài học:
> *Không tự tạo văn bản giả mạo và không sinh kết luận tuân thủ giả.*

---

## 3. Kết quả Chạy Thử nghiệm 3 Yêu cầu Pháp lý NHNN

### Yêu cầu 1: Quản lý Tiền mặt & Kho quỹ (01/2014/TT-NHNN)
- **Mã Gap**: `GAP_D77A3D21` | **Request ID**: `req_df3c5f95b4d9`
- **Yêu cầu bên ngoài**: Quy định tổ chức tín dụng phải thực hiện giao nhận, kiểm đếm bó/túi tiền nguyên niêm phong kẹp chì và bảo quản nghiêm ngặt trong kho tiền.
- **Bằng chứng nội bộ**: Không có tài liệu quy định nội bộ (INTERNAL_POLICY) trong dữ liệu nguồn.
- **Kết quả phân loại**: `CHUA_DU_BANG_CHUNG`
- **Lý do**: Dữ liệu corpus hiện tại chỉ bao gồm 100% văn bản quy phạm pháp luật bên ngoài (Thông tư NHNN, Nghị định, Luật), chưa có tài liệu quy định nội bộ của tổ chức để tiến hành đối chiếu khoảng cách tuân thủ (Compliance Gap).
- **Confidence**: `0.0` | **Trạng thái**: `NEEDS_HUMAN_REVIEW`

---

### Yêu cầu 2: Tỷ lệ An toàn Vốn CAR (41/2016/TT-NHNN)
- **Mã Gap**: `GAP_DC99718F` | **Request ID**: `req_36a3e8bc07c6`
- **Yêu cầu bên ngoài**: Quy định tỷ lệ an toàn vốn tối thiểu (CAR) của ngân hàng thương mại phải duy trì tối thiểu 8% theo phương pháp tiêu chuẩn.
- **Bằng chứng nội bộ**: Không có tài liệu quy định nội bộ (INTERNAL_POLICY) trong dữ liệu nguồn.
- **Kết quả phân loại**: `CHUA_DU_BANG_CHUNG`
- **Lý do**: Dữ liệu corpus hiện tại chỉ bao gồm 100% văn bản quy phạm pháp luật bên ngoài (Thông tư NHNN, Nghị định, Luật), chưa có tài liệu quy định nội bộ của tổ chức để tiến hành đối chiếu khoảng cách tuân thủ (Compliance Gap).
- **Confidence**: `0.0` | **Trạng thái**: `NEEDS_HUMAN_REVIEW`

---

### Yêu cầu 3: Tổ chức lại Ngân hàng Thương mại (62/2024/TT-NHNN)
- **Mã Gap**: `GAP_29170549` | **Request ID**: `req_657064bc1687`
- **Yêu cầu bên ngoài**: Quy định điều kiện, hồ sơ, thủ tục chấp thuận việc tổ chức lại ngân hàng thương mại và tổ chức tín dụng phi ngân hàng.
- **Bằng chứng nội bộ**: Không có tài liệu quy định nội bộ (INTERNAL_POLICY) trong dữ liệu nguồn.
- **Kết quả phân loại**: `CHUA_DU_BANG_CHUNG`
- **Lý do**: Dữ liệu corpus hiện tại chỉ bao gồm 100% văn bản quy phạm pháp luật bên ngoài (Thông tư NHNN, Nghị định, Luật), chưa có tài liệu quy định nội bộ của tổ chức để tiến hành đối chiếu khoảng cách tuân thủ (Compliance Gap).
- **Confidence**: `0.0` | **Trạng thái**: `NEEDS_HUMAN_REVIEW`

---

## 4. Bảng Kết quả Tổng hợp (Schema Chuẩn)

| Gap ID | External Citation | Internal Citation | Classification | Confidence | Review Status | Reason |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `GAP_D77A3D21` | `01/2014/TT-NHNN` | `N/A` | **CHUA_DU_BANG_CHUNG** | 0.0 | `NEEDS_HUMAN_REVIEW` | Không có corpus nội bộ để đối chiếu |
| `GAP_DC99718F` | `41/2016/TT-NHNN` | `N/A` | **CHUA_DU_BANG_CHUNG** | 0.0 | `NEEDS_HUMAN_REVIEW` | Không có corpus nội bộ để đối chiếu |
| `GAP_29170549` | `62/2024/TT-NHNN` | `N/A` | **CHUA_DU_BANG_CHUNG** | 0.0 | `NEEDS_HUMAN_REVIEW` | Không có corpus nội bộ để đối chiếu |

---

## 5. Đánh giá Hệ thống

```text
GAP CHECKER: PASS
HUMAN REVIEW REQUIRED: YES
```
