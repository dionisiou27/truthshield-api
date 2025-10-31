import json
import os
from typing import Dict
from hashlib import sha256
from datetime import datetime
from pathlib import Path


class EvidenceArchiver:
    """
    Stores snapshots of routed items with a SHA-256 content hash for audit.
    Writes JSON files to demo_data/evidence/ by default.
    """

    def __init__(self, base_dir: str = "demo_data/evidence") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def archive(self, item: Dict, decision: str, provenance: Dict = None) -> Dict:
        timestamp = datetime.utcnow().isoformat()
        payload = {
            "timestamp": timestamp,
            "decision": decision,
            "item": item,
            "provenance": provenance or {},
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        content_hash = sha256(raw).hexdigest()
        filename = f"{timestamp.replace(':','-').replace('.','-')}_{content_hash[:12]}.json"
        path = self.base_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({**payload, "sha256": content_hash}, ensure_ascii=False, indent=2))
        return {"sha256": content_hash, "path": str(path)}


