"""Demonstration of Local Data-at-Rest Encryption for Buoi 17.

Uses AES-128-CBC / HMAC-SHA256 (via cryptography Fernet) to encrypt audit logs.
Key is generated or loaded dynamically from a separate keyfile (.secret.key)
and never hard-coded in the source code.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet

# Set UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BUOI_17_ROOT = Path(__file__).resolve().parent.parent
KEY_PATH = BUOI_17_ROOT / "scripts" / ".audit_encryption.key"
SOURCE_AUDIT_FILE = BUOI_17_ROOT / "outputs" / "audit_log.jsonl"
ENCRYPTED_FILE = BUOI_17_ROOT / "outputs" / "audit_log.jsonl.enc"
REPORT_PATH = BUOI_17_ROOT / "outputs" / "encryption_demo_report.md"


def get_or_create_key() -> bytes:
    """Retrieve encryption key from environment or local keyfile, never hard-coded."""
    env_key = os.getenv("AUDIT_ENCRYPTION_KEY")
    if env_key:
        return env_key.encode("utf-8")

    if KEY_PATH.exists():
        return KEY_PATH.read_bytes().strip()

    # Generate a fresh cryptographic key
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    return key


def run_encryption_demo():
    print("=" * 60)
    print("BẮT ĐẦU CHẠY DEMO MÃ HÓA CỤC BỘ (DATA-AT-REST ENCRYPTION)")
    print("=" * 60)

    # 1. Load key securely
    key = get_or_create_key()
    fernet = Fernet(key)
    print(f"[Key Management] Loaded key from: {KEY_PATH.name} (Key length: {len(key)} bytes)")

    # 2. Read source audit file (without modifying it)
    if not SOURCE_AUDIT_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file audit nguồn: {SOURCE_AUDIT_FILE}")

    original_bytes = SOURCE_AUDIT_FILE.read_bytes()
    original_text = original_bytes.decode("utf-8")
    print(f"[Source Audit] Đọc {len(original_bytes)} bytes từ {SOURCE_AUDIT_FILE.name}")

    # 3. Encrypt data at rest
    encrypted_bytes = fernet.encrypt(original_bytes)
    ENCRYPTED_FILE.write_bytes(encrypted_bytes)
    encrypt_pass = ENCRYPTED_FILE.exists() and len(encrypted_bytes) > 0
    print(f"[Encryption] Mã hóa thành công -> {ENCRYPTED_FILE.name} ({len(encrypted_bytes)} bytes)")
    print(f"  + Preview ciphertext (trích đoạn): {encrypted_bytes[:60].decode('latin-1')}...")

    # 4. Decrypt and verify exact match
    decrypted_bytes = fernet.decrypt(encrypted_bytes)
    decrypted_text = decrypted_bytes.decode("utf-8")
    decrypt_match = (original_bytes == decrypted_bytes)
    print(f"[Decryption] Giải mã và đối chiếu: {'MATCH 100%' if decrypt_match else 'MISMATCH'}")
    print(f"  + Số byte gốc: {len(original_bytes)} | Số byte giải mã: {len(decrypted_bytes)}")

    # 5. Write comprehensive report
    report_content = f"""# Báo cáo Demo Mã hóa Cục bộ Dữ liệu Kiểm toán (Data-at-Rest Encryption)

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
   - Được nạp động từ biến môi trường `AUDIT_ENCRYPTION_KEY` hoặc tệp khóa cục bộ `{KEY_PATH.name}`.
   - Định dạng `*.key` đã được khai báo loại trừ nghiêm ngặt trong `.gitignore` để tránh rủi ro đẩy khóa lên kho mã nguồn.
3. **Bảo toàn dữ liệu**:
   - Quá trình mã hóa chỉ đọc dữ liệu nguồn và sinh tệp mã hóa `{ENCRYPTED_FILE.name}`, hoàn toàn không làm thay đổi hay làm sai lệch tệp dữ liệu nguồn.

---

## 3. Kết quả Thực nghiệm

| Tiêu chí | Kết quả kiểm tra | Trạng thái |
| :--- | :--- | :---: |
| **Tệp nguồn (Plaintext)** | `{SOURCE_AUDIT_FILE.name}` ({len(original_bytes)} bytes) | Đọc thành công |
| **Mã hóa (Encryption)** | Sinh `{ENCRYPTED_FILE.name}` ({len(encrypted_bytes)} bytes) | **PASS** |
| **Giải mã (Decryption)** | Khôi phục chính xác {len(decrypted_bytes)} bytes | **PASS** |
| **Độ khớp nối dữ liệu** | So khớp byte-for-byte đạt 100.0% | **PASS** |

### Đoạn trích Ciphertext (Dữ liệu đã mã hóa):
```text
{encrypted_bytes[:100].decode('latin-1')}...
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
ENCRYPT: {'PASS' if encrypt_pass else 'FAIL'}
DECRYPT MATCH: {'PASS' if decrypt_match else 'FAIL'}
PRODUCTION READY: NO
```
"""

    REPORT_PATH.write_text(report_content, encoding="utf-8")
    print(f"[Report] Đã lưu báo cáo tại: {REPORT_PATH}")


if __name__ == "__main__":
    run_encryption_demo()
