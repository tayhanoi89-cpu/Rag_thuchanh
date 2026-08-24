# BÁO CÁO AI AUDIT CHECKLIST GENERATOR (UC4)
## Hệ thống Tự động Sinh Danh mục Kiểm toán Nội bộ Agribank

**Thời gian tạo báo cáo:** 2026-08-24 19:42:04  
**Tổng số mục kiểm tra (Checklist Items):** `7`  
**Trạng thái Review Guardrail:** `NEEDS_HUMAN_REVIEW` (100%)

---
### 1. Bảng Danh mục Checklist Kiểm toán Chi tiết

| Mã Mục | Miền Nghiệp vụ | Phạm vi Đơn vị | Câu hỏi Kiểm toán | Rủi ro Tiềm ẩn | Mức Rủi ro | Trích dẫn Văn bản Gốc (Citation) |
|---|---|---|---|---|---|---|
| `CHK_KHO_01` | **An toàn kho quỹ & Vận chuyển tiền** | Chi nhánh loại 1 | Ban Quản lý kho tiền Chi nhánh có đảm bảo đủ 3 thành viên theo quy định (Giám đốc/Phó Giám đốc ủy quyền, Kế toán trưởng/Phụ trách kế toán và Thủ kho tiền) và có mặt đầy đủ cả 3 thành viên trong mỗi lần mở cửa gian kho tiền hay không? | Nếu không đủ 3 thành viên khi mở cửa gian kho tiền hoặc có sự thông đồng, mở cửa kho không đúng quy định sẽ dẫn đến rủi ro mất an toàn tài sản kho tiền, thất thoát tài sản lớn và vi phạm nghiêm trọng quy chế quản lý kho quỹ. | <span style='color:red;'>🔴 <b>HIGH</b></span> | `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 30 | doc_agr_at01_04]: Ban Quản lý kho tiền tại mỗi chi nhánh Agribank bao gồm 3 thành viên bắt buộc: Giám đốc (hoặc Phó Giám đốc ủy quyền), Kế toán trưởng (hoặc Phụ trách kế toán) và Thủ kho tiền. Mọi lần mở cửa gian kho tiền phải có mặt đầy đủ 3 thành viên.` |
| `CHK_KHO_02` | **An toàn kho quỹ & Vận chuyển tiền** | Chi nhánh loại 1 | Các chuyến vận chuyển tiền mặt có giá trị từ 3 tỷ đồng trở lên hoặc tuyến đường di chuyển liên tỉnh tại Chi nhánh có tuân thủ đúng quy định về việc sử dụng xe ô tô bọc thép chuyên dùng, bố trí tối thiểu 02 bảo vệ chuyên trách có trang bị công cụ hỗ trợ và đảm bảo hạn mức không quá 50 tỷ đồng/chuyến không? | Vận chuyển tiền không đúng phương tiện bọc thép chuyên dùng, thiếu lực lượng bảo vệ hoặc vận chuyển vượt hạn mức cho phép sẽ làm tăng nguy cơ bị đe dọa an ninh, cướp tài sản trên đường vận chuyển, gây tổn thất tài sản đặc biệt lớn. | <span style='color:red;'>🔴 <b>HIGH</b></span> | `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 12 | doc_agr_at01_02]: Khi tiến hành vận chuyển tiền mặt có giá trị từ 3 tỷ đồng trở lên hoặc tuyến đường di chuyển liên tỉnh, Agribank bắt buộc bố trí xe ô tô bọc thép chuyên dùng và 02 bảo vệ chuyên trách trang bị công cụ hỗ trợ. Hạn mức vận chuyển không quá 50 tỷ đồng mỗi chuyến.` |
| `CHK_KHO_03` | **An toàn kho quỹ & Vận chuyển tiền** | Chi nhánh loại 1 | Chi nhánh có thực hiện công tác kiểm tra toàn diện, tổng kiểm kê kho quỹ định kỳ (thời điểm 0 giờ ngày 01/01 và 01/07 hàng năm) và thực hiện kiểm kê Quỹ tiền mặt vào cuối giờ làm việc hàng ngày đầy đủ, chính xác không? | Không kiểm kê định kỳ hoặc bỏ qua việc kiểm kê tồn quỹ cuối ngày dẫn đến rủi ro không kịp thời phát hiện chênh lệch thừa/thiếu tiền mặt, tạo sơ hở cho việc chiếm dụng tiền mặt hoặc làm sai lệch số liệu báo cáo kế toán kho quỹ. | <span style='color:orange;'>🟡 <b>MEDIUM</b></span> | `[01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 59. Định kỳ kiểm tra, kiểm kê | doc_44209_định_kỳ_kiểm_tra__kiểm_kê_59]: 1. Kiểm tra toàn diện công tác đảm bảo an toàn kho quỹ và tổng kiểm kê tiền mặt, tài sản quý, giấy tờ có giá mỗi năm 2 lần, thời điểm 0 giờ ngày 01 tháng 01 và ngày 01 tháng 7... 3. Kiểm kê tiền mặt thuộc Quỹ tiền mặt của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài, Quỹ nghiệp vụ phát hành của Sở Giao dịch, Ngân hàng Nhà nước chi nhánh, giấy tờ có giá, tài sản quý vào cuối giờ làm việc hàng ngày.` |
| `CHK_KHO_04` | **An toàn kho quỹ & Vận chuyển tiền** | Chi nhánh loại 1 | Cán bộ được giao quản lý chìa khóa kho tiền tại Chi nhánh có tuân thủ quy định bảo vệ an toàn chìa khóa, tuyệt đối không giao cho người khác cầm hộ và không mang chìa khóa kho tiền ra khỏi trụ sở làm việc hay không? | Mang chìa khóa kho tiền ra khỏi trụ sở làm việc hoặc giao cho người khác cất giữ hộ làm lộ bí mật an toàn kho tiền, tạo nguy cơ bị sao chép/đánh tráo chìa khóa, dẫn tới rủi ro kẻ gian xâm nhập kho tiền trái phép. | <span style='color:red;'>🔴 <b>HIGH</b></span> | `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 1 | doc_agr_at01_01]: Nghiêm cấm mọi hành vi mang chìa khóa kho tiền ra khỏi trụ sở làm việc. [01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN | Điều 35 | doc_44209_trách_nhiệm_của_cán_bộ_được_giao_nhiệm_vụ_quản_lý__sử_dụng_chìa_khóa_kho_tiền__két_sắt_35]: 1. Bảo đảm an toàn bí mật chìa khóa được giao, không làm thất lạc, mất mát, hư hỏng. Tuyệt đối không cho người khác xem, cầm, cất giữ hộ. 2. Không mang chìa khóa ra ngoài trụ sở cơ quan.` |
| `CHK_CNTT_01` | **Bảo mật CNTT & AI** | Khối CNTT | Hệ thống RAG và các ứng dụng AI tra cứu quy định có thực hiện mã hóa toàn bộ dữ liệu nhạy cảm lưu trữ (at-rest) bằng thuật toán AES-128/Fernet và tuân thủ cấp độ 3 An toàn thông tin hay không? | Rủi ro rò rỉ dữ liệu nhạy cảm của ngân hàng khi lưu trữ, bị khai thác lỗ hổng bảo mật, dẫn đến vi phạm pháp luật về an toàn thông tin và tổn thất uy tín nghiêm trọng. | <span style='color:red;'>🔴 <b>HIGH</b></span> | `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 9 | doc_agr_it07_01]` |
| `CHK_CNTT_02` | **Bảo mật CNTT & AI** | Khối CNTT | Nhật ký hệ thống (Audit Trail) của ứng dụng RAG Agribank có ghi lại đầy đủ các trường thông tin bắt buộc (timestamp, user_id, user_role, query, access decision, candidate filtered) và lưu đúng định dạng JSON Lines không? | Thiếu sót thông tin nhật ký hệ thống hoặc sai định dạng làm mất khả năng giám sát, không thể truy vết khi xảy ra sự cố an ninh mạng hoặc gian lận nội bộ. | <span style='color:red;'>🔴 <b>HIGH</b></span> | `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 16 | doc_agr_it07_02]` |
| `CHK_CNTT_03` | **Bảo mật CNTT & AI** | Khối CNTT | Khối CNTT có thiết lập cơ chế lưu trữ và bảo đảm thời gian lưu vết tệp log nhật ký hệ thống của ứng dụng RAG Agribank tối thiểu là 12 tháng hay không? | Nhật ký hệ thống bị xóa trước thời hạn dẫn đến thiếu bằng chứng phục vụ công tác thanh tra, kiểm tra, điều tra sự cố và không tuân thủ quy chế quản trị CNTT nội bộ. | <span style='color:orange;'>🟡 <b>MEDIUM</b></span> | `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 16 | doc_agr_it07_02]` |

