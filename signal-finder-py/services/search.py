import os
import httpx
from typing import List
from dotenv import load_dotenv
from .models import Post

# Load environment variables
load_dotenv()

KEY = os.getenv("GOOGLE_CSE_KEY", "")
CX_LI = os.getenv("GOOGLE_CSE_CX_LINKEDIN", "")
CX_RD = os.getenv("GOOGLE_CSE_CX_REDDIT", "")

async def _cse(cx: str, q: str, http: httpx.AsyncClient, num: int = 10, start: int = 1) -> dict:
    params = {"key": KEY, "cx": cx, "q": q, "num": str(num), "start": str(start)}
    r = await http.get("https://www.googleapis.com/customsearch/v1", params=params)
    r.raise_for_status()
    return r.json()

def _normalize(source: str, data: dict) -> List[Post]:
    items = data.get("items", []) or []
    out: List[Post] = []
    for i in items:
        out.append(Post(
            source=source,
            title=i.get("title") or "",
            url=i.get("link") or "",
            snippet=i.get("snippet") or ""
        ))
    return out

# --- your function names ---
async def searchXApi(queries: List[str], per_query: int, http: httpx.AsyncClient) -> List[Post]:
    # Placeholder: integrate X official API if available; keep signature.
    return []

async def searchLinkedInApi(queries: List[str], per_query: int, http: httpx.AsyncClient) -> List[Post]:
    all_posts: List[Post] = []
    for q in queries:
        data = await _cse(CX_LI, q, http, per_query)
        all_posts.extend(_normalize("linkedin", data))
    return all_posts

async def searchRedditApi(queries: List[str], per_query: int, http: httpx.AsyncClient) -> List[Post]:
    all_posts: List[Post] = []
    for q in queries:
        data = await _cse(CX_RD, q, http, per_query)
        all_posts.extend(_normalize("reddit", data))
    return all_posts

async def SearchAllApis(queries: List[str], per_query: int, http: httpx.AsyncClient) -> List[Post]:
    # Prioritize Reddit for better community discussions
    rd = await searchRedditApi(queries, per_query * 2, http)  # More Reddit results
    li = await searchLinkedInApi(queries, per_query, http)    # Normal LinkedIn results  
    x  = await searchXApi(queries, per_query, http)
    
    # Mix results instead of just concatenating
    mixed_results = []
    max_len = max(len(rd), len(li), len(x))
    
    for i in range(max_len):
        if i < len(rd): mixed_results.append(rd[i])
        if i < len(li): mixed_results.append(li[i])
        if i < len(x): mixed_results.append(x[i])
    
    return mixed_results
