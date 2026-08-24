---
id: RR-010
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Sai lệch số liệu báo cáo quản trị

## Thông tin rủi ro

- name: Sai lệch số liệu báo cáo quản trị
- description: Dữ liệu nguồn không được đối chiếu
- category: Rui ro bao cao
- cause: Thay đổi dữ liệu không có kiểm soát
- event: Báo cáo quản trị có số liệu sai
- impact: Quyết định quản trị sai lệch
- inherent_level: Trung binh
- residual_level: Thap
- owner_unit_id: DV-FINANCE

## Kiểm soát liên quan

[[controls/KS-010-oi-chieu-du-lieu-nguon-truoc-khi-phat-hanh-bao-cao|Đối chiếu dữ liệu nguồn trước khi phát hành báo cáo]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: đối chiếu nguồn giảm sai lệch báo cáo
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-010-bao-cao-quan-tri-su-dung-du-lieu-nguon-chua-oi-chieu|Báo cáo quản trị sử dụng dữ liệu nguồn chưa đối chiếu]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện sai lệch báo cáo
- verification_status: `VERIFIED`
