from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator

class Article(BaseModel):
    """Data model for a research article"""
    title: str = Field(default="Untitled Article")
    url: str = Field(default="")
    proper_content: str = Field(default="No content available")  # Default value for proper_content
    published_date: Optional[str] = Field(default=None)
    score: Optional[float] = Field(default=None)
    raw_content: Optional[str] = Field(default=None)  # Original raw_content from Tavily
    content: Optional[str] = Field(default=None)      # Original content from Tavily
    
    @validator('proper_content', always=True)
    def set_proper_content(cls, v, values):
        """Set proper_content from raw_content or content if not provided"""
        if v and v != "No content available":
            return v.strip() if isinstance(v, str) else str(v)
            
        # Try raw_content first
        raw = values.get('raw_content')
        if raw and isinstance(raw, str):
            return raw.strip()
            
        # Fallback to content
        content = values.get('content')
        if content and isinstance(content, str):
            return content.strip()
            
        return "No content available"
    
    @classmethod
    def from_tavily_response(cls, article_data: dict) -> 'Article':
        """Create Article instance from Tavily API response"""
        return cls(
            title=article_data.get('title', "Untitled Article"),  # Provide default
            url=article_data.get('url', ''),
            published_date=article_data.get('published_date'),
            score=article_data.get('score'),
            raw_content=article_data.get('raw_content'),
            content=article_data.get('content'),
            # proper_content will be set by validator
        )

class ResearchData(BaseModel):
    """Container for research results"""
    topic: str
    timestamp: datetime
    articles: List[Article]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y%m%d_%H%M%S")
        }
    
    @property
    def total_articles(self) -> int:
        return len(self.articles)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ResearchData':
        """Create ResearchData instance from dictionary"""
        return cls(
            topic=data['topic'],
            timestamp=datetime.strptime(data['timestamp'], "%Y%m%d_%H%M%S"),
            articles=[Article.from_tavily_response(article) for article in data['articles']]
        )
