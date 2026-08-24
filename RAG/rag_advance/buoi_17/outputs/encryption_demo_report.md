# Báo cáo Demo Mã hóa Cục bộ Dữ liệu Kiểm toán (Data-at-Rest Encryption)

## 1. Mục tiêu và Phạm vi thực nghiệm
Bài thực hành nhằm minh họa cơ chế bảo vệ an ninh dữ liệu tĩnh (**Data-at-Rest**) cho tệp tin nhật ký kiểm toán (`audit_log.jsonl`), đảm bảo ngay cả khi kẻ tấn công có quyền truy cập vật lý hoặc đánh cắp file từ ổ cứng, dữ liệu audit vẫn không bị rò rỉ dưới dạng văn bản rõ (plaintext).

> [!WARNING]
> Đây là demo minh họa cơ bản ở cấp độ ứng dụng cục bộ, **KHÔNG PHẢI giải pháp Production-ready**. 

---

## 2. Thiết kế Cơ chế Mã hóa

1. **Thuật toán sử dụng**:
   - Thư viện `cryptography.fernet.Fernet`.
   - Chuẩn mã hóa đối xứng: **AES-128-CBC** kết hợp với **HMAC-SHA256** để xác thực tính toàn vẹn (Authenticated Encryption), sử dụng dẫn xuất khóa PKCS7 padding.
2. **Quản lý Khóa (Key Management)**:
   - Khóa **không được hard-code** trong mã nguồn Python.
   - Được nạp động từ biến môi trường `AUDIT_ENCRYPTION_KEY` hoặc tệp khóa cục bộ `.audit_encryption.key`.
   - Định dạng `*.key` đã được khai báo loại trừ nghiêm ngặt trong `.gitignore` để tránh rủi ro đẩy khóa lên kho mã nguồn.
3. **Bảo toàn dữ liệu**:
   - Quá trình mã hóa chỉ đọc dữ liệu nguồn và sinh tệp mã hóa `audit_log.jsonl.enc`, hoàn toàn không làm thay đổi hay làm sai lệch tệp dữ liệu nguồn.

---

## 3. Kết quả Thực nghiệm

| Tiêu chí | Kết quả kiểm tra | Trạng thái |
| :--- | :--- | :---: |
| **Tệp nguồn (Plaintext)** | `audit_log.jsonl` (1544 bytes) | Đọc thành công |
| **Mã hóa (Encryption)** | Sinh `audit_log.jsonl.enc` (2148 bytes) | **PASS** |
| **Giải mã (Decryption)** | Khôi phục chính xác 1544 bytes | **PASS** |
| **Độ khớp nối dữ liệu** | So khớp byte-for-byte đạt 100.0% | **PASS** |

### Đoạn trích Ciphertext (Dữ liệu đã mã hóa):
```text
gAAAAABqiFCIRBW2LWsMS-Q7dMhTmZJlwqu4-piWUh9dhBZ9Xf_6Xtabm2thIj6UKN2ei9W3IiB3F3rDg8UimrkUlxyBsxELJCf8...
```

---

## 4. Phân tích Khoảng cách tới Hệ thống Production thực tế

Để đưa cơ chế bảo vệ dữ liệu vào môi trường Doanh nghiệp / Ngân hàng thực tế, cần hoàn thiện các trụ cột an ninh bắt buộc:

1. **Bảo vệ Dữ liệu Truyền tải (Data-in-Transit)**:
   - Bắt buộc kích hoạt **TLS 1.3** mã hóa toàn bộ kênh giao tiếp mạng giữa Streamlit, AI Agent, Neo4j Graph DB và LLM Router API.
   - Sử dụng chứng chỉ số x509 được cấp phát và quản lý bởi Certificate Authority (CA) nội bộ / tin cậy.
2. **Hệ thống Quản lý Khóa Chuyên dụng (KMS / HSM)**:
   - Không lưu trữ file `.key` trên filesystem máy chủ ứng dụng.
   - Tích hợp dịch vụ Quản lý khóa tập trung cấp phần cứng: **AWS KMS**, **Azure Key Vault**, **HashiCorp Vault**, hoặc thiết bị **HSM FIPS 140-2/3 Level 3**.
3. **Chính sách Luân chuyển Khóa (Key Rotation)**:
   - Thiết lập quy trình tự động luân chuyển khóa định kỳ (ví dụ: 90 ngày/lần) và hỗ trợ giải mã đa thế hệ khóa (Envelope Encryption).
4. **Kiểm soát Truy cập Đặc quyền (IAM & Zero Trust)**:
   - Áp dụng nguyên tắc đặc quyền tối thiểu (Least Privilege). Chỉ có tiến trình Audit Service có quyền đọc Master Key để mã hóa; quyền giải mã chỉ cấp cho Quản trị viên Tuân thủ / Kiểm toán nội bộ.
5. **Sao lưu Bất biến & Khắc phục Thảm họa (Immutable Backup & DR)**:
   - Nhật ký kiểm toán phải được chuyển vào kho lưu trữ bất biến **WORM (Write Once, Read Many)** ngăn chặn nguy cơ bị xóa/sửa đổi bởi tài khoản quản trị cấp cao.

---

```text
ENCRYPT: PASS
DECRYPT MATCH: PASS
PRODUCTION READY: NO
```
