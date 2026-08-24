---
id: RR-003
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Giải ngân thiếu hồ sơ bảo đảm

## Thông tin rủi ro

- name: Giải ngân thiếu hồ sơ bảo đảm
- description: Hồ sơ giải ngân chưa đủ điều kiện
- category: Rui ro tin dung
- cause: Kiểm tra điều kiện tiên quyết bị bỏ qua
- event: Giải ngân khi thiếu chứng từ bắt buộc
- impact: Khó thu hồi nợ và vi phạm quy trình
- inherent_level: Cao
- residual_level: Trung binh
- owner_unit_id: DV-CREDIT

## Kiểm soát liên quan

[[controls/KS-003-checklist-ieu-kien-giai-ngan-bat-buoc|Checklist điều kiện giải ngân bắt buộc]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: checklist ngăn giải ngân thiếu hồ sơ
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-003-giai-ngan-truoc-khi-hoan-thien-chung-tu-bao-am|Giải ngân trước khi hoàn thiện chứng từ bảo đảm]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện giải ngân thiếu hồ sơ
- verification_status: `VERIFIED`
