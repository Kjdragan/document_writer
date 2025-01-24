from typing import List, Dict, Any
import json
from tavily import TavilyClient
import os
from loguru import logger
from pydantic import ValidationError
from ..models import TavilySearchResult

class ResearchService:
    def __init__(self):
        """Initialize the research service"""
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable is required")
        self.client = TavilyClient(api_key)

    async def search(self, topic: str) -> List[TavilySearchResult]:
        """
        Execute Tavily search and return cleaned results
        
        Args:
            topic: The search topic/query
            
        Returns:
            List of cleaned and typed search results
        """
        try:
            # Execute search with Tavily (synchronous)
            raw_response = self.client.search(topic, search_depth="advanced")
            
            # Tavily response is already a dict, no need for parsing
            return self._clean_tavily_response(raw_response)
                
        except Exception as e:
            logger.error(f"Error during Tavily search: {str(e)}")
            raise

    def _clean_tavily_response(self, raw_response: Dict[str, Any]) -> List[TavilySearchResult]:
        """
        Clean and process Tavily response
        
        Args:
            raw_response: Raw response from Tavily API
            
        Returns:
            List of cleaned TavilySearchResult objects
        """
        cleaned_results = []
        seen_urls = set()
        
        try:
            if not isinstance(raw_response, dict):
                logger.warning(f"Raw response is not a dict, got {type(raw_response)}")
                return []
                
            results = raw_response.get('results', [])
            if not isinstance(results, list):
                logger.warning(f"Results is not a list, got {type(results)}")
                return []
            
            for result in results:
                if not isinstance(result, dict):
                    logger.warning(f"Result is not a dict, got {type(result)}")
                    continue
                    
                # Skip if URL already processed (deduplication)
                url = result.get('url')
                if not url or url in seen_urls:
                    continue
                    
                seen_urls.add(url)
                
                # Get content, preferring raw_content if available
                content = result.get('raw_content', '') or result.get('content', '')
                if not content:
                    continue
                
                try:
                    # Create Pydantic model with cleaned data
                    search_result = TavilySearchResult(
                        content=str(content),
                        raw_content=result.get('raw_content'),
                        url=str(url),
                        title=str(result.get('title', '')),
                        publication_date=result.get('published_date')
                    )
                    cleaned_results.append(search_result)
                except ValidationError as ve:
                    logger.warning(f"Validation error for result {url}: {str(ve)}")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to process result {url}: {str(e)}")
                    continue
                    
            return cleaned_results
            
        except Exception as e:
            logger.error(f"Error cleaning Tavily response: {str(e)}")
            return []

    async def process_results(self, results: List[TavilySearchResult]) -> str:
        """
        Combine and format search results for document creation
        
        Args:
            results: List of search results to process
            
        Returns:
            Formatted content string with source attribution
        """
        if not results:
            return ""
            
        # Combine content with source attribution
        processed_content = []
        
        for result in results:
            content = result.content.strip()
            if content:
                # Add content with source attribution
                processed_content.extend([
                    f"\n## Content from {result.title or 'Untitled'}\n",
                    content,
                    f"\nSource: {result.url}\n"
                ])
                
        return "\n".join(processed_content)