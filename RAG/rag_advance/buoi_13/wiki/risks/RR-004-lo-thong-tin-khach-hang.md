---
id: RR-004
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Lộ thông tin khách hàng

## Thông tin rủi ro

- name: Lộ thông tin khách hàng
- description: Quyền truy cập dữ liệu không được kiểm soát phù hợp
- category: Rui ro cong nghe thong tin
- cause: Cấp quyền vượt nhu cầu công việc
- event: Dữ liệu khách hàng bị truy cập hoặc chia sẻ trái phép
- impact: Vi phạm bảo mật và tổn hại uy tín
- inherent_level: Cao
- residual_level: Trung binh
- owner_unit_id: DV-IT

## Kiểm soát liên quan

[[controls/KS-004-ra-soat-quyen-truy-cap-inh-ky|Rà soát quyền truy cập định kỳ]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: rà soát quyền hạn giảm lộ dữ liệu
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-004-tai-khoan-co-quyen-truy-cap-du-lieu-vuot-pham-vi-cong-viec|Tài khoản có quyền truy cập dữ liệu vượt phạm vi công việc]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện quyền truy cập quá mức
- verification_status: `VERIFIED`
