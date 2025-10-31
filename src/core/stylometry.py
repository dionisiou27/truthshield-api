from typing import Dict
import hashlib


def ngram_shingle(text: str, n: int = 3) -> Dict[str, int]:
    t = (text or "").lower()
    shingles: Dict[str, int] = {}
    for i in range(max(0, len(t) - n + 1)):
        g = t[i : i + n]
        shingles[g] = shingles.get(g, 0) + 1
    return shingles


def cosine_similarity(a: Dict[str, int], b: Dict[str, int]) -> float:
    if not a or not b:
        return 0.0
    dot = 0
    norm_a = 0
    norm_b = 0
    for k, va in a.items():
        vb = b.get(k, 0)
        dot += va * vb
        norm_a += va * va
    for vb in b.values():
        norm_b += vb * vb
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return min(1.0, max(0.0, dot / ((norm_a ** 0.5) * (norm_b ** 0.5))))


def stylometry_similarity(text_a: str, text_b: str, n: int = 3) -> float:
    return cosine_similarity(ngram_shingle(text_a, n), ngram_shingle(text_b, n))


