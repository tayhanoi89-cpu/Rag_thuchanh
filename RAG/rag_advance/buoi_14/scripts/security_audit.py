"""Run automated leakage checks against the Buoi 15 secure retriever."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from neo4j import GraphDatabase


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_neo4j_config, validate_roles
from src.secure_retriever import SecureRetriever


REPORT_PATH = PROJECT_ROOT / "outputs" / "security_audit_report.md"
TOP_K = 5


@dataclass(frozen=True)
class SecurityTestCase:
    name: str
    query: str
    target_sensitive_document_id: str
    unauthorized_roles: tuple[str, ...]
    authorized_roles: tuple[str, ...]


TEST_CASES = (
    SecurityTestCase(
        "risk-license",
        "cấp giấy phép quỹ tín dụng nhân dân",
        "177271",
        ("Guest", "HR_Manager"),
        ("Risk_Officer",),
    ),
    SecurityTestCase(
        "risk-safety-fund",
        "quỹ bảo đảm an toàn hệ thống quỹ tín dụng nhân dân",
        "168220",
        ("Guest",),
        ("Admin",),
    ),
    SecurityTestCase(
        "risk-reorganization",
        "tổ chức lại ngân hàng thương mại tổ chức tín dụng phi ngân hàng",
        "174218",
        ("Guest", "HR_Manager"),
        ("Risk_Officer",),
    ),
    SecurityTestCase(
        "risk-capital-ratio",
        "tỷ lệ an toàn vốn ngân hàng chi nhánh ngân hàng nước ngoài",
        "117310",
        ("Guest",),
        ("Employee",),
    ),
    SecurityTestCase(
        "risk-amendment",
        "sửa đổi bổ sung thông tư quỹ tín dụng nhân dân",
        "185630",
        ("Guest", "HR_Manager"),
        ("Admin",),
    ),
)


def validate_test_cases() -> None:
    for case in TEST_CASES:
        validate_roles(case.unauthorized_roles)
        validate_roles(case.authorized_roles)
        if set(case.unauthorized_roles).intersection(case.authorized_roles):
            raise ValueError(f"Overlapping roles in test case: {case.name}")


def check_database() -> tuple[bool, str]:
    try:
        config = get_neo4j_config()
        with GraphDatabase.driver(config["uri"], auth=(config["user"], config["password"])) as driver:
            driver.verify_connectivity()
        return True, "Neo4j connectivity verified"
    except Exception as error:
        return False, f"{type(error).__name__}: {error}"


def run_case(retriever: SecureRetriever, case: SecurityTestCase) -> dict[str, object]:
    unauthorized_results = retriever.retrieve(
        case.query,
        list(case.unauthorized_roles),
        method="bm25",
        top_k=TOP_K,
    )
    leaked_results = [
        row for row in unauthorized_results
        if row["document_id"] == case.target_sensitive_document_id
    ]

    authorized_results = retriever.retrieve(
        case.query,
        list(case.authorized_roles),
        method="bm25",
        top_k=TOP_K,
    )
    authorized_hits = [
        row for row in authorized_results
        if row["document_id"] == case.target_sensitive_document_id
    ]
    return {
        "case": case,
        "unauthorized_count": len(unauthorized_results),
        "leaked_results": leaked_results,
        "authorized_found": bool(authorized_hits),
        "authorized_count": len(authorized_results),
        "status": "PASS" if not leaked_results else "FAIL",
    }


def report_text(results: list[dict[str, object]], database_ok: bool, database_message: str) -> str:
    passed = sum(result["status"] == "PASS" for result in results)
    failed = len(results) - passed
    lines = [
        "# Buoi 15 Security Audit Report",
        "",
        f"- Audit time (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Total test cases: {len(results)}",
        f"- PASS: {passed}",
        f"- FAIL: {failed}",
        f"- Neo4j connectivity: {'PASS' if database_ok else 'FAIL'} ({database_message})",
        "- Retrieval method: BM25 over the role-filtered secure corpus",
        f"- Top-K: {TOP_K}",
        "",
    ]
    for result in results:
        case = result["case"]
        lines.extend(
            [
                f"## {case.name}",
                "",
                f"- Query: `{case.query}`",
                f"- Target sensitive document: `{case.target_sensitive_document_id}`",
                f"- Unauthorized roles: `{', '.join(case.unauthorized_roles)}`",
                f"- Authorized roles: `{', '.join(case.authorized_roles)}`",
                f"- Unauthorized results inspected: {result['unauthorized_count']}",
                f"- Authorized target visibility: {'FOUND' if result['authorized_found'] else 'NOT FOUND (not treated as a failure)'}",
                f"- Status: **{result['status']}**",
            ]
        )
        if result["leaked_results"]:
            lines.append("- Evidence: **DATA LEAKAGE - unauthorized results contained the target document.**")
        else:
            lines.append("- Evidence: No unauthorized result contained the target document.")
        lines.append("")

    certified = failed == 0 and database_ok
    lines.extend(
        [
            "## Conclusion",
            "",
            f"**Basic data security certification: {'ACHIEVED' if certified else 'NOT ACHIEVED'}**",
            "",
            "The certification requires every unauthorized-role check to pass and Neo4j connectivity to be verified.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    validate_test_cases()
    database_ok, database_message = check_database()
    retriever = SecureRetriever()
    results = [run_case(retriever, case) for case in TEST_CASES]
    report = report_text(results, database_ok, database_message)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")

    passed = sum(result["status"] == "PASS" for result in results)
    print("SECURITY AUDIT COMPLETE")
    print(f"test_cases: {len(results)}")
    print(f"pass: {passed}")
    print(f"fail: {len(results) - passed}")
    print(f"neo4j: {'PASS' if database_ok else 'FAIL'}")
    print(f"report: {args.report}")
    return 0 if passed == len(results) and database_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())