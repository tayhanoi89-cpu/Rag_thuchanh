---
id: RR-005
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Gián đoạn dịch vụ ngân hàng số

## Thông tin rủi ro

- name: Gián đoạn dịch vụ ngân hàng số
- description: Hệ thống thanh toán trực tuyến không sẵn sàng
- category: Rui ro cong nghe thong tin
- cause: Kế hoạch năng lực và dự phòng chưa đầy đủ
- event: Dịch vụ ngân hàng số bị gián đoạn
- impact: Mất doanh thu và khiếu nại khách hàng
- inherent_level: Cao
- residual_level: Trung binh
- owner_unit_id: DV-IT

## Kiểm soát liên quan

[[controls/KS-005-kiem-thu-kha-nang-chiu-tai-va-chuyen-oi-du-phong|Kiểm thử khả năng chịu tải và chuyển đổi dự phòng]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: kiểm thử dự phòng giảm gián đoạn dịch vụ
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-005-dich-vu-ngan-hang-so-gian-oan-trong-gio-cao-iem|Dịch vụ ngân hàng số gián đoạn trong giờ cao điểm]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện gián đoạn dịch vụ
- verification_status: `VERIFIED`
