---
id: RR-006
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Gian lận giả mạo yêu cầu chuyển tiền

## Thông tin rủi ro

- name: Gian lận giả mạo yêu cầu chuyển tiền
- description: Nhận diện và xác thực yêu cầu chưa đủ mạnh
- category: Rui ro gian lan
- cause: Nhân viên không xác minh kênh liên lạc
- event: Yêu cầu chuyển tiền giả mạo được xử lý
- impact: Tổn thất tài chính
- inherent_level: Cao
- residual_level: Trung binh
- owner_unit_id: DV-OPS

## Kiểm soát liên quan

[[controls/KS-006-xac-thuc-hai-kenh-voi-lenh-chuyen-tien-ngoai-le|Xác thực hai kênh với lệnh chuyển tiền ngoại lệ]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: xác thực hai kênh giảm gian lận chuyển tiền
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-006-yeu-cau-chuyen-tien-gia-mao-uoc-xu-ly-truoc-khi-bi-thu-hoi|Yêu cầu chuyển tiền giả mạo được xử lý trước khi bị thu hồi]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện giả mạo chuyển tiền
- verification_status: `VERIFIED`
