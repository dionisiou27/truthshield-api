import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class PublishQueue:
    """File-backed publish queue for auto-posts (mock processing)."""

    def __init__(self, path: str = "demo_data/publish_queue.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"items": []})

    def _read(self) -> Dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"items": []}

    def _write(self, obj: Dict) -> None:
        self.path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self) -> List[Dict]:
        return self._read().get("items", [])

    def enqueue(self, item: Dict) -> Dict:
        obj = self._read()
        entry = {
            "id": f"q_{int(datetime.utcnow().timestamp()*1000)}",
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "item": item,
        }
        obj["items"].append(entry)
        self._write(obj)
        return entry

    def mark_processed(self, entry_id: str, status: str = "posted") -> bool:
        obj = self._read()
        for e in obj.get("items", []):
            if e.get("id") == entry_id:
                e["status"] = status
                e["processed_at"] = datetime.utcnow().isoformat()
                self._write(obj)
                return True
        return False


