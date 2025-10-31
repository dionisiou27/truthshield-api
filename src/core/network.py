from typing import List, Dict, Tuple
from collections import defaultdict


def build_co_posting_graph(items: List[Dict]) -> Dict[str, Dict[str, int]]:
    """Simple adjacency map where edges connect authors who posted same signature."""
    # Compute signature buckets
    from .temporal import text_signature

    sig_to_authors: Dict[str, List[str]] = defaultdict(list)
    for it in items:
        sig = text_signature(it.get("content_text") or "")
        author = (it.get("author_username") or "").lower()
        if sig and author:
            sig_to_authors[sig].append(author)

    # Build adjacency counts
    adj: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for authors in sig_to_authors.values():
        unique = list(dict.fromkeys(authors))
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                a, b = unique[i], unique[j]
                adj[a][b] += 1
                adj[b][a] += 1
    return adj


def connected_components(adj: Dict[str, Dict[str, int]], min_weight: int = 1) -> List[List[str]]:
    """Return connected components using BFS over edges >= min_weight."""
    visited = set()
    comps: List[List[str]] = []
    nodes = list(adj.keys())
    for n in nodes:
        if n in visited:
            continue
        stack = [n]
        comp = []
        visited.add(n)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v, w in adj[u].items():
                if w >= min_weight and v not in visited:
                    visited.add(v)
                    stack.append(v)
        comps.append(comp)
    return comps


