---
id: RR-002
type: RuiRo
verification_status: VERIFIED
data_origin: SYNTHETIC
---

# Phê duyệt tín dụng vượt thẩm quyền

## Thông tin rủi ro

- name: Phê duyệt tín dụng vượt thẩm quyền
- description: Kiểm tra hạn mức phê duyệt không hiệu lực
- category: Rui ro tin dung
- cause: Phân quyền trên hệ thống không cập nhật
- event: Khoản vay được phê duyệt vượt thẩm quyền
- impact: Tăng nợ xấu và vi phạm quy định
- inherent_level: Cao
- residual_level: Trung binh
- owner_unit_id: DV-CREDIT

## Kiểm soát liên quan

[[controls/KS-002-kiem-tra-han-muc-phe-duyet-tren-he-thong|Kiểm tra hạn mức phê duyệt trên hệ thống]]
- relationship_type: `MITIGATES`
- evidence_quote: Dữ liệu mô phỏng: kiểm tra hạn mức ngăn phê duyệt vượt thẩm quyền
- verification_status: `VERIFIED`


## Sự kiện liên quan

[[events/SK-002-ho-so-tin-dung-uoc-phe-duyet-vuot-han-muc-cua-nguoi-phe-duyet|Hồ sơ tín dụng được phê duyệt vượt hạn mức của người phê duyệt]]
- relationship_type: `OBSERVED_AS`
- evidence_quote: Dữ liệu mô phỏng: sự kiện vượt thẩm quyền
- verification_status: `VERIFIED`
