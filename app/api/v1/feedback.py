from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.dependencies import get_current_active_user, get_db
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import FeedbackService
from app.core.exceptions import AppException

router = APIRouter(
    prefix="/feedback",
    tags=["feedback"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FeedbackResponse:
    """
    Submit user feedback which creates a GitHub issue.
    
    The feedback can be:
    - Bug report
    - Feature request
    - Translation issue
    
    The issue will be created in the frontend repository with appropriate labels
    and all relevant user context.
    """
    try:
        service = FeedbackService()
        return await service.create_github_issue(feedback, current_user)
    except AppException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to submit feedback")