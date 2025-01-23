from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class TavilySearchResult(BaseModel):
    content: str
    raw_content: Optional[str]
    publication_date: Optional[datetime]
    url: str
    title: Optional[str]

class DocumentState(BaseModel):
    content: str
    topics: List[str]
    version: int
    metadata: Dict[str, Any]
    sources: List[str]

class EditorResponse(BaseModel):
    content: str
    revision_notes: Optional[List[str]]
    version: int

class JudgeFeedback(BaseModel):
    approved: bool
    recommendations: List[str]
    revision_required: bool