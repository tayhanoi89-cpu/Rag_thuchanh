# Bài thực hành 2: Tìm kiếm Đồ thị RAG Đa bước (Multi-hop Graph RAG) và Ứng dụng Hỏi đáp (QA)

## Mục tiêu
Xây dựng một hệ thống Graph RAG (Truy vấn tăng cường bằng đồ thị) bằng cách truy vấn các phân đoạn văn bản và các mối quan hệ được lưu trữ trong cơ sở dữ liệu Neo4j `lab1` từ Bài thực hành 1, thực hiện tìm kiếm đa bước (multi-hop) giữa các văn bản liên quan, và tạo câu trả lời tự động bằng Gemini API.

---

## Các bước thực hiện

### **Bước 1: Kết nối Cơ sở dữ liệu Neo4j**
- Kết nối tới thực thể Neo4j cục bộ bằng các thông tin đã được thiết lập ở Bài thực hành 1:
  - **Connection URL**: `neo4j://localhost:7687` hoặc `bolt://localhost:7687`
  - **Database Name**: `kb-hops`
  - **Credentials**: `neo4j / abcd1234` (hoặc mật khẩu của bạn)

### **Bước 2: Truy vấn Vector và Mối quan hệ Đa bước (Multi-hop)**
- Xây dựng một hàm tìm kiếm ngữ cảnh:
  - Chuyển đổi câu hỏi của người dùng thành vector nhúng bằng mô hình tiếng Việt MSMARCO.
  - Thực hiện tìm kiếm vector trong Neo4j để tìm ra $k$ phân đoạn phù hợp nhất.
  - **Mở rộng Đa bước (Multi-hop)**: Cho phép duyệt qua các mối quan hệ liên kết giữa các tài liệu (ví dụ: `CAN_CU`, `THAY_THE`, `HOP_NHAT`).
  - **Tính linh hoạt**: Cho phép người dùng cấu hình số lượng bước nhảy (ví dụ: $N$ bước nhảy từ tài liệu khớp gốc) để thu thập thêm các đoạn văn bản ngữ cảnh từ các tài liệu luật có liên quan.

Gợi ý triển khai trong project hiện tại:
- Sử dụng script `multi_hop_retrieval.py` để thực hiện trọn vẹn pipeline truy vấn ngữ cảnh:
  - Mã hóa câu hỏi bằng model `thuannc/vi-distilled-msmarco-MiniLM-L12-cos-v5`.
  - Truy vấn top-$k$ `Chunk` tương đồng cosine cao nhất từ Neo4j.
  - Lấy các `Document` nguồn của top-$k$ chunk làm tập seed.
  - Duyệt multi-hop qua quan hệ `RELATIONSHIP` và lọc theo `RELATIONSHIP.type` (ví dụ `CAN_CU`, `THAY_THE`, `HOP_NHAT`).
  - Thu thập thêm chunk ngữ cảnh từ các tài liệu mở rộng theo số bước nhảy cấu hình.

Lệnh chạy mẫu:
1. Truy vấn với 0 bước nhảy (chỉ ngữ cảnh trực tiếp):
  - `python multi_hop_retrieval.py --question "Nghị định 46/2023/NĐ-CP thay thế nghị định nào?" --k 5 --hops 0`
2. Truy vấn với 1 bước nhảy:
  - `python multi_hop_retrieval.py --question "Nghị định 46/2023/NĐ-CP thay thế nghị định nào?" --k 5 --hops 1 --relation-types "THAY_THE,CAN_CU,HOP_NHAT"`
3. Truy vấn với 2 bước nhảy:
  - `python multi_hop_retrieval.py --question "Nghị định 46/2023/NĐ-CP thay thế nghị định nào?" --k 5 --hops 2 --relation-types "THAY_THE,CAN_CU,HOP_NHAT"`

Các tham số chính cần thử nghiệm:
- `--k`: số chunk khớp trực tiếp lấy từ vector search.
- `--hops`: số bước nhảy multi-hop từ tập seed document.
- `--relation-types`: danh sách loại quan hệ tài liệu được phép duyệt.
- `--max-hop-documents`: số tài liệu mở rộng tối đa.
- `--hop-chunk-limit`: số chunk lấy cho mỗi tài liệu mở rộng.

### **Bước 3: Tích hợp Ngữ cảnh và Gọi LLM (Gemini API)**
- Kết nối ngữ cảnh đã truy vấn (các đoạn văn bản khớp trực tiếp + các đoạn văn bản từ tài liệu liên quan đa bước) vào Gemini API (`gemini-flash-latest`).
Nhiệm vụ của người học:
- Thiết kế và tinh chỉnh cấu trúc Prompt hệ thống cho LLM:
  - Cung cấp thông tin chi tiết về lược đồ dữ liệu đồ thị (schema) và cấu trúc của văn bản luật tiếng Việt.
  - Hướng dẫn mô hình trả lời chính xác dựa trên ngữ cảnh được cung cấp, nêu rõ nếu ngữ cảnh không có thông tin thay vì tự suy đoán.

Goi y trien khai trong project hien tai:
- Su dung script `graph_rag_qa_gemini.py` de noi pipeline retrieval + LLM:
  - Script se goi `multi_hop_retrieval.py` (thong qua class `MultiHopRetriever`) de lay `direct_chunks` + `hop_chunks`.
  - Script dung system prompt co schema do thi va quy tac "khong duoc suy doan".
  - Script goi Gemini model mac dinh: `gemini-flash-latest`.

