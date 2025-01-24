import os
from datetime import datetime
from typing import List, Optional
from loguru import logger
from rich.console import Console

from .agents import EditorAgent, JudgeAgent
from .services import ResearchService
from .models import DocumentState

class DocumentWriter:
    def __init__(self):
        """Initialize document writer with necessary agents and services"""
        self.research_service = ResearchService()
        self.editor_agent = EditorAgent()
        self.judge_agent = JudgeAgent()
        self.console = Console()

    async def process_document(self, topic: str) -> None:
        """
        Process a document through the full pipeline
        
        Args:
            topic: Topic to write about
        """
        try:
            # Start research phase
            self.console.print("Starting document creation for topic:", topic)
            self.console.print("Researching topic...")
            
            # Get research results
            research_content = self.research_service.research_topic(topic)
            
            # Save initial research
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sanitized_topic = topic.lower().replace(" ", "_")
            initial_filename = f"01_initial_research_{sanitized_topic}_{timestamp}.md"
            
            # Create document state
            doc_state = DocumentState(
                content=research_content,
                topics=[topic],
                version=1
            )
            
            # Save initial research to file
            os.makedirs("_workproduct", exist_ok=True)
            with open(os.path.join("_workproduct", initial_filename), "w", encoding="utf-8") as f:
                f.write(doc_state.content)
            logger.info(f"Saved document version to _workproduct\\{initial_filename}")
            
            # Edit document
            self.console.print("Editing document...")
            edited = await self.editor_agent.process_document(doc_state)
            
            # Review document
            self.console.print("Reviewing document...")
            feedback = await self.judge_agent.review_document(doc_state, edited)
            
            if feedback.revision_required:
                self.console.print("[yellow]Document needs revision. Recommendations:[/]")
                for rec in feedback.recommendations:
                    self.console.print(f"- {rec}")
            else:
                self.console.print("[green]Document approved![/]")
                
            self.console.print("\nDocument creation complete!")
            
        except Exception as e:
            logger.error(f"Error during document processing: {str(e)}")
            self.console.print(f"[red]Critical error: {str(e)}[/]")
            raise

    async def continue_latest(self, topic_filter: Optional[str] = None) -> None:
        """
        Continue working on the latest document version
        
        Args:
            topic_filter: Optional topic to filter documents by
        """
        try:
            # Find latest document
            workproduct_dir = "_workproduct"
            if not os.path.exists(workproduct_dir):
                raise FileNotFoundError("No existing documents found")
                
            files = [f for f in os.listdir(workproduct_dir) if f.endswith(".md")]
            if not files:
                raise FileNotFoundError("No markdown documents found")
                
            # Filter by topic if specified
            if topic_filter:
                files = [f for f in files if topic_filter.lower() in f.lower()]
                if not files:
                    raise FileNotFoundError(f"No documents found matching topic: {topic_filter}")
                    
            # Get latest file
            latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(workproduct_dir, x)))
            
            # Load document
            with open(os.path.join(workproduct_dir, latest_file), "r", encoding="utf-8") as f:
                content = f.read()
                
            # Extract topic from filename
            topic = latest_file.split("_", 2)[2].rsplit("_", 1)[0].replace("_", " ")
            
            # Create document state
            doc_state = DocumentState(
                content=content,
                topics=[topic],
                version=int(latest_file.split("_")[0])
            )
            
            # Process document
            await self.process_document(topic)
            
        except FileNotFoundError as e:
            logger.error(f"File not found: {str(e)}")
            self.console.print(f"[red]Error: {str(e)}[/]")
        except Exception as e:
            logger.error(f"Error continuing document: {str(e)}")
            self.console.print(f"[red]Error: {str(e)}[/]")
            raise