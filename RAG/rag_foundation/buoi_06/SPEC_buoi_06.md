# SPEC_buoi_06

## Workspace

Chỉ được phép đọc các đường dẫn sau:
- `RAG/rag_foundation/buoi_05/output/chunks/`
- `RAG/rag_foundation/buoi_05/.venv/`
- `RAG/rag_foundation/buoi_06/`

Không được đọc:
- source code của Buổi 5
- README các buổi trước
- notebook
- git history
- các thư mục khác

Buổi 5 là black box. Không reverse engineering. Không phân tích cách Buổi 5 hoạt động.

## Python

Sử dụng đúng interpreter trong:
- `RAG/rag_foundation/buoi_05/.venv/`

Không tạo virtual environment mới.

## Package

Chỉ được phép cài các package sau:
- streamlit
- google-genai
- chromadb
- psycopg
- python-dotenv

Không cài framework khác.

## Coding Style

Ưu tiên thiết kế:
- ít file
- ít class
- ít function
- code dễ đọc

Không tạo các pattern sau:
- repository pattern
- service layer
- dependency injection
- factory
- plugin

## Scope

Chỉ cần phát triển các chức năng:
- index
- retrieval
- answer
- streamlit

Không phát triển ngoài yêu cầu.

## Error Handling

Chỉ cần try/except tối thiểu.

Không cần:
- retry
- logging
- monitoring

## Security

Không in ra:
- API Key
- password
- secret

## Code Size

Mục tiêu khoảng 300–500 dòng Python.

Nếu vượt khoảng 700 dòng, hãy đơn giản hóa thiết kế.

## Delivery Expectations

- Project phải nhỏ gọn, dễ đọc và dễ demo.
- Tập trung vào khả năng chạy được và minh họa RAG workflow cơ bản.
- Không thêm feature phụ không liên quan đến index, retrieval, answer và streamlit.
- Giữ code tối giản nhưng đủ để demo một luồng RAG hoàn chỉnh.
