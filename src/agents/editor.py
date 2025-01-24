import os
import json
from datetime import datetime
from typing import List, Optional
from openai import AsyncOpenAI
import instructor
from loguru import logger
from rich.console import Console
from pydantic import BaseModel, Field
import asyncio

from ..models import DocumentState, EditorResponse

class EditorRevisionResponse(BaseModel):
    """Structured response for document revision"""
    improved_content: str = Field(..., description="The improved version of the document")
    revision_notes: List[str] = Field(default_factory=list, description="List of key improvements and changes made")

class EditorAgent:
    def __init__(self, model: str = "deepseek-chat"):
        """
        Initialize editor agent
        
        Args:
            model: Model to use for processing
        """
        self.model = model
        # Initialize with Instructor and Deepseek
        client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )
        self.client = instructor.patch(client)
        self.console = Console()

    async def process_document(self, doc: DocumentState) -> EditorResponse:
        """
        Analyze and improve document structure and coherence
        
        Args:
            doc: Current document state to process
            
        Returns:
            EditorResponse with improved content and notes
        """
        try:
            # Prepare system message for the editor role
            system_message = """You are an advanced AI document editor with expertise in technical and academic writing. 
            Your mission is to transform raw content into a polished, professional document.

            EDITORIAL MANDATE:
            1. Structural Refinement
               - Create a clear, logical narrative arc
               - Ensure smooth transitions between sections
               - Balance depth and accessibility of content

            2. Technical Precision
               - Verify technical accuracy of terminology
               - Maintain domain-specific nuance
               - Eliminate ambiguity or vague statements

            3. Clarity and Readability
               - Optimize sentence structure for comprehension
               - Remove unnecessary jargon
               - Create a consistent, engaging writing style

            4. Information Hierarchy
               - Prioritize key insights
               - Create meaningful section headings
               - Ensure proportional coverage of subtopics

            5. Citation and Reference Management
               - Identify areas needing additional context
               - Suggest potential reference points
               - Maintain academic/professional tone

            EDITING GUIDELINES:
            - Preserve original intent and core information
            - Make surgical, meaningful improvements
            - Provide transparent revision notes
            - Target an audience of informed professionals
            """

            # Detailed editing prompt
            user_message = f"""DOCUMENT EDITING REQUEST

            CURRENT DOCUMENT CONTEXT:
            - Primary Topics: {', '.join(doc.topics)}
            - Current Version: {doc.version}
            - Content Length: {len(doc.content)} characters

            DOCUMENT CONTENT:
            {doc.content}

            EDITING INSTRUCTIONS:
            1. Perform a comprehensive, multi-dimensional document refinement
            2. Improve overall document quality
            3. Provide specific, actionable revision notes
            4. Maintain the original document's core insights and intent"""

            # Call Deepseek API with Instructor for structured output
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                response_model=EditorRevisionResponse,
                max_tokens=3000,
                temperature=0.7
            )

            # Create editor response from structured output
            editor_response = EditorResponse(
                content=completion.improved_content,
                revision_notes=completion.revision_notes,
                version=doc.version + 1
            )

            # Save editor's work product
            await self._save_editor_workproduct(doc.topics[0], editor_response)

            return editor_response

        except Exception as e:
            logger.error(f"Error during document editing: {str(e)}")
            raise

    async def _save_editor_workproduct(self, topic: str, editor_response: EditorResponse) -> None:
        """
        Save editor's work product to _workproduct directory
        
        Args:
            topic: Document topic
            editor_response: Editor's response with revised content
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            topic_slug = "_".join(topic.lower().split())[:50]
            filename = f"02_editor_revision_{topic_slug}_{timestamp}.json"
            
            # Ensure _workproduct directory exists
            os.makedirs("_workproduct", exist_ok=True)
            
            # Prepare editor work product data
            workproduct_data = {
                "topic": topic,
                "timestamp": timestamp,
                "version": editor_response.version,
                "revision_notes": editor_response.revision_notes,
                "content_length": len(editor_response.content)
            }
            
            # Save file
            filepath = os.path.join("_workproduct", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(workproduct_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved editor work product to {filepath}")
            self.console.print(f"[green]Editor work product saved to {filename}[/]")
            
        except Exception as e:
            logger.error(f"Error saving editor work product: {str(e)}")
            self.console.print(f"[red]Failed to save editor work product: {str(e)}[/]")

    async def _retry_with_backoff(self, func, max_retries: int = 2):
        """
        Retry an async function with exponential backoff
        
        Args:
            func: Async function to retry
            max_retries: Maximum number of retry attempts
            
        Returns:
            Function result
        """
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries:
                    raise
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)