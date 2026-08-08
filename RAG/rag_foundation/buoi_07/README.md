# Buổi 07 — RAG pipeline tối thiểu

## 1. Mục tiêu

Buổi 07 thực hiện một pipeline RAG nhỏ, tập trung vào:
- đọc dữ liệu đã chuẩn bị ở Buổi 05
- validate chunk JSON
- tạo embedding bằng Gemini
- lưu vector vào ChromaDB persistent
- thực hiện retrieval và confidence gate
- tạo câu trả lời có citation
- cung cấp giao diện Streamlit tiếng Việt
- chạy test offline bằng unittest

## 2. Quan hệ với Buổi 05 và Buổi 06

- Buổi 05 là nguồn dữ liệu đầu vào: các file chunk JSON trong thư mục output/chunks.
- Buổi 06 là tham chiếu kiến trúc, nhưng Buổi 07 không sửa code Buổi 05 hoặc Buổi 06.
- Buổi 07 chỉ làm việc trong thư mục riêng của mình.

## 3. Sơ đồ pipeline

```text
JSON chunks (Buổi 05)
  -> validate
  -> embedding (Gemini)
  -> Chroma persistent collection
  -> retrieval + confidence gate
  -> generation + citation
  -> Streamlit UI / CLI / unittest
```

## 4. Cấu trúc thư mục

```text
rag_foundation/buoi_07/
├── SPEC_buoi_07.md
├── app.py
├── rag.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── tests/
│   ├── __init__.py
│   └── fixtures/
│       └── chunks_sample.json
└── storage/
    └── .gitkeep
```

## 5. Điều kiện đầu vào

- Có thư mục dữ liệu chunk ở Buổi 05: [RAG/rag_foundation/buoi_05/output/chunks](RAG/rag_foundation/buoi_05/output/chunks)
- Có môi trường Python của Buổi 05: [RAG/rag_foundation/buoi_05/.venv](RAG/rag_foundation/buoi_05/.venv)
- Có file cấu hình môi trường ở Buổi 07: [.env.example](RAG/rag_foundation/buoi_07/.env.example)

## 6. Dùng đúng .venv Buổi 05

Windows PowerShell:
```powershell
.
ag_foundationuoi_05\.venv\Scripts\python.exe --version
```

Linux/macOS:
```bash
./rag_foundation/buoi_05/.venv/bin/python --version
```

## 7. Cài requirements

Windows PowerShell:
```powershell
.
ag_foundationuoi_05\.venv\Scripts\python.exe -m pip install -r .\rag_foundation\buoi_07\requirements.txt
```

Linux/macOS:
```bash
./rag_foundation/buoi_05/.venv/bin/python -m pip install -r ./rag_foundation/buoi_07/requirements.txt
```

## 8. Tạo file .env

Sao chép từ file mẫu:

Windows PowerShell:
```powershell
Copy-Item .\rag_foundation\buoi_07\.env.example .\rag_foundation\buoi_07\.env -ErrorAction SilentlyContinue
```

Linux/macOS:
```bash
cp ./rag_foundation/buoi_07/.env.example ./rag_foundation/buoi_07/.env 2>/dev/null || true
```

### Các biến môi trường

- GEMINI_API_KEY: khóa API Gemini. Nếu thiếu, index/query sẽ báo rõ và không tạo kết quả giả.
- GEMINI_EMBEDDING_MODEL: model embedding dùng cho document/query.
- GEMINI_EMBEDDING_DIM: số chiều embedding, ví dụ 768.
- GEMINI_GENERATION_MODEL: model dùng để tạo câu trả lời.
- DEFAULT_TOP_K: giá trị top-k mặc định.
- RAG_MAX_DISTANCE: ngưỡng confidence gate demo cho khoảng cách cosine.

## 9. Lệnh validate

Windows PowerShell:
```powershell
.
ag_foundationuoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_07\rag.py validate --strategy hierarchical
```

Linux/macOS:
```bash
./rag_foundation/buoi_05/.venv/bin/python ./rag_foundation/buoi_07/rag.py validate --strategy hierarchical
```

## 10. Lệnh status

Windows PowerShell:
```powershell
.
ag_foundationuoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_07\rag.py status --strategy hierarchical
```

Linux/macOS:
```bash
./rag_foundation/buoi_05/.venv/bin/python ./rag_foundation/buoi_07/rag.py status --strategy hierarchical
```

## 11. Lệnh index

Windows PowerShell:
```powershell
.
ag_foundationuoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_07\rag.py index --strategy hierarchical
```

Linux/macOS:
```bash
./rag_foundation/buoi_05/.venv/bin/python ./rag_foundation/buoi_07/rag.py index --strategy hierarchical
```

### Reset đúng collection đích

Windows PowerShell:
```powershell
.
ag_foundationuoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_07\rag.py index --strategy hierarchical --reset
```

