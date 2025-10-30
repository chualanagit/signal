from datetime import datetime, timezone
from typing import List
from .models import Post

def heuristic_intent_score(post: Post, query_terms: List[str]) -> float:
    """
    Calculate a deterministic intent score for a post based on:
    - Source quality (Reddit > LinkedIn > Twitter)
    - Recency (newer posts get higher scores)
    - Query term matching (title > snippet)
    - Buying intent keywords
    """
    score = 0.0
    
    # Source quality - Reddit has best buyer intent discussions
    url_str = str(post.url).lower()
    if "reddit.com" in url_str: 
        score += 1.5
    elif "linkedin.com" in url_str: 
        score += 1.0
    elif "x.com" in url_str or "twitter.com" in url_str: 
        score += 0.7
    
    # Recency boost - newer posts are more valuable
    if hasattr(post, 'ts') and post.ts:
        try:
            post_date = datetime.fromisoformat(post.ts.replace('Z', '+00:00'))
            days_old = (datetime.now(timezone.utc) - post_date).days
            # Posts within 6 months get declining boost (0-2 points)
            if days_old < 180:
                score += max(0, 2.0 * (1 - days_old / 180))
        except:
            pass
    
    # Query term matching - strong relevance signal
    title = (post.title or "").lower()
    snippet = (post.snippet or "").lower()
    
    for term in query_terms:
        term_lower = term.lower()
        if term_lower in title: 
            score += 0.8  # Title match is very relevant
        if term_lower in snippet: 
            score += 0.4  # Snippet match is good
    
    # Buying intent keywords boost
    buying_signals = [
        "our company", "our team", "we need", "looking for", 
        "recommend", " vs ", "alternative", "switching from", 
        "for our", "enterprise", "business", "comparing",
        "evaluation", "migrating", "replacing our"
    ]
    combined_text = f"{title} {snippet}"
    for signal in buying_signals:
        if signal in combined_text:
            score += 0.5
            break  # Only count once
    
    return score


def rank_posts_by_intent(posts: List[Post], queries: List[str], top_n: int = 60) -> List[Post]:
    """
    Rank posts using deterministic heuristics and return top N.
    This reduces the number of posts that need expensive LLM filtering.
    
    Args:
        posts: List of posts to rank
        queries: Search queries used (for term matching)
        top_n: Number of top posts to return (default 60)
    
    Returns:
        Top N posts sorted by intent score (highest first)
    """
    # Extract all query terms
    query_terms = []
    for q in queries:
        query_terms.extend(q.lower().split())
    
    # Calculate scores
    scored_posts = []
    for post in posts:
        score = heuristic_intent_score(post, query_terms)
        scored_posts.append((score, post))
    
    # Sort by score descending and return top N
    scored_posts.sort(key=lambda x: x[0], reverse=True)
    return [post for score, post in scored_posts[:top_n]]

