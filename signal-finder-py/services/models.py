from pydantic import BaseModel, HttpUrl
from typing import List, Literal, Optional, Dict

Source = Literal["linkedin", "reddit", "x"]

class Post(BaseModel):
    source: Source
    title: str
    url: HttpUrl | str
    snippet: str
    ts: Optional[str] = None

class ExtractReq(BaseModel):
    url: str

class ExtractResp(BaseModel):
    description: str
    customer_segment: str
    pain_points: List[str]

class GTMReq(BaseModel):
    description: str

class GTMResp(BaseModel):
    topics: List[str]

class KeywordsReq(BaseModel):
    topic: str
    description: str

class KeywordsResp(BaseModel):
    queries: List[str]

class SearchReq(BaseModel):
    topic: str
    queries: List[str]
    per_query: int = 6

class SearchResp(BaseModel):
    posts: List[Post]

class ReplyReq(BaseModel):
    topic: str
    post: Post

class ReplyResp(BaseModel):
    response: str

class JudgeItem(BaseModel):
    url: str
    keep: bool    
    reason: str

