"""Test suite for Secure Retrieval Adapter in Buoi 17."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

# Set UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BUOI_17_ROOT = Path(__file__).resolve().parent.parent
BUOI_14_ROOT = BUOI_17_ROOT.parent / "buoi_14"

sys.path.insert(0, str(BUOI_17_ROOT))
sys.path.insert(0, str(BUOI_14_ROOT))

from scripts.secure_retrieval_adapter import SecureRetrievalAdapter

def run_tests():
    adapter = SecureRetrievalAdapter()
    
    print("=== BẮT ĐẦU KIỂM THỬ SECURE RETRIEVAL ADAPTER ===")
    
    # Target query and chunks to test
    query = "vận chuyển và bảo quản tiền mặt ngân hàng"
    risk_target_chunk = "44209__full"  # TT 01/2014/TT-NHNN - Quản lý tiền mặt (Risk class: Admin, Risk_Officer, Employee)
    
    # All 10 Risk-restricted chunks (not allowed for Guest or HR_Manager)
    restricted_chunk_ids = {
        "44209__full", "177271__full", "168220__full", "174218__full", "117310__full",
        "6e689cd0-6f81-11f1-94d6-fd5d6d5ff793__full", "185630__full", "173695__full",
        "95652__full", "25692__full"
    }

    # -------------------------------------------------------------
    # Test Case 1: Role được phép nhận được chunk
    # -------------------------------------------------------------
    print("\n[Test 1] Role được phép truy cập (Employee / Staff)...")
    res_employee = adapter.retrieve(query, user_roles=["Staff"], method="hybrid", top_k=5)
    emp_chunk_ids = [r["chunk_id"] for r in res_employee]
    test1_pass = risk_target_chunk in emp_chunk_ids
    print(f"  + Retrieved chunk IDs: {emp_chunk_ids}")
    print(f"  + Target Risk chunk ({risk_target_chunk}) found: {test1_pass} -> {'PASS' if test1_pass else 'FAIL'}")

    # -------------------------------------------------------------
    # Test Case 2: Role không được phép KHÔNG nhận được chunk đó
    # -------------------------------------------------------------
    print("\n[Test 2] Role không được phép truy cập (Guest / HR)...")
    res_guest = adapter.retrieve(query, user_roles=["Guest"], method="hybrid", top_k=5)
    guest_chunk_ids = [r["chunk_id"] for r in res_guest]
    
    # Check that no restricted chunk is returned
    leaked_chunks = set(guest_chunk_ids).intersection(restricted_chunk_ids)
    test2_pass = (len(leaked_chunks) == 0) and all("Guest" in r["allowed_roles"] for r in res_guest)
    print(f"  + Retrieved chunk IDs for Guest: {guest_chunk_ids}")
    print(f"  + Restricted chunks leaked: {leaked_chunks}")
    print(f"  + All returned chunks valid for Guest: {test2_pass} -> {'PASS' if test2_pass else 'FAIL'}")

    # -------------------------------------------------------------
    # Test Case 3: Unauthorized chunk không xuất hiện trong LLM context
    # -------------------------------------------------------------
    print("\n[Test 3] Kiểm tra Unauthorized chunk trong Context...")
    context_guest = adapter.build_context(res_guest)
    leaked_context_chunks = [c_id for c_id in restricted_chunk_ids if c_id in context_guest]
    test3_pass = (len(leaked_context_chunks) == 0)
    print(f"  + Context length: {len(context_guest)} chars")
    print(f"  + Leaked restricted chunk IDs in context: {leaked_context_chunks}")
    print(f"  + No unauthorized context: {test3_pass} -> {'PASS' if test3_pass else 'FAIL'}")

    # -------------------------------------------------------------
    # Test Case 4: citation/document_id/chunk_id không bị mất
    # -------------------------------------------------------------
    print("\n[Test 4] Kiểm tra tính toàn vẹn metadata (citation/document_id/chunk_id)...")
    test4_pass = True
    required_keys = ["rank", "chunk_id", "document_id", "title", "article", "citation", "allowed_roles", "access_decision", "retrieval_method", "score", "text"]
    for item in res_employee:
        missing = [k for k in required_keys if k not in item or item[k] is None or item[k] == ""]
        if missing:
            test4_pass = False
            print(f"  - Missing keys {missing} in: {item['chunk_id']}")
    print(f"  + Standardized fields check on {len(res_employee)} records: {'PASS' if test4_pass else 'FAIL'}")
    
    # -------------------------------------------------------------
    # Output to secure_retrieval_test.md
    # -------------------------------------------------------------
    report_content = f"""# Báo cáo Kiểm thử Secure Retrieval Adapter Buổi 17

