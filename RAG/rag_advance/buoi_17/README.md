# Buổi 17: Secure RAG & Compliance Gap Analysis Trong Ngân Hàng

## 1. Tổng quan Kiến trúc
Buổi 17 chuyển đổi hệ thống RAG từ tìm kiếm tài liệu thông thường sang hệ thống an toàn cấp độ doanh nghiệp (Enterprise Grade) với các thành phần cốt lõi:
1. **RBAC Pre-filtering**: Lọc bỏ 100% tài liệu hạn chế trước retrieval và trước context LLM (Zero Leakage).
2. **Audit Trail**: Ghi nhận toàn bộ thao tác, người dùng, vai trò, câu hỏi, kết quả và trạng thái truy cập theo chuẩn ISO-8601 UTC.
3. **Mã hóa At-Rest Cục bộ**: Mã hóa nhật ký kiểm toán bằng Fernet AES-128-CBC + HMAC-SHA256, minh bạch phạm vi demo đào tạo.
4. **Use Case 1 (Internal Policy Lookup)**: Trợ lý AI tra cứu văn bản quy định với grounded generation và trích dẫn pháp lý thực tế.
5. **Use Case 2 (Compliance Gap Checker)**: Rà soát khoảng cách tuân thủ giữa quy định NHNN và quy chế nội bộ với cơ chế Human-in-the-loop.
6. **Streamlit UI**: Giao diện trực quan hỗ trợ chuyển đổi role, tra cứu, đối chiếu gap và xem log kiểm toán thời gian thực.

---

## 2. Cấu trúc Thư mục

```text
buoi_17/
├── config/
│   └── rbac_policy.json                # Định nghĩa chính sách phân quyền RBAC
├── scripts/
│   ├── rbac.py                         # Module chuẩn hóa vai trò và kiểm tra quyền
│   ├── secure_retrieval.py             # Re-export adapter truy xuất an toàn
│   ├── secure_retrieval_adapter.py     # Adapter bọc SecureRetriever từ Buổi 14/16
│   ├── audit_logger.py                 # Engine ghi nhận nhật ký kiểm toán
│   ├── encryption_demo.py              # Demo mã hóa dữ liệu at-rest (Fernet)
│   ├── internal_lookup.py              # Use Case 1: Tra cứu quy định nội bộ
│   ├── compliance_gap.py               # Use Case 2: AI Compliance Gap Checker
│   ├── security_tests.py               # 10 kịch bản kiểm thử bảo mật & tuân thủ
│   └── final_validation.py             # Script tổng duyệt toàn bộ hệ thống
├── outputs/
│   ├── dependency_report.md            # Báo cáo kiểm tra phụ thuộc dữ liệu
│   ├── rbac_reuse_report.md            # Báo cáo tái sử dụng RBAC
│   ├── rbac_test_report.md             # Báo cáo kiểm thử RBAC
│   ├── secure_retrieval_test.md        # Báo cáo kiểm thử Secure Retrieval Adapter
│   ├── audit_log.jsonl                 # Nhật ký kiểm toán các yêu cầu
│   ├── audit_log.jsonl.enc             # File audit đã mã hóa
│   ├── encryption_demo_report.md       # Báo cáo demo mã hóa at-rest
│   ├── internal_lookup_demo.md         # Báo cáo thực nghiệm Use Case 1
│   ├── gap_input_catalog.md            # Danh mục phân loại dữ liệu Gap
│   ├── compliance_gap_results.csv      # Bảng kết quả phân tích Gap (14 cột)
│   ├── compliance_gap_report.md        # Báo cáo đánh giá AI Compliance Gap
│   ├── graph_gap_integration_report.md # Báo cáo đánh giá vai trò Knowledge Graph
│   ├── security_test_report.md         # Báo cáo 10 test cases bảo mật
│   └── final_validation_report.md      # Báo cáo tổng duyệt toàn diện
├── app.py                              # Giao diện Streamlit hoàn chỉnh
└── README.md                           # Tài liệu hướng dẫn sử dụng
```

---

## 3. Hướng dẫn Chạy Hệ thống

### 3.1. Kích hoạt môi trường và chạy ứng dụng Streamlit
```powershell
# Chạy ứng dụng Streamlit
..\..\..\.venv\Scripts\python.exe -m streamlit run app.py
```

### 3.2. Chạy từng script kiểm thử độc lập
```powershell
# 1. Kiểm thử Secure Retrieval Adapter
..\..\..\.venv\Scripts\python.exe scripts/run_secure_retrieval_test.py

# 2. Demo Mã hóa At-Rest
..\..\..\.venv\Scripts\python.exe scripts/encryption_demo.py

# 3. Chạy Use Case 1: Tra cứu quy định nội bộ
..\..\..\.venv\Scripts\python.exe scripts/internal_lookup.py

# 4. Chạy Use Case 2: Compliance Gap Checker
..\..\..\.venv\Scripts\python.exe scripts/compliance_gap.py

# 5. Chạy Security Test Suite (10 Kịch bản)
..\..\..\.venv\Scripts\python.exe scripts/security_tests.py

# 6. Chạy Tổng duyệt Toàn diện (Final Validation)
..\..\..\.venv\Scripts\python.exe scripts/final_validation.py
```

---

## 4. Kịch bản Demo Chuẩn (Demo Flow)

1. **Cùng query, hai role** → Chứng minh `Risk_Manager` nhận được tài liệu rủi ro tiền mặt/CAR, trong khi `Guest` bị chặn hoàn toàn.
2. **Audit log** → Chứng minh mọi request (kể cả bị DENY) đều được ghi nhận với request_id và số lượng chunk bị lọc.
3. **Tra cứu quy định nội bộ** → AI trả lời chính xác từ ngữ cảnh đã qua RBAC kèm trích dẫn văn bản pháp lý thực tế.
4. **Compliance Gap Checker** → Minh bạch phân loại `CHUA_DU_BANG_CHUNG` khi thiếu dữ liệu quy định nội bộ, không bịa đặt kết luận.
5. **Human Review** → 100% kết quả rà soát đều có trạng thái `NEEDS_HUMAN_REVIEW` để kiểm toán viên thẩm định cuối cùng.

---

## 5. Câu chốt Buổi 17

> *"Buổi 17 chuyển hệ thống từ việc chỉ tìm đúng tài liệu sang việc kiểm soát ai được thấy tài liệu nào, truy vết hệ thống đã làm gì và hỗ trợ kiểm toán viên đối chiếu quy định bằng evidence."*

> *"Trong hệ thống ngân hàng, trả lời đúng chưa đủ. Kết quả còn phải đúng quyền, có nguồn, có log và có người chịu trách nhiệm kiểm tra."*
