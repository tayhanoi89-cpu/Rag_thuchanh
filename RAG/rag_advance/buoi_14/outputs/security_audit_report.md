# Buoi 15 Security Audit Report

- Audit time (UTC): 2026-08-17T12:23:44.508228+00:00
- Total test cases: 5
- PASS: 5
- FAIL: 0
- Neo4j connectivity: PASS (Neo4j connectivity verified)
- Retrieval method: BM25 over the role-filtered secure corpus
- Top-K: 5

## risk-license

- Query: `cấp giấy phép quỹ tín dụng nhân dân`
- Target sensitive document: `177271`
- Unauthorized roles: `Guest, HR_Manager`
- Authorized roles: `Risk_Officer`
- Unauthorized results inspected: 5
- Authorized target visibility: FOUND
- Status: **PASS**
- Evidence: No unauthorized result contained the target document.

## risk-safety-fund

- Query: `quỹ bảo đảm an toàn hệ thống quỹ tín dụng nhân dân`
- Target sensitive document: `168220`
- Unauthorized roles: `Guest`
- Authorized roles: `Admin`
- Unauthorized results inspected: 5
- Authorized target visibility: FOUND
- Status: **PASS**
- Evidence: No unauthorized result contained the target document.

## risk-reorganization

- Query: `tổ chức lại ngân hàng thương mại tổ chức tín dụng phi ngân hàng`
- Target sensitive document: `174218`
- Unauthorized roles: `Guest, HR_Manager`
- Authorized roles: `Risk_Officer`
- Unauthorized results inspected: 5
- Authorized target visibility: FOUND
- Status: **PASS**
- Evidence: No unauthorized result contained the target document.

## risk-capital-ratio

- Query: `tỷ lệ an toàn vốn ngân hàng chi nhánh ngân hàng nước ngoài`
- Target sensitive document: `117310`
- Unauthorized roles: `Guest`
- Authorized roles: `Employee`
- Unauthorized results inspected: 5
- Authorized target visibility: FOUND
- Status: **PASS**
- Evidence: No unauthorized result contained the target document.

## risk-amendment

- Query: `sửa đổi bổ sung thông tư quỹ tín dụng nhân dân`
- Target sensitive document: `185630`
- Unauthorized roles: `Guest, HR_Manager`
- Authorized roles: `Admin`
- Unauthorized results inspected: 5
- Authorized target visibility: FOUND
- Status: **PASS**
- Evidence: No unauthorized result contained the target document.

## Conclusion

**Basic data security certification: ACHIEVED**

The certification requires every unauthorized-role check to pass and Neo4j connectivity to be verified.
