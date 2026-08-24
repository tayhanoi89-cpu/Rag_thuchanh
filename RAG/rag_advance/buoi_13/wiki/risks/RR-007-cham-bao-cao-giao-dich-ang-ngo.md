---
id: RR-007
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Chậm báo cáo giao dịch đáng ngờ

## Thông tin rủi ro

- name: Chậm báo cáo giao dịch đáng ngờ
- description: Theo dõi cảnh báo AML không kịp thời
- category: Rui ro tuan thu
- cause: Khối lượng cảnh báo vượt năng lực xử lý
- event: Báo cáo giao dịch đáng ngờ nộp muộn
- impact: Chế tài và rủi ro pháp lý
- inherent_level: Cao
- residual_level: Trung binh
- owner_unit_id: DV-COMPLIANCE

## Kiểm soát liên quan

[[controls/KS-007-theo-doi-sla-xu-ly-canh-bao-aml|Theo dõi SLA xử lý cảnh báo AML]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: theo dõi SLA giảm nguy cơ báo cáo muộn
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-007-bao-cao-giao-dich-ang-ngo-nop-qua-han-noi-bo|Báo cáo giao dịch đáng ngờ nộp quá hạn nội bộ]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện báo cáo AML muộn
- verification_status: `VERIFIED`
