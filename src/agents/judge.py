from typing import List
from openai import AsyncOpenAI
from loguru import logger
from pydantic import BaseModel, Field
from ..models import DocumentState, EditorResponse, JudgeFeedback, Decision
from asyncio import sleep as asyncio_sleep

class JudgeReviewResponse(BaseModel):
    """Structured response for document review"""
    feedback: str = Field(..., description="Detailed feedback about the document changes")
    recommendations: List[str] = Field(..., description="List of specific recommendations for improvement")
    decision: Decision = Field(..., description="Decision whether to approve or revise")

class JudgeAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize judge agent
        
        Args:
            model: OpenAI model to use for review
        """
        self.model = model
        self.client = AsyncOpenAI()

    async def review_document(self, original: DocumentState, edited: EditorResponse) -> JudgeFeedback:
        """
        Review changes made by the editor and provide structured feedback
        
        Args:
            original: Original document state
            edited: Editor's response with changes
            
        Returns:
            Structured feedback about the changes
        """
        try:
            # Prepare system message for the judge role
            system_message = """You are an expert judge evaluating document improvements. 
            Analyze the original and edited versions to assess:
            1. Content accuracy and completeness
            2. Structural improvements
            3. Clarity and readability
            4. Proper handling of topics
            5. Overall document quality
            
            Provide specific recommendations if improvements are needed."""

            # Prepare the review prompt
            user_message = f"""Review the following document versions:
            
            Original Document:
            Topics: {', '.join(original.topics)}
            Version: {original.version}
            Content:
            {original.content}
            
            Edited Document:
            Version: {edited.version}
            Changes Made:
            {chr(10).join(edited.revision_notes) if edited.revision_notes else 'No revision notes provided'}
            
            Content:
            {edited.content}
            
            Evaluate the changes and provide structured feedback."""

            # Call OpenAI API with response format
            completion = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                response_format=JudgeReviewResponse,
            )

            # Get the parsed response
            review = completion.choices[0].message.parsed
            if not review:
                logger.error("Model refused to provide review")
                raise ValueError("Model refused to provide review")

            return JudgeFeedback(
                approved=review.decision == Decision.APPROVE,
                recommendations=review.recommendations,
                revision_required=review.decision == Decision.REVISE
            )

        except Exception as e:
            logger.error(f"Error during document review: {str(e)}")
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
                await asyncio_sleep(wait_time)