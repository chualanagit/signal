from typing import List
from .models import Post

def dedupe_by_url(items: List[Post]) -> List[Post]:
    seen = set()
    out: List[Post] = []
    for i in items:
        key = str(i.url).split("?")[0]
        if key not in seen:
            seen.add(key)
            out.append(i)
    return out

def simple_overlap_score(query: str, p: Post) -> float:
    terms = [t for t in query.lower().split() if t.strip()]
    hay = (p.title + " " + p.snippet).lower()
    hits = sum(1 for t in terms if t in hay)
    return hits / max(len(terms), 1)
