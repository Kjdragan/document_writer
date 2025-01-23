from typing import List, Dict
import dirtyjson
import tavily
from loguru import logger
from pydantic import ValidationError
from ..models import TavilySearchResult

class ResearchService:
    def __init__(self):
        """Initialize the research service"""
        # Tavily client will be initialized using API key from environment variables
        pass

    async def search(self, topic: str) -> List[TavilySearchResult]:
        """
        Execute Tavily search and return cleaned results
        
        Args:
            topic: The search topic/query
            
        Returns:
            List of cleaned and typed search results
        """
        try:
            # Execute search with Tavily
            raw_response = await tavily.search(topic, search_depth="advanced")
            
            # Convert to string for dirtyjson parsing
            response_str = str(raw_response)
            
            # Parse with dirtyjson to handle potential "dirty" JSON
            try:
                cleaned_response = dirtyjson.loads(response_str)
                return self._clean_tavily_response(cleaned_response)
            except Exception as e:
                logger.error(f"Error parsing Tavily response with dirtyjson: {str(e)}")
                # Fallback to using raw response if dirtyjson parsing fails
                return self._clean_tavily_response(raw_response)
                
        except Exception as e:
            logger.error(f"Error during Tavily search: {str(e)}")
            raise

    def _clean_tavily_response(self, raw_response: Dict) -> List[TavilySearchResult]:
        """
        Clean and process Tavily response
        
        1. Extract relevant fields
        2. Prefer raw_content over content when available
        3. Deduplicate by URL
        4. Remove entries with missing critical data
        5. Return cleaned, typed results
        
        Args:
            raw_response: Raw response from Tavily API
            
        Returns:
            List of cleaned TavilySearchResult objects
        """
        cleaned_results = []
        seen_urls = set()
        
        try:
            results = raw_response.get('results', [])
            
            # Handle potential string results from dirtyjson
            if isinstance(results, str):
                try:
                    results = dirtyjson.loads(results)
                except Exception as e:
                    logger.warning(f"Failed to parse results string: {str(e)}")
                    results = []
            
            for result in results:
                # Skip if URL already processed (deduplication)
                url = result.get('url')
                if not url or url in seen_urls:
                    continue
                    
                seen_urls.add(url)
                
                # Prefer raw_content if available
                content = result.get('raw_content') or result.get('content')
                if not content:
                    continue
                
                # Clean potential string escaping issues
                if isinstance(content, str):
                    content = content.replace('\\"', '"').replace('\\n', '\n')
                
                try:
                    # Create Pydantic model with cleaned data
                    search_result = TavilySearchResult(
                        content=content,
                        raw_content=result.get('raw_content'),
                        url=url,
                        title=result.get('title'),
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