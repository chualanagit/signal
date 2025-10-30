import os
import httpx
from dotenv import load_dotenv

# Load .env as early as possible (before any os.getenv calls)
load_dotenv()  # or: load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from services.models import (
    ExtractReq, ExtractResp, GTMReq, GTMResp, KeywordsReq, KeywordsResp,
    SearchReq, SearchResp, ReplyReq, ReplyResp, Post
)
from services.search import SearchAllApis
from services.llm import (
    llmGetAppDescriptionFromWebsite,
    llmAnalyzeCustomerSegment,
    llmExtractPainPoints,
    llmGenerateGtmTopicForApp,
    llmGenerateSearchKeywords,
    llmFilterPosts,
    llmGenerateResponse,
    llmGenerateResponseStream
)
from services.utils import dedupe_by_url
from services.rank import rank_posts_by_intent

load_dotenv()

app = FastAPI(title="Intent Finder API", version="1.0")

# Shared HTTP client for connection pooling
@app.on_event("startup")
async def startup():
    app.state.http = httpx.AsyncClient(
        timeout=60.0,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
    )

@app.on_event("shutdown")
async def shutdown():
    await app.state.http.aclose()

def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http

@app.get("/")
def root_page():
    path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    return FileResponse(path)

@app.get("/health")
def health_check():
    """Health check endpoint for deployment platforms"""
    return {"status": "healthy", "service": "Intent Finder API"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
# ---- Routes mapping 1:1 to your design ----
@app.post("/extract", response_model=ExtractResp)
async def extract(req: ExtractReq, request: Request):
    try:
        http = get_http(request)
        if req.url.startswith('manual:'):
            # Handle manual text input
            description = req.url[7:]  # Remove 'manual:' prefix
        else:
            # Handle URL extraction
            description = await llmGetAppDescriptionFromWebsite(req.url, http)
        
        customer_segment = await llmAnalyzeCustomerSegment(description, http)
        pain_points = await llmExtractPainPoints(description, http)
        return ExtractResp(description=description, customer_segment=customer_segment, pain_points=pain_points)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/gtm-topics", response_model=GTMResp)
async def gtm_topics(req: GTMReq, request: Request):
    try:
        http = get_http(request)
        topics = await llmGenerateGtmTopicForApp(req.description, http)
        return GTMResp(topics=topics)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/keywords", response_model=KeywordsResp)
async def keywords(req: KeywordsReq, request: Request):
    try:
        http = get_http(request)
        queries = await llmGenerateSearchKeywords(req.topic, req.description, http)
        return KeywordsResp(queries=queries)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/search", response_model=SearchResp)
async def search(req: SearchReq, request: Request):
    try:
        http = get_http(request)
        posts = await SearchAllApis(req.queries, req.per_query, http)
        print(f"DEBUG: Found {len(posts)} raw posts")
        unique = dedupe_by_url(posts)
        print(f"DEBUG: After dedup: {len(unique)} posts")
        
        if not unique:
            return SearchResp(posts=[])
        
        # Stage 1: Deterministic ranking to reduce LLM load
        top_candidates = rank_posts_by_intent(unique, req.queries, top_n=60)
        print(f"DEBUG: Ranked top {len(top_candidates)} posts by heuristics")
        
        # Show sample posts
        for i, p in enumerate(top_candidates[:3]):
            print(f"DEBUG: Top post {i+1}: {p.source} - {p.title[:50]}...")
        
        # Stage 2: LLM filtering on top candidates only (saves tokens!)
        judged = await llmFilterPosts(req.topic, [{"title":p.title,"snippet":p.snippet,"url":p.url} for p in top_candidates], http)
        print(f"DEBUG: LLM judged {len(judged)} posts")
        
        keep = {j.url for j in judged if j.keep}
        print(f"DEBUG: Keeping {len(keep)} posts after LLM filtering")
        
        if len(keep) == 0:
            print("DEBUG: No posts passed LLM filter, returning top 3 by heuristic score")
            return SearchResp(posts=top_candidates[:3])
        
        # Return top 15 that passed LLM filter, maintaining heuristic rank order
        top15 = [p for p in top_candidates if p.url in keep][:15]
        return SearchResp(posts=top15)
    except Exception as e:
        print(f"DEBUG: Search error: {e}")
        raise HTTPException(500, str(e))

@app.post("/reply", response_model=ReplyResp)
async def reply(req: ReplyReq, request: Request):
    try:
        http = get_http(request)
        text = await llmGenerateResponse(req.topic, {"title": req.post.title, "snippet": req.post.snippet, "url": str(req.post.url)}, http)
        return ReplyResp(response=text)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/reply/stream")
async def reply_stream(req: ReplyReq, request: Request):
    """
    Stream response generation using Server-Sent Events (SSE).
    Returns text chunks as they're generated for real-time UX.
    """
    try:
        http = get_http(request)
        
        async def event_generator():
            try:
                async for chunk in llmGenerateResponseStream(
                    req.topic, 
                    {"title": req.post.title, "snippet": req.post.snippet, "url": str(req.post.url)}, 
                    http
                ):
                    # SSE format: "data: {content}\n\n"
                    yield f"data: {chunk}\n\n"
                
                # Signal completion
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: [ERROR] {str(e)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    except Exception as e:
        raise HTTPException(500, str(e))