Linux/macOS:
```bash
./rag_foundation/buoi_05/.venv/bin/python ./rag_foundation/buoi_07/rag.py index --strategy hierarchical --reset
```

## 12. Lệnh query CLI

Windows PowerShell:
```powershell
.
ag_foundationuoi_05\.venv\Scripts\python.exe .\rag_foundation\buoi_07\rag.py query --strategy hierarchical --top-k 5 --question "Cơ cấu lại thời hạn trả nợ được quy định như thế nào?"
```

Linux/macOS:
```bash
./rag_foundation/buoi_05/.venv/bin/python ./rag_foundation/buoi_07/rag.py query --strategy hierarchical --top-k 5 --question "Cơ cấu lại thời hạn trả nợ được quy định như thế nào?"
```

## 13. Lệnh chạy test

Windows PowerShell:
```powershell
.
ag_foundationuoi_05\.venv\Scripts\python.exe -m unittest discover -s .\rag_foundation\buoi_07\tests -v
```

Linux/macOS:
```bash
./rag_foundation/buoi_05/.venv/bin/python -m unittest discover -s ./rag_foundation/buoi_07/tests -v
```

## 14. Lệnh chạy Streamlit

Windows PowerShell:
```powershell
.
ag_foundationuoi_05\.venv\Scripts\python.exe -m streamlit run .\rag_foundation\buoi_07\app.py
```

Linux/macOS:
```bash
./rag_foundation/buoi_05/.venv/bin/python -m streamlit run ./rag_foundation/buoi_07/app.py
```

Để dừng Streamlit, nhấn Ctrl+C trong terminal.

## 15. Giải thích các khái niệm chính

- Strategy: chọn dữ liệu chunk theo kiểu hierarchical, semantic hoặc fixed-size.
- Embedding model: model dùng để tạo vector cho document và query.
- Embedding dimension: số chiều vector, phải khớp giữa index và query.
- Collection identity: collection được định danh bằng strategy + model + dimension để tránh nhầm collection cũ.
- Top-k: số evidence tối đa lấy về cho retrieval.
- Cosine distance: khoảng cách dùng để sắp xếp độ liên quan. Giá trị thấp hơn thường liên quan hơn.
- RAG_MAX_DISTANCE: ngưỡng demo cho confidence gate.
- Confidence gate: chỉ evidence đạt ngưỡng mới được đưa vào generation.
- Retrieval-only: có evidence nhưng generation lỗi hoặc trả text rỗng.
- Citation: thay label như [E1] bằng citation thực tế từ metadata đã lưu.

## 16. Kịch bản kiểm tra thủ công

### A. Có khả năng thuộc tài liệu

Câu hỏi:
```text
Cơ cấu lại thời hạn trả nợ được quy định như thế nào?
```

### B. Có khả năng thuộc tài liệu

Câu hỏi:
```text
Việc phân loại nợ và trích lập dự phòng được thực hiện như thế nào?
```

### C. Ngoài phạm vi

Câu hỏi:
```text
Ngân hàng nào có lãi suất tiết kiệm cao nhất hôm nay?
```

Kết quả cho câu C không nên được giả định là đúng. Nếu retrieval cho câu này vẫn đạt threshold, đó là một trường hợp false positive và cần ghi nhận.

## 17. Troubleshooting

- Thiếu package: cài lại requirements bằng đúng interpreter Buổi 05.
- Sai interpreter: kiểm tra lại đường dẫn đến .venv Buổi 05.
- Thiếu API key: điền GEMINI_API_KEY vào .env và chạy lại index/query.
- Collection rỗng: chạy index trước khi query.
- Model/dimension mismatch: chạy lại index với collection mới hoặc dùng --reset.
- JSON lỗi: kiểm tra cấu trúc file chunk trong Buổi 05.
- Embedding lỗi/rate limit: kiểm tra key, mạng và log lỗi từ runtime.

## 18. Giới hạn của demo

- Đây là demo học tập, không phải tư vấn pháp lý.
- Ngưỡng RAG_MAX_DISTANCE cần được hiệu chỉnh trên dữ liệu thật.
- Retrieval có thể bỏ sót thông tin hoặc trả evidence không đủ mạnh.
- Nội dung chunk có thể được gửi tới Gemini khi embedding/generation; chỉ dùng dữ liệu mà người vận hành được phép gửi tới dịch vụ bên ngoài.

## 19. Checklist nghiệm thu

- [x] Có project Buổi 07
- [x] Có file SPEC_buoi_07.md
- [x] Dùng đúng .venv Buổi 05
- [x] Loader/validator chạy được
- [x] Chroma persistent và collection identity hoạt động
- [x] UI Streamlit có status/index/query/evidence
- [x] Test offline chạy thành công
