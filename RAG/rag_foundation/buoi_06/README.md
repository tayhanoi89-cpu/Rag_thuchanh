# Buổi 06 - Mini RAG Demo

Project demo nhỏ, dễ đọc, phục vụ workshop về RAG.

## Mục tiêu
- Có sẵn cấu trúc project tối giản
- Dễ mở rộng theo từng buổi học
- Tập trung vào luồng: dữ liệu -> truy xuất -> trả lời

## Cấu trúc
- `app.py`: entry point của ứng dụng
- `rag.py`: logic chính của RAG
- `requirements.txt`: dependency cơ bản
- `.env.example`: mẫu biến môi trường

## Thiết lập
1. Tạo môi trường ảo
2. Cài đặt dependency:
   ```bash
   pip install -r requirements.txt
   ```
3. Sao chép file môi trường:
   ```bash
   copy .env.example .env
   ```
4. Cập nhật giá trị trong `.env`

## Chạy demo
```bash
python app.py
```

## Ghi chú
- Project này mới chỉ là khung demo ban đầu
- Bạn có thể bổ sung UI, vector store, hoặc mô hình AI theo từng bước học