Cai dat va cau hinh API key:
1. Cai SDK Gemini cho Python:
  - `pip install google-generativeai`
2. Dat bien moi truong API key trong PowerShell:
  - `$env:GEMINI_API_KEY="AQ.Ab8RN6L2QNYFlQo93-acDf34CEIFQ0ygT12rCimUhpOBo7sKzg"`

Lenh chay mau:
1. QA voi 0 hop:
  - `python graph_rag_qa_gemini.py --question "Nghi dinh 46/2023/ND-CP thay the nghi dinh nao?" --k 5 --hops 0`
2. QA voi 1 hop:
  - `python graph_rag_qa_gemini.py --question "Nghi dinh 46/2023/ND-CP thay the nghi dinh nao?" --k 5 --hops 1 --relation-types "THAY_THE,CAN_CU,HOP_NHAT"`
3. QA voi 2 hop:
  - `python graph_rag_qa_gemini.py --question "Nghi dinh 46/2023/ND-CP thay the nghi dinh nao?" --k 5 --hops 2 --relation-types "THAY_THE,CAN_CU,HOP_NHAT"`

Khung system prompt de tinh chinh (tom tat):
- Vai tro: Tro ly QA van ban phap luat tieng Viet.
- Quy tac:
  - Chi duoc dung thong tin trong context truy van.
  - Neu khong du thong tin, phai tra loi ro rang la khong tim thay trong ngu canh.
  - Khong duoc tu tao so van ban, dieu khoan, hay moi quan he.
  - Co gang dan chung nguon theo `document_id` va `chunk_id`.
- Schema can dua vao prompt:
  - `(:Document {id, title, source, metadata})`
  - `(:Chunk {id, type, title, text, embedding, embedding_dim})`
  - `(:Chunk)-[:PART_OF]->(:Document)`
  - `(:Document)-[:RELATIONSHIP {type, description}]->(:Document)`

Mau output nen yeu cau tu LLM:
- Phan 1: "Tra loi" (ngan gon, truc tiep).
- Phan 2: "Bang chung" (liet ke cac dong theo dinh dang `document_id/chunk_id: trich dan ngan`).

### **Bước 4: Kiểm thử và Đánh giá Đường ống(pipeline)**
- Tạo **5 câu hỏi kiểm thử** đại diện cho các tình huống tra cứu luật phức tạp cần thông tin từ nhiều tài liệu liên quan:
  1. *Câu hỏi 1*: Nghị định 46/2023/NĐ-CP thay thế cho nghị định nào, và nghị định bị thay thế đó có nội dung gì nổi bật về kinh doanh bảo hiểm?
  2. *Câu hỏi 2*: Văn bản hợp nhất số 52/VBHN-NHNN được hợp nhất từ văn bản nào, và quy định về hồ sơ, thủ tục cấp giấy phép lần đầu của ngân hàng thương mại gồm những tài liệu gì?
  3. *Câu hỏi 3*: Thông tư số 01/2025/TT-NHNN quy định về cấp giấy phép quỹ tín dụng nhân dân được sửa đổi, bổ sung bởi văn bản nào, và những nội dung sửa đổi bổ sung chính là gì?
  4. *Câu hỏi 4*: Thông tư số 41/2016/TT-NHNN về tỷ lệ an toàn vốn của ngân hàng căn cứ vào luật nào, và luật đó quy định chức năng nhiệm vụ của cơ quan nào?
  5. *Câu hỏi 5*: Hoạt động giao nhận, vận chuyển tiền mặt và tài sản quý của Ngân hàng Nhà nước được điều chỉnh bởi Thông tư nào, và Thông tư đó có được sửa đổi bổ sung bởi văn bản nào không?

Nhiệm vụ người học:
- Chạy thử nghiệm trên hệ thống Hỏi đáp của bạn, so sánh câu trả lời thu được khi thay đổi số bước nhảy (ví dụ: so sánh giữa 0 bước, 1 bước và 2 bước nhảy) và ghi nhận kết quả đánh giá so sánh vào một tệp tin mới (ví dụ: `qa_comparison.md`) để chứng minh hiệu quả của ngữ cảnh đa bước.

Goi y thuc thi tu dong trong project:
- Da co script `run_qa_comparison.py` de chay 5 cau hoi voi 3 cau hinh hop (`0`, `1`, `2`) va sinh bao cao markdown.

Lenh chay:
1. Dat API key (PowerShell):
  - `$env:GEMINI_API_KEY="<YOUR_API_KEY>"`
2. Chay danh gia day du:
  - `python run_qa_comparison.py --output qa_comparison.md --top-k 5 --relation-types "CAN_CU,THAY_THE,HOP_NHAT"`
3. Neu muon tao mau file de dien tay (khong goi LLM):
  - `python run_qa_comparison.py --dry-run --output qa_comparison.md`

Ket qua sinh ra:
- `qa_comparison.md`: Bang so sanh cau tra loi giua hops `0/1/2` cho tung cau hoi.
- Thu muc `qa_run_artifacts/`: Luu ket qua chi tiet tung lan chay (`Q1_hops_0.json`, ...).

Tieu chi danh gia de ghi nhan trong bao cao:
- Do day du thong tin: cau tra loi co day du cac ve trong cau hoi hay khong.
- Do dung bang chung: co dan duoc nguon theo `document_id/chunk_id` va phu hop noi dung hay khong.
- Tac dong cua multi-hop: hops `1` hoac `2` co bo sung duoc thong tin ma hops `0` bo sot hay khong.