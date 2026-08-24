import sys
import json
import io
from pathlib import Path
import pandas as pd

# Set UTF-8 encoding for stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

buoi_14_dir = Path(r'c:\Users\ngocngothi\Desktop\Rag_thuchanh\RAG\rag_advance\buoi_14')
sys.path.insert(0, str(buoi_14_dir))

from src.secure_retriever import SecureRetriever
from src.config import VALID_ROLES

corpus_path = buoi_14_dir / 'data' / 'processed' / 'chunks_secure.csv'
df = pd.read_csv(corpus_path)

print("=" * 60)
print("1. DANH SÁCH ROLES TRONG CORPUS")
print("=" * 60)
all_roles = set()
for r in df['allowed_roles']:
    parsed = json.loads(r)
    all_roles.update(parsed)
print("Unique roles in allowed_roles:", sorted(all_roles))
print("VALID_ROLES trong config:", sorted(VALID_ROLES))

print("\n" + "=" * 60)
print("2. SỐ LƯỢNG CHUNK THEO TỪNG ROLE")
print("=" * 60)
for role in sorted(all_roles):
    count = sum(1 for r in df['allowed_roles'] if role in json.loads(r))
    pct = count / len(df) * 100
    print(f"Role '{role}': {count}/{len(df)} chunks ({pct:.1f}%)")

print("\n" + "=" * 60)
print("3. CHUNKS CHO NHIỀU ROLES VS HẠN CHẾ QUYỀN")
print("=" * 60)
general_chunks = df[df['security_class'] == 'General']
risk_chunks = df[df['security_class'] == 'Risk']
print(f"- General (Tất cả 5 roles: Admin, HR_Manager, Risk_Officer, Employee, Guest): {len(general_chunks)} chunks")
for idx, row in general_chunks.iterrows():
    print(f"  + [{row['chunk_id']}] {row['citation_code']}: {row['title'][:70]}...")

print(f"\n- Risk (Hạn chế quyền - Chỉ Admin, Risk_Officer, Employee): {len(risk_chunks)} chunks")
for idx, row in risk_chunks.iterrows():
    print(f"  + [{row['chunk_id']}] {row['citation_code']}: {row['title'][:70]}...")

print("\n" + "=" * 60)
print("4. KIỂM TRA TÍNH ỔN ĐỊNH PARSE allowed_roles")
print("=" * 60)
parse_success = True
for idx, r in enumerate(df['allowed_roles']):
    try:
        val = json.loads(r)
        if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
            print(f"Row {idx} invalid structure: {r}")
            parse_success = False
    except Exception as e:
        print(f"Row {idx} parse error: {e}")
        parse_success = False
print(f"Toàn bộ {len(df)} chunks parse JSON ổn định 100%: {parse_success}")

print("\n" + "=" * 60)
print("5. KIỂM TRA UNKNOWN ROLE")
print("=" * 60)
retriever = SecureRetriever()
try:
    retriever.retrieve("tiền mặt", user_roles=["HackerRole"], method="hybrid")
    print("Unknown role test: Allowed (FAIL)")
except ValueError as e:
    print(f"Unknown role test: DEFAULT DENY with ValueError ('{e}') -> PASS")

print("\n" + "=" * 60)
print("6. CHẠY CÙNG 1 QUERY VỚI CÁC ROLES")
print("=" * 60)
query = "Quy định về an toàn vốn và quản lý tiền mặt"

role_aliases = {
    "Admin": ["Admin"],
    "HR": ["HR_Manager"],
    "Risk_Manager": ["Risk_Officer"],
    "Staff": ["Employee"],
    "Guest": ["Guest"]
}

for role_alias, mapped_roles in role_aliases.items():
    results = retriever.retrieve(query, user_roles=mapped_roles, method="hybrid", top_k=5)
    stats = retriever.last_filter_stats
    print(f"\n--- Vai trò: {role_alias} (mapped: {mapped_roles}) ---")
    print(f"Stats: Total={stats['total']}, Allowed={stats['allowed']}, Filtered={stats['filtered']}")
    print(f"Số kết quả trả về: {len(results)}")
    for res in results:
        print(f"  [Rank {res['rank']}] Doc: {res['document_id']} | Citation: {res['citation']} | Roles: {res['allowed_roles']}")
