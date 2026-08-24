---
id: RR-008
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Định giá tài sản bảo đảm không chính xác

## Thông tin rủi ro

- name: Định giá tài sản bảo đảm không chính xác
- description: Dữ liệu định giá không độc lập hoặc hết hạn
- category: Rui ro tin dung
- cause: Thiếu rà soát lại giá trị tài sản
- event: Tài sản bảo đảm được định giá cao hơn thực tế
- impact: Tăng tổn thất khi xử lý nợ
- inherent_level: Cao
- residual_level: Trung binh
- owner_unit_id: DV-CREDIT

## Kiểm soát liên quan

[[controls/KS-008-ra-soat-oc-lap-inh-gia-tai-san-bao-am|Rà soát độc lập định giá tài sản bảo đảm]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: rà soát độc lập giảm sai định giá
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-008-ra-soat-phat-hien-gia-tri-tai-san-bao-am-a-het-hieu-luc|Rà soát phát hiện giá trị tài sản bảo đảm đã hết hiệu lực]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện sai định giá tài sản
- verification_status: `VERIFIED`
