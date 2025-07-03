from typing import List
import httpx

from app.models.user import User
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.core.exceptions import AppException
from app.config import settings


class FeedbackService:
    def __init__(self):
        self.github_token = settings.GITHUB_TOKEN
        self.github_owner = settings.GITHUB_OWNER
        self.github_repo = settings.GITHUB_REPO
        
        if not self.github_token:
            raise AppException("GitHub token not configured", status_code=500, error_code="CONFIG_ERROR")

    async def create_github_issue(
        self, 
        feedback: FeedbackRequest, 
        current_user: User = None
    ) -> FeedbackResponse:
        """Create a GitHub issue from user feedback"""
        try:
            # Prepare issue data
            title = self._generate_issue_title(feedback.type, feedback.description)
            labels = self._get_issue_labels(feedback.type)
            body = self._format_issue_body(feedback, current_user)

            # Create GitHub issue using httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/issues",
                    headers={
                        "Authorization": f"Bearer {self.github_token}",
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                    json={
                        "title": title,
                        "body": body,
                        "labels": labels,
                    }
                )

                if response.status_code != 201:
                    raise AppException(f"Failed to create GitHub issue: {response.text}", status_code=502, error_code="GITHUB_API_ERROR")

                issue_data = response.json()

                return FeedbackResponse(
                    success=True,
                    issue_number=issue_data["number"],
                    issue_url=issue_data["html_url"]
                )

        except httpx.RequestError as e:
            raise AppException(f"Network error while creating GitHub issue: {str(e)}", status_code=502, error_code="NETWORK_ERROR")
        except Exception as e:
            raise AppException(f"Unexpected error while creating GitHub issue: {str(e)}", status_code=500, error_code="INTERNAL_ERROR")

    def _generate_issue_title(self, feedback_type: str, description: str) -> str:
        """Generate a concise title for the GitHub issue"""
        prefix_map = {
            "bug": "🐛 Bug:",
            "feature": "✨ Feature Request:",
            "translation": "🌐 Translation:"
        }
        
        prefix = prefix_map.get(feedback_type, "Feedback:")
        
        # Extract first line and limit to 60 characters
        first_line = description.strip().split('\n')[0]
        if len(first_line) > 60:
            first_line = first_line[:57] + "..."
        
        return f"{prefix} {first_line}"

    def _get_issue_labels(self, feedback_type: str) -> List[str]:
        """Get appropriate labels for the issue type"""
        base_labels = ["user-feedback"]
        
        type_labels = {
            "bug": ["bug"],
            "feature": ["enhancement"],
            "translation": ["documentation", "i18n"]
        }
        
        return base_labels + type_labels.get(feedback_type, [])

    def _format_issue_body(self, feedback: FeedbackRequest, user: User = None) -> str:
        """Format the issue body with all relevant information"""
        issue_type = {
            "bug": "Bug Report",
            "feature": "Feature Request",
            "translation": "Translation Issue"
        }.get(feedback.type, "Feedback")

        # Get user role names
        user_roles = "N/A"
        if user and hasattr(user, 'user_roles'):
            role_names = [ur.role.name for ur in user.user_roles if ur.role]
            user_roles = ", ".join(role_names) if role_names else "No roles assigned"
        
        # Get tenant name
        tenant_name = "N/A"
        if user and hasattr(user, 'tenant') and user.tenant:
            tenant_name = user.tenant.name
        
        # Check if super admin
        is_super_admin = user.is_super_admin if user and hasattr(user, 'is_super_admin') else False

        return f"""## {issue_type}

### Description
{feedback.description}

### User Information
- **Email**: {feedback.user_email}
- **User ID**: {feedback.user_id or "N/A"}
- **Roles**: {user_roles}
- **Tenant**: {tenant_name}
- **Super Admin**: {is_super_admin}

### Context
- **Page**: {feedback.current_page}
- **Timestamp**: {feedback.timestamp.isoformat()}
- **Screen Resolution**: {feedback.screen_resolution}

### Browser Information
```
{feedback.user_agent}
```

---
*This issue was automatically created via the in-app feedback widget*"""