---
### 2. Chi tiết Quy trình Kiểm tra & Kiến nghị Kiểm toán

#### [CHK_KHO_01] Ban Quản lý kho tiền Chi nhánh có đảm bảo đủ 3 thành viên theo quy định (Giám đốc/Phó Giám đốc ủy quyền, Kế toán trưởng/Phụ trách kế toán và Thủ kho tiền) và có mặt đầy đủ cả 3 thành viên trong mỗi lần mở cửa gian kho tiền hay không?
- **Miền / Đơn vị:** `An toàn kho quỹ & Vận chuyển tiền` - `Chi nhánh loại 1`
- **Rủi ro tiềm ẩn:** Nếu không đủ 3 thành viên khi mở cửa gian kho tiền hoặc có sự thông đồng, mở cửa kho không đúng quy định sẽ dẫn đến rủi ro mất an toàn tài sản kho tiền, thất thoát tài sản lớn và vi phạm nghiêm trọng quy chế quản lý kho quỹ.
- **Mức độ rủi ro:** `HIGH`
- **Trích dẫn căn cứ:** `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 30 | doc_agr_at01_04]: Ban Quản lý kho tiền tại mỗi chi nhánh Agribank bao gồm 3 thành viên bắt buộc: Giám đốc (hoặc Phó Giám đốc ủy quyền), Kế toán trưởng (hoặc Phụ trách kế toán) và Thủ kho tiền. Mọi lần mở cửa gian kho tiền phải có mặt đầy đủ 3 thành viên.`
- **Kiến nghị / Thủ tục kiểm tra:** Thủ tục kiểm toán thực địa: (1) Kiểm tra Quyết định thành lập Ban Quản lý kho tiền và văn bản ủy quyền (nếu có); (2) Đối chiếu Sổ đăng ký vào/ra kho tiền với dữ liệu camera giám sát tại khu vực cửa kho tiền trong các thời điểm mở cửa gian kho; (3) Kiến nghị Ban Giám đốc Chi nhánh nghiêm túc duy trì nguyên tắc có mặt đầy đủ cả 3 thành viên khi mở cửa gian kho.
- **Trạng thái phê duyệt:** `NEEDS_HUMAN_REVIEW`

