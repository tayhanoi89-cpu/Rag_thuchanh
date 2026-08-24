"""Run Audit Trail Demonstration with 3 representative requests."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

# Set UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BUOI_17_ROOT = Path(__file__).resolve().parent.parent
BUOI_14_ROOT = BUOI_17_ROOT.parent / "buoi_14"

sys.path.insert(0, str(BUOI_17_ROOT))
sys.path.insert(0, str(BUOI_14_ROOT))

from scripts.audit_logger import AuditLogger
from scripts.secure_retrieval_adapter import SecureRetrievalAdapter, normalize_roles

def run_audit_demo():
    log_file = BUOI_17_ROOT / "outputs" / "audit_log.jsonl"
    
    # Reset log file for clean demonstration
    if log_file.exists():
        log_file.write_text("", encoding="utf-8")
        
    logger = AuditLogger(log_file)
    adapter = SecureRetrievalAdapter()
    
    print("=" * 60)
    print("BẮT ĐẦU CHẠY 3 REQUEST DEMO CHO AUDIT TRAIL")
    print("=" * 60)
    
    # -------------------------------------------------------------
    # Request 1: ALLOWED (Truy cập được phép)
    # -------------------------------------------------------------
    req1_user = "user_risk_001"
    req1_role = "Risk_Manager"
    req1_query = "Quy định về tỷ lệ an toàn vốn ngân hàng thương mại"
    print(f"\n[Demo 1 - ALLOWED] User: {req1_user} | Role: {req1_role}")
    print(f"Query: {req1_query}")
    
    res1 = adapter.retrieve(req1_query, user_roles=[req1_role], method="hybrid", top_k=3)
    stats1 = adapter.last_filter_stats
    
    event1 = logger.log_event(
        user_id_demo=req1_user,
        user_role=req1_role,
        action="POLICY_LOOKUP",
        query=req1_query,
        retrieval_method="hybrid",
        retrieved_document_ids=[r["document_id"] for r in res1],
        retrieved_chunk_ids=[r["chunk_id"] for r in res1],
        citation_ids=[r["citation"] for r in res1],
        rbac_filtered_count=stats1.get("filtered", 0),
        status="SUCCESS" if res1 else "DENIED",
    )
    print(f"Status: {event1['status']} | Retrieved chunks: {event1['retrieved_chunk_ids']} | RBAC Filtered: {event1['rbac_filtered_count']}")

    # -------------------------------------------------------------
    # Request 2: DENIED (Truy cập bị từ chối)
    # -------------------------------------------------------------
    req2_user = "user_unauthorized_999"
    req2_role = "External_Auditor_Unregistered"
    req2_query = "Báo cáo chi tiết danh mục rủi ro đặc biệt"
    print(f"\n[Demo 2 - DENIED] User: {req2_user} | Role: {req2_role}")
    print(f"Query: {req2_query}")
    
    # Role không hợp lệ -> Adapter kích hoạt Default Deny
    res2 = adapter.retrieve(req2_query, user_roles=[req2_role], method="hybrid", top_k=3)
    stats2 = adapter.last_filter_stats
    
    event2 = logger.log_event(
        user_id_demo=req2_user,
        user_role=req2_role,
        action="RESTRICTED_ACCESS_ATTEMPT",
        query=req2_query,
        retrieval_method="hybrid",
        retrieved_document_ids=[],
        retrieved_chunk_ids=[],
        citation_ids=[],
        rbac_filtered_count=stats2.get("filtered", len(adapter.rows)),
        status="DENIED",
        extra_metadata={"reason": "Role unregistered in system (Default Deny triggered)"}
    )
    print(f"Status: {event2['status']} | Retrieved chunks: {event2['retrieved_chunk_ids']} | RBAC Filtered: {event2['rbac_filtered_count']}")

    # -------------------------------------------------------------
    # Request 3: BÌNH THƯỜNG (Tra cứu nghiệp vụ thông thường)
    # -------------------------------------------------------------
    req3_user = "user_staff_102"
    req3_role = "Staff"
    req3_query = "Quy định về kinh doanh bảo hiểm và hợp tác xã"
    print(f"\n[Demo 3 - NORMAL / BÌNH THƯỜNG] User: {req3_user} | Role: {req3_role}")
    print(f"Query: {req3_query}")
    
    res3 = adapter.retrieve(req3_query, user_roles=[req3_role], method="hybrid", top_k=3)
    stats3 = adapter.last_filter_stats
    
    event3 = logger.log_event(
        user_id_demo=req3_user,
        user_role=req3_role,
        action="GENERAL_POLICY_QUERY",
        query=req3_query,
        retrieval_method="hybrid",
        retrieved_document_ids=[r["document_id"] for r in res3],
        retrieved_chunk_ids=[r["chunk_id"] for r in res3],
        citation_ids=[r["citation"] for r in res3],
        rbac_filtered_count=stats3.get("filtered", 0),
        status="SUCCESS",
    )
    print(f"Status: {event3['status']} | Retrieved chunks: {event3['retrieved_chunk_ids']} | RBAC Filtered: {event3['rbac_filtered_count']}")

    print("\n" + "=" * 60)
    print(f"Đã lưu toàn bộ audit trail vào: {log_file}")
    print("=" * 60)
    
    # Print content of jsonl
    all_logs = logger.read_all_logs()
    for idx, l in enumerate(all_logs, 1):
        print(f"\n--- AUDIT LOG RECORD #{idx} ---")
        print(json.dumps(l, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    run_audit_demo()
