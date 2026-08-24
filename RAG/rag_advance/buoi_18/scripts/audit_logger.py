import os
import sys
import json
import time
import uuid
import re
from datetime import datetime

class AuditLogger:
    def __init__(self, log_dir="outputs", log_file="audit_trail.jsonl"):
        self.log_dir = log_dir
        self.log_path = os.path.join(log_dir, log_file)
        os.makedirs(log_dir, exist_ok=True)
        
    @staticmethod
    def sanitize(text: str) -> str:
        """Sanitize sensitive data such as API keys, tokens, and secrets."""
        if not isinstance(text, str):
            return text
        # Redact common API key patterns
        text = re.sub(r'(GEMINI_API_KEY|LLM_API_KEY|HF_TOKEN|API_KEY|token|secret)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1: [REDACTED]', text, flags=re.IGNORECASE)
        text = re.sub(r'AQ\.[A-Za-z0-9_\-]{20,}', '[REDACTED_API_KEY]', text)
        text = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED_API_KEY]', text)
        text = re.sub(r'hf_[A-Za-z0-9]{30,}', '[REDACTED_HF_TOKEN]', text)
        return text

    def log_action(self, user_id: str, user_role: str, action: str, domain: str = "General",
                   request_id: str = None, status: str = "SUCCESS", details: dict = None) -> dict:
        """Log an audit event with timestamps and sanitized metadata."""
        if not request_id:
            request_id = str(uuid.uuid4())[:8]
            
        timestamp = datetime.now().isoformat()
        
        # Sanitize details
        sanitized_details = {}
        if details:
            for k, v in details.items():
                if isinstance(v, str):
                    sanitized_details[k] = self.sanitize(v)
                elif isinstance(v, dict):
                    sanitized_details[k] = {ik: self.sanitize(iv) if isinstance(iv, str) else iv for ik, iv in v.items()}
                else:
                    sanitized_details[k] = v
                    
        log_entry = {
            "timestamp": timestamp,
            "request_id": request_id,
            "user_id": user_id,
            "user_role": user_role,
            "action": action,
            "domain": domain,
            "status": status,
            "details": sanitized_details
        }
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[AuditLogger Error] Failed to write log: {e}", file=sys.stderr)
            
        return log_entry

    def get_logs(self, role: str = None, action: str = None, limit: int = 100) -> list:
        """Retrieve audit log entries with optional filters."""
        if not os.path.exists(self.log_path):
            return []
        
        entries = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if role and entry.get("user_role") != role and role != "Admin":
                            continue
                        if action and entry.get("action") != action:
                            continue
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[AuditLogger Error] Failed to read logs: {e}", file=sys.stderr)
            
        return entries[-limit:]
