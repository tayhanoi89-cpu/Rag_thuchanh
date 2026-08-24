# Danh Mục Phân Loại Tài Liệu Phục Vụ Compliance Gap Analysis

## 1. Tổng quan Đánh giá Dữ liệu Nguồn
- **Nguồn dữ liệu**: `buoi_16/data/processed/chunks_secure.csv` (15 chunks / 15 documents).
- **Mục tiêu**: Kiểm tra và phân loại tài liệu theo evidence thực tế để chuẩn bị dữ liệu cho quy trình **Compliance Gap Analysis** (đối chiếu quy định nội bộ của tổ chức với yêu cầu pháp lý bên ngoài).
- **Nguyên tắc phân loại**:
  - `EXTERNAL_REQUIREMENT`: Tài liệu quy phạm pháp luật do cơ quan nhà nước ban hành (Luật, Nghị định, Thông tư, Văn bản hợp nhất).
  - `INTERNAL_POLICY`: Quy định/Quy trình/Chính sách nội bộ do tổ chức tín dụng / ngân hàng ban hành.
  - *Tuyệt đối không gán ép một Thông tư hay Nghị định bên ngoài thành "quy định nội bộ" để giả lập dữ liệu.*

---

## 2. Bảng Phân loại Chi tiết Toàn bộ 15 Tài liệu

| STT | Document ID | Số hiệu / Citation | Loại văn bản | Cơ quan ban hành | Ngày ban hành | Phân loại (Classification) | Evidence phân loại |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| 1 | `44209` | `01/2014/TT-NHNN` | Thông tư | Ngân hàng Nhà nước Việt Nam | 06/01/2014 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Thống đốc NHNN ban hành |
| 2 | `177271` | `01/2025/TT-NHNN` | Thông tư | Ngân hàng Nhà nước Việt Nam | 29/04/2025 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Thống đốc NHNN ban hành |
| 3 | `112025` | `73/2016/NĐ-CP` | Nghị định | Chính phủ | 01/07/2016 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Chính phủ ban hành |
| 4 | `169221` | `43/2024/TT-NHNN` | Thông tư | Ngân hàng Nhà nước Việt Nam | 09/08/2024 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Thống đốc NHNN ban hành |
| 5 | `163441` | `46/2023/NĐ-CP` | Nghị định | Chính phủ | 01/07/2023 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Chính phủ ban hành |
| 6 | `168220` | `27/2024/TT-NHNN` | Thông tư | Ngân hàng Nhà nước Việt Nam | 28/06/2024 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Thống đốc NHNN ban hành |
| 7 | `174218` | `62/2024/TT-NHNN` | Thông tư | Ngân hàng Nhà nước Việt Nam | 31/12/2024 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Thống đốc NHNN ban hành |
| 8 | `117310` | `41/2016/TT-NHNN` | Thông tư | Ngân hàng Nhà nước Việt Nam | 30/12/2016 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Thống đốc NHNN ban hành |
| 9 | `112924` | `105/2016/TT-BTC` | Thông tư | Bộ Tài chính | 29/06/2016 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Bộ Tài chính ban hành |
| 10 | `166269` | `17/2023/QH15` | Luật | Quốc hội | 20/06/2023 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Quốc hội thông qua |
| 11 | `6e689cd0-6f81-11f1-94d6-fd5d6d5ff793` | `52/VBHN-NHNN` | Văn bản hợp nhất | Ngân hàng Nhà nước Việt Nam | 21/05/2026 | **EXTERNAL_REQUIREMENT** | Văn bản hợp nhất văn bản quy phạm pháp luật của NHNN |
| 12 | `185630` | `63/2025/TT-NHNN` | Thông tư | Ngân hàng Nhà nước Việt Nam | 31/12/2025 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Thống đốc NHNN ban hành |
| 13 | `173695` | `56/2024/TT-NHNN` | Thông tư | Ngân hàng Nhà nước Việt Nam | 24/12/2024 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Thống đốc NHNN ban hành |
| 14 | `95652` | `135/2015/NĐ-CP` | Nghị định | Chính phủ | 31/12/2015 | **EXTERNAL_REQUIREMENT** | Văn bản quy phạm pháp luật do Chính phủ ban hành |
| 15 | `25692` | `46/2010/QH12` | Luật | Quốc hội | 16/06/2010 | **EXTERNAL_REQUIREMENT** | Luật Ngân hàng Nhà nước do Quốc hội thông qua |

---

## 3. Thống kê & Đánh giá Dữ liệu Phục vụ Compliance Gap

- **Tổng số document**: 15 tài liệu.
- **Số tài liệu EXTERNAL_REQUIREMENT**: 15/15 (100%).
- **Số tài liệu INTERNAL_POLICY**: 0/15 (0%).

### Nhận xét & Kết luận:
1. **Thiếu một vế so sánh**: Quy trình Compliance Gap Analysis bắt buộc phải có ít nhất 2 tập dữ liệu:
   - Tập 1: Quy định bên ngoài cần tuân thủ (`EXTERNAL_REQUIREMENT` - Nhà nước/NHNN).
   - Tập 2: Quy chế/Quy định nội bộ của đơn vị (`INTERNAL_POLICY` - Ngân hàng thương mại/Tổ chức).
2. **Không gán ép dữ liệu**: Toàn bộ 15 văn bản trong `chunks_secure.csv` đều là Luật của Quốc hội, Nghị định của Chính phủ, Thông tư và Văn bản hợp nhất của NHNN/Bộ Tài chính. Không có văn bản nào là quy chế nội bộ thực sự của một ngân hàng thương mại cụ thể.
3. **Quyết định tuân thủ**: Không kết luận compliance hoặc tự suy diễn kết quả gap analysis trên tập dữ liệu này.

---

```text
COMPLIANCE GAP DATA: INSUFFICIENT
DATA GAP: INTERNAL POLICY NOT FOUND
```
