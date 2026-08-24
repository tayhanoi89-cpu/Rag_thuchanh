---
id: RR-009
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Không phát hiện giao dịch bất thường

## Thông tin rủi ro

- name: Không phát hiện giao dịch bất thường
- description: Luật phát hiện gian lận không được cập nhật
- category: Rui ro gian lan
- cause: Ngưỡng cảnh báo không phù hợp
- event: Giao dịch nghi ngờ không bị chặn kịp thời
- impact: Tổn thất tài chính và uy tín
- inherent_level: Cao
- residual_level: Trung binh
- owner_unit_id: DV-OPS

## Kiểm soát liên quan

[[controls/KS-009-hieu-chinh-luat-phat-hien-giao-dich-gian-lan|Hiệu chỉnh luật phát hiện giao dịch gian lận]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: hiệu chỉnh luật giảm bỏ sót giao dịch bất thường
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-009-giao-dich-bat-thuong-chi-bi-phat-hien-sau-khi-khach-hang-khieu-nai|Giao dịch bất thường chỉ bị phát hiện sau khi khách hàng khiếu nại]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện không phát hiện bất thường
- verification_status: `VERIFIED`
