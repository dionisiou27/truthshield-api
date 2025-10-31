import json
from pathlib import Path
from typing import Dict, List, Optional


class WatchlistStore:
    """File-backed watchlists with custom ROI thresholds per client."""

    def __init__(self, path: str = "demo_data/watchlists.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({})

    def _read(self) -> Dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write(self, obj: Dict) -> None:
        self.path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self) -> Dict:
        return self._read()

    def upsert(self, client: str, data: Dict) -> Dict:
        client = (client or "").strip().lower()
        obj = self._read()
        wl = obj.get(client, {
            "topics": [],
            "accounts": [],
            "roi_threshold": 1.0,  # multiplier applied to default thresholds
        })
        wl.update({k: v for k, v in data.items() if k in ("topics", "accounts", "roi_threshold")})
        obj[client] = wl
        self._write(obj)
        return wl

    def get(self, client: str) -> Optional[Dict]:
        return self._read().get((client or "").strip().lower())


