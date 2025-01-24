import os
import json
from datetime import datetime
from typing import List, Optional, cast
from openai import AsyncOpenAI
from loguru import logger
from rich.console import Console
from pydantic import BaseModel, Field
from enum import Enum, auto

from ..models import DocumentState, EditorResponse, JudgeFeedback, Decision

class JudgeReviewResponse(BaseModel):
    """Structured response for document review"""
    feedback: str = Field(..., description="Detailed feedback about the document changes")
    recommendations: List[str] = Field(default_factory=list, description="List of specific recommendations for improvement")
    decision: Decision = Field(..., description="Decision whether to approve or revise")
    critique_severity: int = Field(default=0, ge=0, le=10, description="Severity of critique (0-10)")

class JudgeAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize judge agent
        
        Args:
            model: OpenAI model to use for review
        """
        self.model = model
        self.client = AsyncOpenAI()
        self.console = Console()

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
            system_message = """You are a rigorous, expert-level document quality assessor. 
            Your task is to provide an exhaustive, critical review of the document:

            REVIEW CRITERIA:
            1. Content Depth and Accuracy
               - Verify factual correctness
               - Assess comprehensiveness of topic coverage
               - Identify potential knowledge gaps

            2. Structural and Organizational Analysis
               - Evaluate logical flow and coherence
               - Check for clear section transitions
               - Assess argument progression

            3. Language and Communication
               - Analyze clarity and readability
               - Check for conciseness
               - Identify complex or unclear passages

            4. Source and Reference Quality
               - Evaluate source credibility
               - Check for balanced perspective
               - Identify potential bias

            5. Technical and Scholarly Rigor
               - Assess technical accuracy
               - Check for appropriate technical depth
               - Verify use of domain-specific terminology

            PROVIDE:
            - Detailed, constructive feedback
            - Specific, actionable recommendations
            - Clear decision on document quality
            """

            # Prepare the review prompt
            user_message = f"""DOCUMENT REVIEW REQUEST

            ORIGINAL DOCUMENT:
            Topics: {', '.join(original.topics)}
            Version: {original.version}
            Content Length: {len(original.content)} characters

            EDITED DOCUMENT:
            Version: {edited.version}
            Revision Notes: {chr(10).join(edited.revision_notes) if edited.revision_notes else 'No revision notes'}
            Content Length: {len(edited.content)} characters

            REVIEW INSTRUCTIONS:
            1. Perform a comprehensive, multi-dimensional analysis
            2. Provide granular, specific recommendations
            3. Decide whether the document needs further revision
            4. Rate the critique severity (0-10)

            Deliver a structured, professional, and actionable review."""

            # Call OpenAI API with detailed response
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                max_tokens=1500
            )

            # Parse the response
            response_text = cast(str, completion.choices[0].message.content)
            if not response_text:
                logger.error("Empty response from OpenAI")
                raise ValueError("Empty response from OpenAI")
                
            try:
                review_data = json.loads(response_text)
                
                # Create JudgeReviewResponse from parsed data
                review = JudgeReviewResponse(
                    feedback=review_data.get('feedback', 'No detailed feedback provided'),
                    recommendations=review_data.get('recommendations', []),
                    decision=Decision.REVISE if review_data.get('decision', 'REVISE') == 'REVISE' else Decision.APPROVE,
                    critique_severity=review_data.get('critique_severity', 5)
                )
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse judge response: {str(e)}")
                raise ValueError(f"Invalid JSON response from judge: {str(e)}")

            # Save recommendations to _workproduct
            await self._save_judge_recommendations(original.topics[0], review)

            return JudgeFeedback(
                approved=review.decision == Decision.APPROVE,
                recommendations=review.recommendations,
                revision_required=review.decision == Decision.REVISE
            )

        except Exception as e:
            logger.error(f"Error during document review: {str(e)}")
            raise

    async def _save_judge_recommendations(self, topic: str, review: JudgeReviewResponse) -> None:
        """
        Save judge's recommendations to a JSON file in _workproduct
        
        Args:
            topic: Document topic
            review: Judge's review response
        """
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            topic_slug = "_".join(topic.lower().split())[:50]
            filename = f"02_judge_recommendations_{topic_slug}_{timestamp}.json"
            
            # Ensure _workproduct directory exists
            os.makedirs("_workproduct", exist_ok=True)
            
            # Prepare recommendation data
            recommendation_data = {
                "topic": topic,
                "timestamp": timestamp,
                "feedback": review.feedback,
                "recommendations": review.recommendations,
                "decision": review.decision.name,
                "critique_severity": review.critique_severity
            }
            
            # Save file
            filepath = os.path.join("_workproduct", filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(recommendation_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved judge recommendations to {filepath}")
            self.console.print(f"[green]Judge recommendations saved to {filename}[/]")
            
        except Exception as e:
            logger.error(f"Error saving judge recommendations: {str(e)}")
            self.console.print(f"[red]Failed to save judge recommendations: {str(e)}[/]")