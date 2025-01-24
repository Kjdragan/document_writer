import os
import json
from datetime import datetime
import httpx
from loguru import logger
from typing import List, Dict, Any
from src.models.article import Article, ResearchData

class ResearchService:
    def __init__(self):
        """Initialize research service with API key"""
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")

    def _analyze_article(self, article: Article, index: int) -> str:
        """
        Format an article for document creation
        
        Args:
            article: Article instance
            index: Article index for numbering
            
        Returns:
            Formatted article content
        """
        # Format article with clear separation and metadata
        formatted_content = f"""
### Article {index + 1}: {article.title}
**Source**: {article.url}
**Published**: {article.published_date or 'Date not available'}

{article.proper_content}

---
"""
        return formatted_content

    def research_topic(self, topic: str) -> str:
        """
        Research a topic using Tavily API and format results
        
        Args:
            topic: Topic to research
            
        Returns:
            Formatted research results
        """
        try:
            logger.info(f"Starting Tavily search for query: {topic}")
            
            # Prepare API request
            url = "https://api.tavily.com/search"
            headers = {
                "content-type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            params = {
                "query": topic,
                "search_depth": "advanced",
                "max_results": 10,
                "include_raw_content": True,
                "include_domains": [],
                "exclude_domains": []
            }
            
            # Make API request
            with httpx.Client() as client:
                response = client.post(url, json=params, headers=headers)
                
            logger.info(f"Tavily API response status: {response.status_code}")
            
            if response.status_code != 200:
                raise Exception(f"Tavily API error: {response.text}")
                
            data = response.json()
            raw_articles = data.get('results', [])
            
            # Convert to our data model
            articles = [Article.from_tavily_response(article_data) for article_data in raw_articles]
            logger.info(f"Found {len(articles)} articles")
            
            # Log sample of content to verify
            if articles:
                first_article = articles[0]
                logger.info(f"First article proper_content length: {len(first_article.proper_content)}")
                logger.debug(f"First article content sources - Raw: {bool(first_article.raw_content)}, Regular: {bool(first_article.content)}")
            
            # Create research data container
            research_data = ResearchData(
                topic=topic,
                timestamp=datetime.now(),
                articles=articles
            )
            
            # Save raw research data
            sanitized_topic = topic.lower().replace(" ", "_")
            raw_filename = f"00_raw_research_{sanitized_topic}_{research_data.timestamp}.json"
            raw_filepath = os.path.join("_workproduct", raw_filename)
            os.makedirs("_workproduct", exist_ok=True)
            
            with open(raw_filepath, 'w', encoding='utf-8') as f:
                json.dump(research_data.model_dump(), f, indent=2)
                
            logger.info(f"Saved raw research data to {raw_filepath}")
            print(f"Raw research data saved to {raw_filename}")
            
            # Process and format articles
            formatted_articles = []
            for i, article in enumerate(articles):
                formatted_content = self._analyze_article(article, i)
                formatted_articles.append(formatted_content)
            
            # Combine all formatted content with a header
            research_content = f"""# Research Results: {topic}
*Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*

**Total Articles Found: {research_data.total_articles}**

{chr(10).join(formatted_articles)}"""
            
            return research_content
            
        except Exception as e:
            logger.error(f"Error during research: {str(e)}")
            raise