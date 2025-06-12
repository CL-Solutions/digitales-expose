"""ChatGPT Service for generating micro location data using OpenAI Assistants API."""

import json
import time
from typing import Dict, Any
from sqlalchemy.orm import Session
from openai import OpenAI
from app.config import settings
from app.core.exceptions import AppException
from app.models.business import Project
from app.utils.audit import AuditLogger
import logging

logger = logging.getLogger(__name__)


class ChatGPTService:
    """Service for interacting with OpenAI Assistants API to generate micro location data."""

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise AppException(
                detail="OpenAI API key not configured",
                status_code=500
            )
        
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.assistant_id = settings.OPENAI_ASSISTANT_ID
        self.audit_logger = AuditLogger()

    def generate_micro_location_data(
        self,
        db: Session,
        project: Project,
        user_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Generate micro location data for a project using OpenAI Assistants API.
        
        Args:
            db: Database session
            project: Project object with location data
            user_id: ID of the user making the request
            tenant_id: Tenant ID
            
        Returns:
            Dict containing micro location data in the format:
            {
                "einkaufsmoeglichkeiten": [...],
                "freizeitmoeglichkeiten": [...],
                "infrastruktur": [...]
            }
        """
        if not self.assistant_id:
            logger.error("OpenAI Assistant ID not configured")
            raise AppException(
                detail="ChatGPT Assistant not configured. Please set OPENAI_ASSISTANT_ID in environment variables.",
                status_code=500
            )

        try:
            # Create a thread
            thread = self.client.beta.threads.create()
            
            # Add message to thread
            message_content = f"Adresse: {project.street} {project.house_number}, {project.zip_code} {project.city}, {project.state}"
            
            message = self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message_content
            )
            
            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            # Wait for completion
            max_attempts = 30  # 30 seconds timeout
            for _ in range(max_attempts):
                time.sleep(1)
                
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                
                if run_status.status == "completed":
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    logger.error(f"Assistant run failed with status: {run_status.status}")
                    raise AppException(
                        detail="Assistant failed to generate response",
                        status_code=500
                    )
            else:
                raise AppException(
                    detail="Timeout waiting for assistant response",
                    status_code=500
                )
            
            # Get messages
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # Find the assistant's response
            for message in messages.data:
                if message.role == "assistant":
                    # Extract text content
                    content = message.content[0].text.value
                    
                    # Parse JSON response
                    try:
                        micro_location_data = json.loads(content)
                        
                        # Validate expected structure
                        required_keys = ["einkaufsmoeglichkeiten", "freizeitmoeglichkeiten", "infrastruktur"]
                        if all(key in micro_location_data for key in required_keys):
                            # Log successful generation
                            self.audit_logger.log_business_event(
                                db=db,
                                action="MICRO_LOCATION_GENERATED",
                                user_id=user_id,
                                tenant_id=tenant_id,
                                resource_type="project",
                                resource_id=project.id,
                                new_values={"location": f"{project.street} {project.house_number}, {project.city}"}
                            )
                            
                            return micro_location_data
                        else:
                            logger.error(f"Invalid response structure: {micro_location_data}")
                            raise AppException(
                                detail="Invalid response format from assistant",
                                status_code=500
                            )
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {content}")
                        raise AppException(
                            detail="Failed to parse assistant response",
                            status_code=500
                        )
            
            raise AppException(
                detail="No response from assistant",
                status_code=500
            )
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating micro location: {str(e)}")
            raise AppException(
                detail="Failed to generate micro location data",
                status_code=500
            )

    @staticmethod
    def update_project_micro_location(
        db: Session,
        project: Project,
        micro_location_data: Dict[str, Any]
    ) -> Project:
        """
        Update a project with micro location data.
        
        Args:
            db: Database session
            project: Project to update
            micro_location_data: Micro location data to save
            
        Returns:
            Updated project
        """
        project.micro_location = micro_location_data
        db.commit()
        db.refresh(project)
        return project