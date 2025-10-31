from typing import List, Dict, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
import hashlib


def text_signature(text: str, n: int = 5) -> str:
    t = (text or "").lower().strip()
    if not t:
        return ""
    # Simple n-gram hashing for speed
    grams = [t[i : i + n] for i in range(max(0, len(t) - n + 1))]
    h = hashlib.sha256("|".join(grams).encode("utf-8")).hexdigest()
    return h[:16]


def temporal_cluster_same_text(
    items: List[Dict], window_minutes: int = 10, ngram: int = 5
) -> List[Dict]:
    """
    Group items that share same text signature within a sliding time window.
    Returns clusters with item indices and summary stats.
    """
    # Precompute signatures and timestamps
    enriched = []
    for idx, it in enumerate(items):
        sig = text_signature((it.get("content_text") or ""), n=ngram)
        ts_str = it.get("created_at") or it.get("timestamp")
        try:
            ts = datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()
        except Exception:
            ts = datetime.utcnow()
        enriched.append((idx, sig, ts))

    # Group by signature
    sig_to_items: Dict[str, List[Tuple[int, datetime]]] = defaultdict(list)
    for idx, sig, ts in enriched:
        if sig:
            sig_to_items[sig].append((idx, ts))

    clusters = []
    window = timedelta(minutes=window_minutes)
    for sig, entries in sig_to_items.items():
        entries.sort(key=lambda x: x[1])
        q: deque = deque()
        current: List[int] = []
        for idx, ts in entries:
            q.append((idx, ts))
            # Pop outside window
            while q and (ts - q[0][1]) > window:
                q.popleft()
            if len(q) >= 2:
                current = [i for i, _ in q]
                clusters.append({
                    "signature": sig,
                    "size": len(current),
                    "indices": current[:],
                    "window_minutes": window_minutes,
                })
    return clusters


