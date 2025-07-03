from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    type: Literal["bug", "feature", "translation"] = Field(..., description="Type of feedback")
    description: str = Field(..., min_length=10, description="Detailed description of the issue or request")
    user_email: str = Field(..., description="Email of the user submitting feedback")
    user_id: Optional[str] = Field(None, description="ID of the authenticated user")
    current_page: str = Field(..., description="Current page URL where feedback was submitted")
    user_agent: str = Field(..., description="Browser user agent string")
    screen_resolution: str = Field(..., description="Screen resolution of the user")
    timestamp: datetime = Field(..., description="Timestamp when feedback was submitted")


class FeedbackResponse(BaseModel):
    success: bool
    issue_number: int
    issue_url: str
    message: str = "Feedback submitted successfully"