#### [CHK_KHO_02] Các chuyến vận chuyển tiền mặt có giá trị từ 3 tỷ đồng trở lên hoặc tuyến đường di chuyển liên tỉnh tại Chi nhánh có tuân thủ đúng quy định về việc sử dụng xe ô tô bọc thép chuyên dùng, bố trí tối thiểu 02 bảo vệ chuyên trách có trang bị công cụ hỗ trợ và đảm bảo hạn mức không quá 50 tỷ đồng/chuyến không?
- **Miền / Đơn vị:** `An toàn kho quỹ & Vận chuyển tiền` - `Chi nhánh loại 1`
- **Rủi ro tiềm ẩn:** Vận chuyển tiền không đúng phương tiện bọc thép chuyên dùng, thiếu lực lượng bảo vệ hoặc vận chuyển vượt hạn mức cho phép sẽ làm tăng nguy cơ bị đe dọa an ninh, cướp tài sản trên đường vận chuyển, gây tổn thất tài sản đặc biệt lớn.
- **Mức độ rủi ro:** `HIGH`
- **Trích dẫn căn cứ:** `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 12 | doc_agr_at01_02]: Khi tiến hành vận chuyển tiền mặt có giá trị từ 3 tỷ đồng trở lên hoặc tuyến đường di chuyển liên tỉnh, Agribank bắt buộc bố trí xe ô tô bọc thép chuyên dùng và 02 bảo vệ chuyên trách trang bị công cụ hỗ trợ. Hạn mức vận chuyển không quá 50 tỷ đồng mỗi chuyến.`
- **Kiến nghị / Thủ tục kiểm tra:** Thủ tục kiểm toán thực địa: (1) Kiểm tra Bảng kê/Lệnh điều chuyển tiền, Giấy ủy quyền vận chuyển và Nhật ký điều xe ô tô chuyên dùng đối với các chuyến vận chuyển liên tỉnh hoặc từ 3 tỷ đồng trở lên; (2) Kiểm tra danh sách phân công lực lượng áp tải, bảo vệ và sổ giao nhận công cụ hỗ trợ; (3) Khuyến nghị Chi nhánh tuyệt đối chấp hành quy định về phương tiện, nhân lực bảo vệ và hạn mức vận chuyển tối đa 50 tỷ đồng/chuyến.
- **Trạng thái phê duyệt:** `NEEDS_HUMAN_REVIEW`

