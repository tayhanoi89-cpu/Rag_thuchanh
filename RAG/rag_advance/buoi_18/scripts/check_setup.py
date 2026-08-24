import os
import sys
import pandas as pd
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

load_dotenv(".env")

print("=== 1. KIỂM TRA PYTHON & MÔI TRƯỜNG ===")
print(f"Python Version: {sys.version}")
print(f"Python Executable: {sys.executable}")
print(f"Working Directory: {os.getcwd()}")

print("\n=== 2. KIỂM TRA CÁC THƯ MỤC CẦN THIẾT ===")
for folder in ["data", "scripts", "outputs"]:
    exists = os.path.isdir(folder)
    print(f"- Thư mục '{folder}/': {'✅ SẴN SÀNG' if exists else '❌ CHƯA CÓ'}")

print("\n=== 3. KIỂM TRA FILE data/agribank_internal_policies.csv ===")
csv_internal = "data/agribank_internal_policies.csv"
internal_ready = False
if os.path.exists(csv_internal):
    df_internal = pd.read_csv(csv_internal)
    print(f"- Số dòng (records): {len(df_internal)}")
    print(f"- Số lượng cột: {len(df_internal.columns)} cột")
    print(f"- Danh sách các cột: {list(df_internal.columns)}")
    
    # 14 metadata columns check
    expected_cols = [
        "chunk_id", "doc_id", "doc_type", "so_ky_hieu", "title",
        "effective_date", "expiration_date", "status", "domain",
        "chapter", "article", "unit", "allowed_roles", "content"
    ]
    matched = [col for col in expected_cols if col in df_internal.columns]
    print(f"- Khớp {len(matched)}/{len(expected_cols)} cột metadata chuẩn.")
    if len(df_internal) > 0 and len(df_internal.columns) >= 14:
        internal_ready = True
        print("=> Trạng thái data/agribank_internal_policies.csv: ✅ HỢP LỆ")
    else:
        print("=> Trạng thái data/agribank_internal_policies.csv: ⚠️ Cần kiểm tra lại cấu trúc")
else:
    print(f"- ❌ Không tìm thấy {csv_internal}")

print("\n=== 4. KIỂM TRA FILE data/chunks_combined_secure.csv ===")
csv_combined = "data/chunks_combined_secure.csv"
combined_ready = False
if os.path.exists(csv_combined):
    df_combined = pd.read_csv(csv_combined)
    print(f"- Tổng số chunks: {len(df_combined)}")
    print(f"- Các cột: {list(df_combined.columns)}")
    
    if "doc_type" in df_combined.columns:
        counts = df_combined["doc_type"].value_counts().to_dict()
        print(f"- Phân loại doc_type: {counts}")
        print(f"  + Số chunks Pháp lý (legal / law): {counts.get('legal', 0) + counts.get('law', 0) + counts.get('phap_ly', 0)}")
        print(f"  + Số chunks Nội bộ (internal / quy_dinh_noi_bo): {counts.get('internal', 0) + counts.get('quy_dinh_noi_bo', 0) + counts.get('policy', 0)}")
    
    if "so_ky_hieu" in df_combined.columns:
        print(f"- Số văn bản duy nhất (so_ky_hieu unique): {df_combined['so_ky_hieu'].nunique()}")
        
    if len(df_combined) > 0:
        combined_ready = True
        print("=> Trạng thái data/chunks_combined_secure.csv: ✅ HỢP LỆ")
else:
    print(f"- ❌ Không tìm thấy {csv_combined}")

print("\n=== 5. KIỂM TRA .ENV & API KEY ===")
gemini_key = os.getenv("GEMINI_API_KEY", "")
llm_key = os.getenv("LLM_API_KEY", "")
llm_model = os.getenv("LLM_MODEL", "")

has_gemini = bool(gemini_key and len(gemini_key) > 10 and not gemini_key.startswith("your_"))
has_llm = bool(llm_key and len(llm_key) > 10 and not llm_key.startswith("your_"))

print(f"- GEMINI_API_KEY: {'✅ Đã cấu hình' if has_gemini else '❌ Chưa có / Không hợp lệ'}")
print(f"- LLM_API_KEY: {'✅ Đã cấu hình' if has_llm else '❌ Chưa có / Không hợp lệ'}")
print(f"- LLM_MODEL: {llm_model if llm_model else 'Chưa đặt'}")

# Test Google GenAI / Gemini call if key exists
llm_test_ok = False
if has_gemini or has_llm:
    api_key = gemini_key if has_gemini else llm_key
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=llm_model if llm_model else "gemini-2.5-flash",
            contents="Say hello in 3 words"
        )
        print(f"- Test gọi Gemini API: ✅ Thành công (Phản hồi: '{response.text.strip()}')")
        llm_test_ok = True
    except Exception as e:
        print(f"- Test gọi Gemini API: ⚠️ Gặp lỗi: {e}")
        # Try fallback or google.generativeai
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            model_inst = genai_legacy.GenerativeModel(llm_model if llm_model else "gemini-1.5-flash")
            resp = model_inst.generate_content("Say hello in 3 words")
            print(f"- Test gọi Gemini API (Legacy SDK): ✅ Thành công (Phản hồi: '{resp.text.strip()}')")
            llm_test_ok = True
        except Exception as e2:
            print(f"- Test gọi Legacy SDK: ⚠️ Gặp lỗi: {e2}")

env_ready = bool((has_gemini or has_llm) and os.path.isdir("data") and os.path.isdir("scripts") and os.path.isdir("outputs"))

print("\n" + "="*40)
print(f"ENVIRONMENT READY: {'YES' if env_ready else 'NO'}")
print(f"INTERNAL DATA READY: {'YES' if internal_ready else 'NO'}")
print(f"COMBINED DATA READY: {'YES' if combined_ready else 'NO'}")
print("="*40)
