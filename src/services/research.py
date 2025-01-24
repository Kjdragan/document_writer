from typing import List, Optional, Dict
import httpx
import os
from loguru import logger
from ..models import TavilyArticle, TavilyResponse

class ResearchService:
    def __init__(self):
        """Initialize research service"""
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
            
        # Ensure API key has tvly- prefix
        self.api_key = f"tvly-{api_key}" if not api_key.startswith("tvly-") else api_key
        
        # Configure client with longer timeout
        timeout = httpx.Timeout(30.0, connect=30.0)  # 30 seconds for both read and connect
        self.client = httpx.AsyncClient(timeout=timeout)

    async def search_topic(self, query: str) -> List[TavilyArticle]:
        """Search for articles about a topic
        
        Args:
            query: Search query
            
        Returns:
            List of top 10 articles sorted by relevance score
        """
        logger.info(f"Starting Tavily search for query: {query}")
        
        try:
            # Call Tavily search API
            logger.debug("Preparing Tavily search request")
            response = await self.client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_answer": False,
                    "include_images": True,
                    "include_image_descriptions": True,
                    "include_raw_content": True,
                    "max_results": 10,
                    "include_domains": [],
                    "exclude_domains": []
                }
            )
            
            # Log response details
            logger.info(f"Tavily API response status: {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            
            # Log raw response for debugging
            logger.debug(f"Tavily API raw response: {data}")
            
            # Convert to our model and get top articles
            tavily_response = TavilyResponse(articles=[
                TavilyArticle(
                    title=str(article.get("title", "")),
                    url=str(article.get("url", "")),
                    content=str(article.get("content", "")),
                    raw_content=str(article.get("raw_content")) if article.get("raw_content") else None,
                    score=float(article.get("score", 0.0)),
                )
                for article in data.get("results", [])
            ])
            
            # Log article details
            logger.info(f"Found {len(tavily_response.articles)} articles")
            for i, article in enumerate(tavily_response.articles, 1):
                logger.debug(f"Article {i}: {article.title} (Score: {article.score})")
            
            return tavily_response.articles

        except httpx.TimeoutException as e:
            logger.error(f"Timeout while calling Tavily API: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Tavily API: {str(e)}")
            if e.response.status_code == 401:
                logger.error("Invalid API key or authentication error")
            raise
        except httpx.RequestError as e:
            logger.error(f"Network error while calling Tavily API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during research: {str(e)}")
            raise

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()