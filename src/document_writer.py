import asyncio
from typing import Optional
from loguru import logger
from rich.console import Console
from rich.prompt import Confirm, Prompt

from .models import DocumentState, EditorResponse
from .services.research import ResearchService
from .services.document import DocumentService
from .agents.editor import EditorAgent
from .agents.judge import JudgeAgent

console = Console()

class DocumentWriter:
    def __init__(self):
        """Initialize the document writer with all required services and agents"""
        self.research_service = ResearchService()
        self.document_service = DocumentService()
        self.editor_agent = EditorAgent()
        self.judge_agent = JudgeAgent()

    async def initial_research(self, topic: str) -> DocumentState:
        """
        Handle initial document creation from research
        
        Args:
            topic: Initial research topic
            
        Returns:
            Initial document state
        """
        try:
            console.print(f"\n[bold blue]Researching topic:[/] {topic}")
            
            # Perform initial research
            results = await self.research_service.search(topic)
            if not results:
                raise ValueError(f"No research results found for topic: {topic}")
                
            # Process results into initial content
            content = await self.research_service.process_results(results)
            
            # Create initial document
            doc_state = self.document_service.create_new(content, topic)
            
            # Save initial version
            self.document_service.save_version(doc_state, "initial_research")
            
            return doc_state
            
        except Exception as e:
            logger.error(f"Error during initial research: {str(e)}")
            raise

    async def expansion_loop(self, doc_state: DocumentState) -> bool:
        """
        Run expansion loop on document
        
        Args:
            doc_state: Current document state
            
        Returns:
            True if more expansion needed, False if complete
        """
        try:
            # Get feedback from judge
            feedback = await self.judge_agent.review_document(doc_state, EditorResponse(
                content=doc_state.content,
                version=doc_state.version,
                revision_notes=None
            ))
            
            if not feedback.revision_required:
                return False
                
            # Apply edits based on feedback
            edited_response = await self.editor_agent.process_document(doc_state)
            
            # Update document state
            doc_state.content = edited_response.content
            doc_state.version = edited_response.version
            
            # Save new version
            self.document_service.save_version(doc_state, "expansion")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in expansion loop: {str(e)}")
            raise

    async def editing_loop(self, doc_state: DocumentState) -> DocumentState:
        """
        Run editing loop on document
        
        Args:
            doc_state: Current document state
            
        Returns:
            Final document state
        """
        try:
            while True:
                # Get feedback from judge
                feedback = await self.judge_agent.review_document(doc_state, EditorResponse(
                    content=doc_state.content,
                    version=doc_state.version,
                    revision_notes=None
                ))
                
                if not feedback.revision_required:
                    break
                    
                # Apply edits based on feedback
                edited_response = await self.editor_agent.process_document(doc_state)
                
                # Update document state
                doc_state.content = edited_response.content
                doc_state.version = edited_response.version
                
                # Save new version
                self.document_service.save_version(doc_state, "editing")
            
            return doc_state
            
        except Exception as e:
            logger.error(f"Error in editing loop: {str(e)}")
            raise

    async def process_document(self, initial_topic: str):
        """
        Main document processing flow
        
        Args:
            initial_topic: Initial topic to research
        """
        try:
            # Initial research
            doc_state = await self.initial_research(initial_topic)
            
            # Expansion loop
            while await self.expansion_loop(doc_state):
                continue
                
            # Editing loop
            final_doc = await self.editing_loop(doc_state)
            
            console.print("\n[bold green]Document processing complete![/]")
            console.print(f"Final document saved with {len(final_doc.topics)} topics "
                        f"and version {final_doc.version}")
                        
        except Exception as e:
            logger.error(f"Error during document processing: {str(e)}")
            raise

    async def continue_latest(self, topic_filter: Optional[str] = None) -> None:
        """
        Continue working on the latest document version
        
        Args:
            topic_filter: Optional topic to filter by
        """
        try:
            # Get latest version
            latest_doc = self.document_service.get_latest_version(topic_filter)
            
            if not latest_doc:
                console.print("[yellow]No existing document found.[/]")
                return
                
            # Run expansion and editing process
            await self.process_document(latest_doc.topics[0])
            
        except Exception as e:
            logger.error(f"Error while continuing document: {str(e)}")
            raise