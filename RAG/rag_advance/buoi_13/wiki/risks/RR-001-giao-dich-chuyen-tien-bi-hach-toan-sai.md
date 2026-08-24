---
id: RR-001
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Giao dịch chuyển tiền bị hạch toán sai

## Thông tin rủi ro

- name: Giao dịch chuyển tiền bị hạch toán sai
- description: Đối soát giao dịch cuối ngày không đầy đủ
- category: Rui ro van hanh
- cause: Thiếu đối chiếu giữa hệ thống thanh toán và sổ cái
- event: Giao dịch được ghi nhận sai trạng thái
- impact: Tổn thất tài chính và khiếu nại khách hàng
- inherent_level: Cao
- residual_level: Trung binh
- owner_unit_id: DV-OPS

## Kiểm soát liên quan

[[controls/KS-001-oi-soat-tu-ong-giao-dich-va-so-cai|Đối soát tự động giao dịch và sổ cái]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: đối soát tự động giảm nguy cơ hạch toán sai
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-001-sai-lech-trang-thai-giao-dich-uoc-phat-hien-khi-oi-soat-cuoi-ngay|Sai lệch trạng thái giao dịch được phát hiện khi đối soát cuối ngày]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện đối soát giao dịch
- verification_status: `VERIFIED`
