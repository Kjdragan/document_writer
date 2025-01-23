import asyncio
from typing import Optional
from loguru import logger
from rich.console import Console
from rich.prompt import Confirm, Prompt

from .models import DocumentState
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

    async def expansion_loop(self, current_doc: DocumentState) -> bool:
        """
        Handle document expansion flow
        
        Args:
            current_doc: Current document state
            
        Returns:
            True if expansion should continue, False if ready for editing
        """
        try:
            # Ask user if they want to expand or finalize
            should_expand = Confirm.ask("\nWould you like to expand the document with a new topic?")
            
            if not should_expand:
                return False
                
            # Get new topic
            new_topic = Prompt.ask("\nEnter the new topic to research")
            
            console.print(f"\n[bold blue]Researching expansion topic:[/] {new_topic}")
            
            # Research new topic
            results = await self.research_service.search(new_topic)
            if not results:
                console.print(f"[yellow]No results found for topic: {new_topic}[/]")
                return True
                
            # Process new content
            new_content = await self.research_service.process_results(results)
            
            # Append to document
            updated_doc = self.document_service.append_content(
                current_doc,
                new_content,
                new_topic
            )
            
            # Save expansion version
            self.document_service.save_version(updated_doc, "expansion")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during expansion: {str(e)}")
            raise

    async def editing_loop(self, doc: DocumentState) -> DocumentState:
        """
        Handle editing and review flow
        
        Args:
            doc: Document to edit
            
        Returns:
            Final approved document state
        """
        current_doc = doc
        max_iterations = 3  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            try:
                console.print("\n[bold blue]Editing document...[/]")
                
                # Submit to editor
                editor_response = await self.editor_agent.process_document(current_doc)
                
                # Save editor's version
                current_doc.content = editor_response.content
                current_doc.version = editor_response.version
                self.document_service.save_version(current_doc, "editor_draft")
                
                console.print("\n[bold blue]Reviewing changes...[/]")
                
                # Get judge's feedback
                feedback = await self.judge_agent.review_document(doc, editor_response)
                
                # Display recommendations
                console.print("\n[bold yellow]Review Feedback:[/]")
                for rec in feedback.recommendations:
                    console.print(f"• {rec}")
                
                if feedback.approved:
                    console.print("\n[bold green]Document approved![/]")
                    
                    # Save final version
                    self.document_service.save_version(current_doc, "final")
                    return current_doc
                    
                if feedback.revision_required:
                    console.print("\n[yellow]Revision required. Continuing editing...[/]")
                    iteration += 1
                    continue
                    
            except Exception as e:
                logger.error(f"Error during editing loop: {str(e)}")
                raise
                
        console.print("\n[yellow]Max editing iterations reached. Saving current version as final.[/]")
        self.document_service.save_version(current_doc, "final")
        return current_doc

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