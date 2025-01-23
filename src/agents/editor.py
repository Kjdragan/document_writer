from typing import List
import openai
from loguru import logger
from ..models import DocumentState, EditorResponse

class EditorAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize editor agent
        
        Args:
            model: OpenAI model to use for processing
        """
        self.model = model

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
            system_message = """You are an expert editor focused on improving document clarity, 
            coherence, and structure. Analyze the provided content and make improvements while 
            maintaining accuracy and key information. Focus on:
            1. Clear narrative flow
            2. Logical structure
            3. Consistent style
            4. Proper transitions between topics
            5. Elimination of redundancy"""

            # Prepare the editing prompt
            user_message = f"""Please review and improve the following document:
            
            Topics: {', '.join(doc.topics)}
            Version: {doc.version}
            
            Content:
            {doc.content}
            
            Provide the improved version maintaining all key information but enhancing readability and structure."""

            # Call OpenAI API
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )

            # Extract improved content
            improved_content = response.choices[0].message.content.strip()

            # Get explanation of changes
            explanation_response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "List the key improvements made to the document."},
                    {"role": "user", "content": f"Original:\n{doc.content}\n\nImproved:\n{improved_content}"}
                ],
                temperature=0.7
            )

            revision_notes = explanation_response.choices[0].message.content.strip().split('\n')

            return EditorResponse(
                content=improved_content,
                revision_notes=revision_notes,
                version=doc.version + 1
            )

        except Exception as e:
            logger.error(f"Error during document editing: {str(e)}")
            raise

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