#### [CHK_KHO_03] Chi nhánh có thực hiện công tác kiểm tra toàn diện, tổng kiểm kê kho quỹ định kỳ (thời điểm 0 giờ ngày 01/01 và 01/07 hàng năm) và thực hiện kiểm kê Quỹ tiền mặt vào cuối giờ làm việc hàng ngày đầy đủ, chính xác không?
- **Miền / Đơn vị:** `An toàn kho quỹ & Vận chuyển tiền` - `Chi nhánh loại 1`
- **Rủi ro tiềm ẩn:** Không kiểm kê định kỳ hoặc bỏ qua việc kiểm kê tồn quỹ cuối ngày dẫn đến rủi ro không kịp thời phát hiện chênh lệch thừa/thiếu tiền mặt, tạo sơ hở cho việc chiếm dụng tiền mặt hoặc làm sai lệch số liệu báo cáo kế toán kho quỹ.
- **Mức độ rủi ro:** `MEDIUM`
- **Trích dẫn căn cứ:** `[01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN Quy định về giao nhận, bảo quản, vận chuyển tiền mặt, tài sản quý, giấy tờ có giá | Điều 59. Định kỳ kiểm tra, kiểm kê | doc_44209_định_kỳ_kiểm_tra__kiểm_kê_59]: 1. Kiểm tra toàn diện công tác đảm bảo an toàn kho quỹ và tổng kiểm kê tiền mặt, tài sản quý, giấy tờ có giá mỗi năm 2 lần, thời điểm 0 giờ ngày 01 tháng 01 và ngày 01 tháng 7... 3. Kiểm kê tiền mặt thuộc Quỹ tiền mặt của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài, Quỹ nghiệp vụ phát hành của Sở Giao dịch, Ngân hàng Nhà nước chi nhánh, giấy tờ có giá, tài sản quý vào cuối giờ làm việc hàng ngày.`
- **Kiến nghị / Thủ tục kiểm tra:** Thủ tục kiểm toán thực địa: (1) Kiểm tra các Biên bản tổng kiểm kê định kỳ thời điểm 0h ngày 01/01 và 01/07; (2) Lấy mẫu đối chiếu Biên bản kiểm kê Quỹ tiền mặt cuối ngày với Sổ quỹ và Sổ kế toán tài khoản tiền mặt tại quỹ; (3) Khuyến nghị Chi nhánh lập đầy đủ hồ sơ kiểm kê có chữ ký xác nhận của Ban Giám đốc, Kế toán trưởng và Thủ quỹ/Thủ kho đúng thời gian quy định.
- **Trạng thái phê duyệt:** `NEEDS_HUMAN_REVIEW`

#### [CHK_KHO_04] Cán bộ được giao quản lý chìa khóa kho tiền tại Chi nhánh có tuân thủ quy định bảo vệ an toàn chìa khóa, tuyệt đối không giao cho người khác cầm hộ và không mang chìa khóa kho tiền ra khỏi trụ sở làm việc hay không?
- **Miền / Đơn vị:** `An toàn kho quỹ & Vận chuyển tiền` - `Chi nhánh loại 1`
- **Rủi ro tiềm ẩn:** Mang chìa khóa kho tiền ra khỏi trụ sở làm việc hoặc giao cho người khác cất giữ hộ làm lộ bí mật an toàn kho tiền, tạo nguy cơ bị sao chép/đánh tráo chìa khóa, dẫn tới rủi ro kẻ gian xâm nhập kho tiền trái phép.
- **Mức độ rủi ro:** `HIGH`
- **Trích dẫn căn cứ:** `[100/QĐ-NHNO-AT - Quy định nội bộ số 100/QĐ-NHNO-AT | Điều 1 | doc_agr_at01_01]: Nghiêm cấm mọi hành vi mang chìa khóa kho tiền ra khỏi trụ sở làm việc. [01/2014/TT-NHNN - Thông tư số 01/2014/TT-NHNN | Điều 35 | doc_44209_trách_nhiệm_của_cán_bộ_được_giao_nhiệm_vụ_quản_lý__sử_dụng_chìa_khóa_kho_tiền__két_sắt_35]: 1. Bảo đảm an toàn bí mật chìa khóa được giao, không làm thất lạc, mất mát, hư hỏng. Tuyệt đối không cho người khác xem, cầm, cất giữ hộ. 2. Không mang chìa khóa ra ngoài trụ sở cơ quan.`
- **Kiến nghị / Thủ tục kiểm tra:** Thủ tục kiểm toán thực địa: (1) Kiểm tra thực tế nơi bảo quản chìa khóa hàng ngày (két sắt riêng tại phòng làm việc trong trụ sở) của từng thành viên giữ chìa khóa; (2) Phỏng vấn cán bộ và kiểm tra nhật ký bàn giao chìa khóa (nếu có); (3) Yêu cầu Ban Giám đốc Chi nhánh quán triệt thực hiện nghiêm lệnh cấm mang chìa khóa kho tiền ra khỏi trụ sở.
- **Trạng thái phê duyệt:** `NEEDS_HUMAN_REVIEW`

