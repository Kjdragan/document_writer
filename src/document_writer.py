import asyncio
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from loguru import logger
from rich.console import Console
from rich.prompt import Confirm, Prompt
from .services.research import ResearchService
from .agents.editor import EditorAgent
from .agents.judge import JudgeAgent
from .models import DocumentState, EditorResponse, TavilyArticle

console = Console()

class DocumentWriter:
    def __init__(self):
        """Initialize document writer with required services and agents"""
        self.research_service = ResearchService()
        self.editor_agent = EditorAgent()
        self.judge_agent = JudgeAgent()
        self.client = AsyncOpenAI()

    async def process_document(self, topic: str) -> None:
        """Process a document about a topic
        
        Args:
            topic: Topic to write about
        """
        console.print(f"[bold blue]Starting document creation for topic: {topic}[/]")
        
        try:
            # Initial research
            try:
                console.print("[yellow]Performing research...[/]")
                articles = await self.research_service.search_topic(topic)
                
                if not articles:
                    logger.warning("No articles found for the topic")
                    console.print("[red]No articles found for the given topic.[/]")
                    return
                
                # Save raw research output
                await self._save_raw_research(topic, articles)
                
                console.print(f"[green]Found {len(articles)} articles for research[/]")
            except Exception as e:
                logger.error(f"Error during document processing: {str(e)}")
                console.print(f"[red]Error: Unable to research topic. {str(e)}[/]")
                return
            
            # Create initial document state
            doc_state = DocumentState(
                content="",
                topics=[topic],
                version=1
            )
            
            # Append analysis for each article
            console.print("[yellow]Analyzing articles...[/]")
            for i, article in enumerate(articles, 1):
                console.print(f"[blue]Analyzing article {i}/{len(articles)}[/]")
                analysis = await self._analyze_article(article)
                doc_state.content += f"\n\n{analysis}"
            
            # Save initial research
            await self.save_version(doc_state, "initial_research")
            
            # Now edit the complete document once
            console.print("[yellow]Editing document...[/]")
            edited = await self.editor_agent.process_document(doc_state)
            doc_state = DocumentState(
                content=edited.content,
                topics=doc_state.topics,
                version=edited.version
            )
            
            # Save edited version
            await self.save_version(doc_state, "edited")
            
            console.print("\n[bold green]Document processing complete![/]")
            console.print(f"Final document saved with {len(doc_state.topics)} topics "
                        f"and version {doc_state.version}")
                        
        except Exception as e:
            logger.error(f"Error during document processing: {str(e)}")
            console.print(f"[red]Critical error: {str(e)}[/]")
            raise

    async def _analyze_article(self, article: TavilyArticle) -> str:
        """Analyze a single article and return formatted content
        
        Args:
            article: Article to analyze
            
        Returns:
            Formatted analysis of the article
        """
        system_message = """You are a news analyst. Your task is to analyze the provided article 
        and extract key information in a clear, concise format. Focus on:
        1. Main events and developments
        2. Key figures and their roles
        3. Important context and implications
        4. Verified facts vs claims
        
        Format your analysis with clear headers and bullet points."""

        user_message = f"""Analyze this article:
        Title: {article.title}
        URL: {article.url}
        Content: {article.get_best_content()}
        
        Provide a clear, structured analysis focusing on verified information."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3
            )
            
            if not response.choices[0].message.content:
                raise ValueError("Empty response from OpenAI")
                
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error analyzing article: {str(e)}")
            return "Error analyzing article: Unable to process content"

    async def _save_raw_research(self, topic: str, articles: List[TavilyArticle]) -> None:
        """Save raw research data as a JSON file
        
        Args:
            topic: Research topic
            articles: List of articles found
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            topic_slug = "_".join(topic.lower().split())[:50]  # First topic, slugified
            filename = f"00_raw_research_{topic_slug}_{timestamp}.json"
            
            # Ensure _workproduct directory exists
            os.makedirs("_workproduct", exist_ok=True)
            
            # Prepare raw research data
            raw_data = {
                "topic": topic,
                "timestamp": timestamp,
                "total_articles": len(articles),
                "articles": [
                    {
                        "title": article.title,
                        "url": article.url,
                        "content": article.content,
                        "raw_content": article.raw_content,
                        "content_length": len(article.content),
                        "raw_content_length": len(article.raw_content) if article.raw_content else 0,
                        "score": article.score
                    } for article in articles
                ]
            }
            
            # Save file
            filepath = os.path.join("_workproduct", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved raw research data to {filepath}")
            console.print(f"[green]Raw research data saved to {filename}[/]")
            
        except Exception as e:
            logger.error(f"Error saving raw research data: {str(e)}")
            console.print(f"[red]Failed to save raw research data: {str(e)}[/]")

    async def save_version(self, doc_state: DocumentState, stage: str) -> None:
        """Save a version of the document
        
        Args:
            doc_state: Document state to save
            stage: Stage of processing (e.g. initial_research, edited)
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            topic_slug = "_".join(doc_state.topics[0].lower().split())[:50]  # First topic, slugified
            filename = f"{doc_state.version:02d}_{stage}_{topic_slug}_{timestamp}.md"
            
            # Ensure _workproduct directory exists
            os.makedirs("_workproduct", exist_ok=True)
            
            # Save file
            filepath = os.path.join("_workproduct", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(doc_state.content)
                
            logger.info(f"Saved document version to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving document version: {str(e)}")
            raise

    async def continue_latest(self, topic_filter: Optional[str] = None) -> None:
        """Continue working on the latest document version
        
        Args:
            topic_filter: Optional topic to filter by
        """
        try:
            console.print("[yellow]No existing document found.[/]")
            return
                
        except Exception as e:
            logger.error(f"Error while continuing document: {str(e)}")
            raise

    async def close(self):
        """Clean up resources"""
        await self.research_service.close()