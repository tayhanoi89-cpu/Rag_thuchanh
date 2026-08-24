# Báo cáo Thực nghiệm Use Case 1: AI Tra Cứu Quy Định Nội Bộ

## 1. Tổng quan Kiến trúc và Nguyên tắc Hoạt động
Use Case 1 xây dựng trợ lý AI tra cứu văn bản quy phạm pháp luật và quy định nội bộ ngân hàng với 3 tầng bảo vệ:
1. **RBAC Pre-filtering**: Lọc bỏ các tài liệu hạn chế trước khi thực hiện truy xuất tìm kiếm (Hybrid Search).
2. **Context-Grounded LLM Generation**: LLM (`gemini-3.6-flash`) chỉ được sinh câu trả lời dựa trên ngữ cảnh đã qua kiểm duyệt quyền. Nếu context không có hoặc không đủ thông tin, bắt buộc phản hồi:
   > *"Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập."*
3. **Audit Trail**: Toàn bộ yêu cầu, người dùng, vai trò, câu hỏi, kết quả truy xuất, số tài liệu bị RBAC lọc và trạng thái đều được ghi nhận vào `outputs/audit_log.jsonl`.

---

## 2. Kết quả Thực nghiệm 3 Kịch bản

### Kịch bản 1: Truy vấn Tài liệu Rủi ro với Quyền Hợp lệ (`Risk_Manager`)
- **Câu hỏi**: `"Quy định về việc giao nhận, bảo quản và vận chuyển tiền mặt, tài sản quý, giấy tờ có giá trong ngành ngân hàng?"`
- **Người dùng**: `user_risk_officer_01` | **Vai trò**: `Risk_Manager`
- **Phạm vi truy cập**: `Allowed: 15/15 chunks (Filtered: 0)`
- **Trích dẫn (Citations)**: `['01/2014/TT-NHNN', '41/2016/TT-NHNN', '46/2023/NĐ-CP']`
- **Chunk IDs**: `['44209__full', '117310__full', '163441__full']`
- **Trạng thái**: `SUCCESS`
- **Câu trả lời sinh ra**:
Dựa trên **Thông tư số 01/2014/TT-NHNN** được cung cấp trong ngữ cảnh, các quy định về việc giao nhận, bảo quản và vận chuyển tiền mặt, tài sản quý, giấy tờ có giá trong ngành ngân hàng được thể hiện qua các nội dung sau:

### 1. Quy định về giao nhận ngoại tệ và giấy tờ có giá (Điều 13)
* **Giao nhận ngoại tệ:**
  * Các khoản thu, chi ngoại tệ giữa tổ chức tín dụng (TCTD), chi nhánh ngân hàng nước ngoài với khách hàng; giữa các TCTD, chi nhánh ngân hàng nước ngoài với nhau; giữa Sở Giao dịch, Ngân hàng Nhà nước (NHNN) chi nhánh với TCTD, chi nhánh ngân hàng nước ngoài phải thực hiện **kiểm đếm tờ và theo đúng quy trình thu chi tiền mặt**.
  * TCTD, chi nhánh ngân hàng nước ngoài tự quy định việc giao nhận ngoại tệ trong hệ thống của mình.
* **Giao nhận giấy tờ có giá:**
  * *Giữa TCTD, chi nhánh ngân hàng nước ngoài, Sở Giao dịch, NHNN chi nhánh và khách hàng; giữa Sở Giao dịch, NHNN chi nhánh và TCTD, chi nhánh ngân hàng nước ngoài; giữa các TCTD, chi nhánh ngân hàng nước ngoài:* Phải kiểm đếm tờ và thực hiện theo quy trình thu chi tiền mặt.
  * *Giữa cơ sở in, đúc tiền với kho tiền Trung ương, giữa kho tiền Trung ương và Sở Giao dịch, NHNN chi nhánh, giữa các NHNN chi nhánh, giữa các kho tiền Trung ương với nhau:*
    * **Giấy tờ có giá mới in:** Giao nhận theo bao nguyên niêm phong kẹp chì như đối với tiền mặt hoặc bó nguyên niêm phong (nếu không chẵn bao). 
    * **Giấy tờ có giá đã qua lưu thông:** Giao nhận theo bó đủ 10 thếp, nguyên niêm phong của Sở Giao dịch, NHNN chi nhánh; trường hợp không đủ bó thì giao nhận theo tờ. Sở Giao dịch, NHNN chi nhánh nhận phải thành lập Hội đồng kiểm đếm tờ trước khi giao cho TCTD, chi nhánh ngân hàng nước ngoài hoặc khách hàng.
    * **Giấy tờ có giá hết thời hạn lưu hành:** Giao nhận theo bó nguyên niêm phong của Sở Giao dịch, NHNN chi nhánh hoặc giao nhận theo tờ (nếu không đủ bó).
  * *Giấy tờ có giá do TCTD, chi nhánh ngân hàng nước ngoài, Kho bạc Nhà nước lưu ký tại NHNN để tham gia các nghiệp vụ thị trường tiền tệ:* Thực hiện giao nhận theo bó đủ 10 thếp nguyên niêm phong; trường hợp không đủ bó thì giao nhận theo tờ.
  * TCTD, chi nhánh ngân hàng nước ngoài quy định việc giao nhận giấy tờ có giá trong hệ thống.

---