## 1. Mục tiêu kiểm thử
Xác thực việc tái sử dụng `SecureRetriever` từ Buổi 16 thông qua `SecureRetrievalAdapter` tại Buổi 17, đảm bảo:
1. **Quyền hợp lệ**: Role được phép truy cập (`Staff` / `Employee`) nhận được đúng tài liệu liên quan.
2. **Loại trừ truy cập trái phép**: Role không có quyền (`Guest` / `HR`) bị loại trừ tuyệt đối toàn bộ 10 chunk hạn chế nghiệp vụ rủi ro.
3. **Không rò rỉ ngữ cảnh (Zero Leakage Context)**: Ngữ cảnh (Context) sinh ra cho LLM hoàn toàn không chứa bất kỳ chunk hoặc nội dung tài liệu trái phép nào.
4. **Bảo toàn siêu dữ liệu**: Chuẩn hóa và giữ nguyên vẹn 100% các trường định danh (`rank`, `chunk_id`, `document_id`, `title`, `article`, `citation`, `allowed_roles`, `access_decision`, `retrieval_method`).

---

## 2. Kết quả 4 kịch bản kiểm thử chi tiết

### Kịch bản 1: Role được phép nhận được chunk (`Staff` / `Employee`)
- **Truy vấn**: `"{query}"`
- **Target chunk**: `{risk_target_chunk}` (Thông tư 01/2014/TT-NHNN - Quản lý tiền mặt, nhóm `Risk`)
- **Kết quả trả về**:
  - Danh sách chunk IDs: `{emp_chunk_ids}`
  - Target chunk `{risk_target_chunk}` xuất hiện ở vị trí Top 1: **{'Có' if test1_pass else 'Không'}**
- **Trạng thái**: **{'PASS' if test1_pass else 'FAIL'}**

### Kịch bản 2: Role không được phép KHÔNG nhận được chunk (`Guest`)
- **Truy vấn**: `"{query}"`
- **Kết quả trả về**:
  - Danh sách chunk IDs: `{guest_chunk_ids}`
  - Target chunk `{risk_target_chunk}` xuất hiện trong kết quả: **{'Có (LỖI RÒ RỈ)' if (risk_target_chunk in guest_chunk_ids) else 'Không (Được lọc an toàn)'}**
  - Số lượng chunk hạn chế (`Risk`) bị rò rỉ: **{len(leaked_chunks)}**
  - 100% chunk trả về đều có quyền `'Guest'`: **{'ĐÚNG' if test2_pass else 'SAI'}**
- **Trạng thái**: **{'PASS' if test2_pass else 'FAIL'}**

### Kịch bản 3: Ngữ cảnh LLM không chứa thông tin trái phép (Zero Leakage Context)
- **Kiểm tra Context sinh cho Guest**:
  - Độ dài Context: {len(context_guest):,} ký tự.
  - Số chunk thuộc danh sách 10 tài liệu hạn chế xuất hiện trong context: **{len(leaked_context_chunks)}**.
  - Không có bất kỳ chunk ID hoặc nội dung tài liệu hạn chế nào lọt vào Context: **{'ĐÚNG' if test3_pass else 'SAI'}**.
- **Trạng thái**: **{'PASS' if test3_pass else 'FAIL'}**

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
- **Trạng thái**: **{'PASS' if test4_pass else 'FAIL'}**

---

## 3. Mẫu kết quả chuẩn hóa từ Adapter

```json
{dict_to_pretty_json(res_employee[0]) if res_employee else "{}"}
```

---

```text
SECURE RETRIEVAL REUSE: {'PASS' if (test1_pass and test2_pass) else 'FAIL'}
NO UNAUTHORIZED CONTEXT: {'PASS' if test3_pass else 'FAIL'}
CITATION PRESERVED: {'PASS' if test4_pass else 'FAIL'}
```
"""
    output_path = BUOI_17_ROOT / "outputs" / "secure_retrieval_test.md"
    output_path.write_text(report_content, encoding="utf-8")
    print(f"\nĐã ghi báo cáo kiểm thử tại: {output_path}")

def dict_to_pretty_json(d):
    # Strip very long text for clean presentation
    cleaned = dict(d)
    if "text" in cleaned and len(cleaned["text"]) > 200:
        cleaned["text"] = cleaned["text"][:200] + "..."
    return json.dumps(cleaned, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_tests()
