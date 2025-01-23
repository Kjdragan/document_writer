import openai
from loguru import logger
from ..models import DocumentState, EditorResponse, JudgeFeedback

class JudgeAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize judge agent
        
        Args:
            model: OpenAI model to use for review
        """
        self.model = model

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

            # Call OpenAI API
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7
            )

            # Analyze the feedback to determine approval
            feedback_text = response.choices[0].message.content.strip()
            
            # Get specific recommendations
            recommendations_response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract specific recommendations from the review as a list."},
                    {"role": "user", "content": feedback_text}
                ],
                temperature=0.7
            )
            
            recommendations = recommendations_response.choices[0].message.content.strip().split('\n')

            # Determine if revisions are required
            approval_response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Based on the review, should the document be approved or does it need revision? Respond with 'APPROVE' or 'REVISE'."},
                    {"role": "user", "content": feedback_text}
                ],
                temperature=0.3
            )
            
            decision = approval_response.choices[0].message.content.strip()
            approved = decision == "APPROVE"
            revision_required = not approved

            return JudgeFeedback(
                approved=approved,
                recommendations=recommendations,
                revision_required=revision_required
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
                await asyncio.sleep(wait_time)