#### [CHK_CNTT_01] Hệ thống RAG và các ứng dụng AI tra cứu quy định có thực hiện mã hóa toàn bộ dữ liệu nhạy cảm lưu trữ (at-rest) bằng thuật toán AES-128/Fernet và tuân thủ cấp độ 3 An toàn thông tin hay không?
- **Miền / Đơn vị:** `Bảo mật CNTT & AI` - `Khối CNTT`
- **Rủi ro tiềm ẩn:** Rủi ro rò rỉ dữ liệu nhạy cảm của ngân hàng khi lưu trữ, bị khai thác lỗ hổng bảo mật, dẫn đến vi phạm pháp luật về an toàn thông tin và tổn thất uy tín nghiêm trọng.
- **Mức độ rủi ro:** `HIGH`
- **Trích dẫn căn cứ:** `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 9 | doc_agr_it07_01]`
- **Kiến nghị / Thủ tục kiểm tra:** Thực hiện kiểm tra cấu hình mã hóa cơ sở dữ liệu/vector database; rà soát mã nguồn (code review) cơ chế mã hóa at-rest; trích xuất mẫu dữ liệu lưu trữ thực tế để xác nhận dữ liệu nhạy cảm đã được mã hóa chuẩn AES-128/Fernet.
- **Trạng thái phê duyệt:** `NEEDS_HUMAN_REVIEW`

#### [CHK_CNTT_02] Nhật ký hệ thống (Audit Trail) của ứng dụng RAG Agribank có ghi lại đầy đủ các trường thông tin bắt buộc (timestamp, user_id, user_role, query, access decision, candidate filtered) và lưu đúng định dạng JSON Lines không?
- **Miền / Đơn vị:** `Bảo mật CNTT & AI` - `Khối CNTT`
- **Rủi ro tiềm ẩn:** Thiếu sót thông tin nhật ký hệ thống hoặc sai định dạng làm mất khả năng giám sát, không thể truy vết khi xảy ra sự cố an ninh mạng hoặc gian lận nội bộ.
- **Mức độ rủi ro:** `HIGH`
- **Trích dẫn căn cứ:** `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 16 | doc_agr_it07_02]`
- **Kiến nghị / Thủ tục kiểm tra:** Kiểm tra mẫu (sample check) các tệp log vận hành thực tế của ứng dụng RAG trên môi trường Production; đối soát định dạng file (.jsonl) và kiểm tra tính đầy đủ của 6 trường dữ liệu bắt buộc theo quy định.
- **Trạng thái phê duyệt:** `NEEDS_HUMAN_REVIEW`

#### [CHK_CNTT_03] Khối CNTT có thiết lập cơ chế lưu trữ và bảo đảm thời gian lưu vết tệp log nhật ký hệ thống của ứng dụng RAG Agribank tối thiểu là 12 tháng hay không?
- **Miền / Đơn vị:** `Bảo mật CNTT & AI` - `Khối CNTT`
- **Rủi ro tiềm ẩn:** Nhật ký hệ thống bị xóa trước thời hạn dẫn đến thiếu bằng chứng phục vụ công tác thanh tra, kiểm tra, điều tra sự cố và không tuân thủ quy chế quản trị CNTT nội bộ.
- **Mức độ rủi ro:** `MEDIUM`
- **Trích dẫn căn cứ:** `[600/QC-NHNO-CNTT - Quy chế bảo mật CNTT số 600/QC-NHNO-CNTT | Điều 16 | doc_agr_it07_02]`
- **Kiến nghị / Thủ tục kiểm tra:** Rà soát cấu hình thời gian lưu trữ (Retention Policy) trên hệ thống Log Management/SIEM hoặc hạ tầng lưu trữ log; kiểm tra thực tế sự tồn tại của dữ liệu log từ 12 tháng trước đó.
- **Trạng thái phê duyệt:** `NEEDS_HUMAN_REVIEW`

---
### 3. Kết luận & Nghiệm thu Core Engine UC4

```plaintext
CHECKLIST GENERATOR ENGINE: PASS
CHECKLIST ITEMS GENERATED: 7
CITATIONS ATTACHED: YES
```