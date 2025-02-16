from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class TavilyArticle(BaseModel):
    """Article from Tavily search"""
    title: str
    url: str
    content: str
    raw_content: Optional[str] = None
    score: float = Field(..., description="Relevance score from Tavily")
    published_date: Optional[str] = None

    def get_best_content(self) -> str:
        """Get the best available content, preferring raw_content"""
        return self.raw_content if self.raw_content else self.content

class TavilyResponse(BaseModel):
    """Response from Tavily search"""
    articles: List[TavilyArticle]

    def get_top_articles(self, limit: int = 5) -> List[TavilyArticle]:
        """Get top N articles sorted by score"""
        return sorted(self.articles, key=lambda x: x.score, reverse=True)[:limit]

class DocumentState(BaseModel):
    """State of a document being processed"""
    content: str
    topics: List[str]
    version: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sources: List[str] = Field(default_factory=list)

class EditorResponse(BaseModel):
    """Response from editor agent"""
    content: str
    revision_notes: List[str] = Field(default_factory=list)
    version: int

class Decision(str, Enum):
    """Decision options for document review"""
    APPROVE = "APPROVE"
    REVISE = "REVISE"

class JudgeFeedback(BaseModel):
    """Feedback from judge agent"""
    approved: bool
    recommendations: List[str]
    revision_required: bool