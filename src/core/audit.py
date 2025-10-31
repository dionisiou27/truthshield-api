import json
from pathlib import Path
from typing import Dict
from datetime import datetime


class AuditLog:
    def __init__(self, path: str = "demo_data/audit_log.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def write(self, record: Dict) -> None:
        entry = {
            **record,
            "timestamp": datetime.utcnow().isoformat(),
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