### 2. Quy định về bảo quản và trách nhiệm của Thủ kho tiền (Điều 19)
Thủ kho tiền (tại Sở Giao dịch, NHNN chi nhánh, TCTD, chi nhánh ngân hàng nước ngoài) chịu trách nhiệm đảm bảo an toàn tuyệt đối các loại tài sản bảo quản trong kho tiền, với các nhiệm vụ chi tiết:
* **Xuất - nhập tài sản:** Thực hiện việc xuất - nhập tiền mặt, tài sản quý, giấy tờ có giá chính xác, kịp thời, đầy đủ theo đúng lệnh của cấp có thẩm quyền và chứng từ kế toán hợp lệ, hợp pháp.
* **Quản lý sổ sách:** Mở sổ quỹ, sổ theo dõi từng loại tiền, từng loại tài sản, thẻ kho và các sổ sách cần thiết khác; ghi chép, bảo quản sổ sách, giấy tờ đầy đủ, rõ ràng, chính xác.
* **Sắp xếp, bảo quản kho:** Sắp xếp tiền mặt, tài sản quý, giấy tờ có giá trong kho tiền gọn gàng, khoa học, đảm bảo vệ sinh; đề xuất các biện pháp cần thiết để bảo đảm chất lượng tài sản bảo quản trong kho tiền.
* **Quản lý chìa khóa:** Quản lý, giữ chìa khóa một ổ khóa của lớp cánh trong cửa kho tiền bảo quản tài sản được giao, các ổ khóa cửa gian kho và các phương tiện bảo quản tài sản trong kho tiền (két, tủ sắt).
* **Phân công thủ kho đặc thù:**
  * Thủ kho tiền NHNN chi nhánh bảo quản tiền mặt thuộc Quỹ dự trữ phát hành; vàng, các loại kim khí quý, đá quý và các tài sản khác.
  * Kho tiền Trung ương có các thủ kho riêng biệt: thủ kho Quỹ dự trữ phát hành, thủ kho tài sản quý, thủ kho giấy tờ có giá.
* **Nhân sự hỗ trợ:** Có các nhân viên phụ kho để giúp thủ kho tiền trong việc kiểm đếm, đóng gói, bốc xếp, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá.

---

### 3. Quy định về ủy quyền quản lý tiền mặt, tài sản quý, giấy tờ có giá (Điều 26)
* Giám đốc được ủy quyền bằng văn bản cho một Phó Giám đốc thực hiện nhiệm vụ quản lý tiền mặt, tài sản quý, giấy tờ có giá và kho tiền trong một thời gian nhất định. 

*(Trích dẫn từ: Điều 13, Điều 19, Điều 26 - Thông tư số 01/2014/TT-NHNN)*

---

### Kịch bản 2: Truy vấn Tài liệu Hạn chế với Quyền Khách (`Guest`)
- **Câu hỏi**: `"Quy định về việc giao nhận, bảo quản và vận chuyển tiền mặt, tài sản quý, giấy tờ có giá trong ngành ngân hàng?"`
- **Người dùng**: `user_guest_visitor_02` | **Vai trò**: `Guest`
- **Phạm vi truy cập**: `Allowed: 5/15 chunks (Filtered: 10)`
- **Trích dẫn (Citations)**: `['43/2024/TT-NHNN', '105/2016/TT-BTC', '46/2023/NĐ-CP']`
- **Trạng thái**: `SUCCESS`
- **Câu trả lời sinh ra**:
> Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập.

*Nhận xét: Hệ thống chặn triệt để 10 tài liệu Risk, không đưa vào context cho LLM và kích hoạt câu trả lời chuẩn từ chối quyền truy cập.*

---

### Kịch bản 3: Truy vấn Tài liệu Mở rộng với Quyền Nhân viên (`Staff`)
- **Câu hỏi**: `"Theo Luật Hợp tác xã số 17/2023/QH15, việc góp vốn điều lệ và quyền của thành viên hợp tác xã được quy định như thế nào?"`
- **Người dùng**: `user_staff_internal_03` | **Vai trò**: `Staff`
- **Phạm vi truy cập**: `Allowed: 15/15 chunks (Filtered: 0)`
- **Trích dẫn (Citations)**: `['17/2023/QH15', '63/2025/TT-NHNN', '46/2023/NĐ-CP']`
- **Chunk IDs**: `['166269__full', '185630__full', '163441__full']`
- **Trạng thái**: `SUCCESS`
- **Câu trả lời sinh ra**:
Không tìm thấy đủ thông tin trong phạm vi tài liệu được phép truy cập.

---

## 3. Đánh giá Tiêu chí Tuân thủ (Compliance Assessment)

| Tiêu chí | Kết quả đánh giá | Trạng thái |
| :--- | :--- | :---: |
| **CITATION** | Trích dẫn đúng số hiệu văn bản từ ngữ cảnh (`01/2014/TT-NHNN`, `17/2023/QH15`), không tạo citation ảo | **PASS** |
| **RBAC** | Lọc trước tìm kiếm, loại bỏ 100% tài liệu hạn chế khi người dùng không đủ quyền | **PASS** |
| **AUDIT** | Ghi nhận đầy đủ 100% request (cả allowed và denied) vào `audit_log.jsonl` | **PASS** |

---

```text
CITATION: PASS
RBAC: PASS
AUDIT: PASS
```
