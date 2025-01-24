from typing import List, Optional, Dict
import httpx
import os
from loguru import logger
from ..models import TavilyArticle, TavilyResponse

class ResearchService:
    def __init__(self):
        """Initialize research service"""
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        self.client = httpx.AsyncClient()

    async def search_topic(self, query: str) -> List[TavilyArticle]:
        """Search for articles about a topic
        
        Args:
            query: Search query
            
        Returns:
            List of top 5 articles sorted by relevance score
        """
        try:
            # Ensure API key is a string
            headers: Dict[str, str] = {"api-key": str(self.api_key)}

            # Call Tavily search API
            response = await self.client.post(
                "https://api.tavily.com/search",
                json={
                    "query": query,
                    "search_depth": "advanced",
                    "include_answer": False,
                    "include_domains": [],
                    "exclude_domains": [],
                    "max_results": 10  # Request more to allow for filtering
                },
                headers=headers
            )
            response.raise_for_status()
            data = response.json()

            # Convert to our model and get top articles
            tavily_response = TavilyResponse(articles=[
                TavilyArticle(
                    title=str(article.get("title", "")),
                    url=str(article.get("url", "")),
                    content=str(article.get("content", "")),
                    raw_content=str(article.get("raw_content")) if article.get("raw_content") else None,
                    score=float(article.get("score", 0.0)),
                    published_date=str(article.get("published_date")) if article.get("published_date") else None
                )
                for article in data.get("results", [])
            ])

            return tavily_response.get_top_articles(limit=5)

        except Exception as e:
            logger.error(f"Error during research: {str(e)}")
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()