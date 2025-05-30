# ================================
# BUSINESS LOGIC SCHEMAS (schemas/business.py)
# ================================

from pydantic import Field
from typing import Optional, List, Literal
from uuid import UUID
from app.schemas.base import BaseSchema, TimestampMixin, AuditMixin, PaginationParams, SortParams, SearchParams

# ================================
# PROJECT SCHEMAS (schemas/project.py)
# ================================

class ProjectBase(BaseSchema):
    """Base Project Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    status: Literal["active", "completed", "archived"] = Field(default="active", description="Project status")

class ProjectCreate(ProjectBase):
    """Schema für Project-Erstellung"""
    pass

class ProjectUpdate(BaseSchema):
    """Schema für Project-Updates"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[Literal["active", "completed", "archived"]] = None

class ProjectResponse(ProjectBase, TimestampMixin, AuditMixin):
    """Schema für Project-Responses"""
    id: UUID
    tenant_id: UUID
    
    # Related data
    document_count: Optional[int] = Field(None, description="Number of documents in project")
    recent_activity: Optional[str] = Field(None, description="Recent activity timestamp")

class ProjectDetailResponse(ProjectResponse):
    """Extended Project Response mit Additional Data"""
    creator_name: Optional[str] = Field(None, description="Name of project creator")
    updater_name: Optional[str] = Field(None, description="Name of last updater")
    documents: List['DocumentResponse'] = Field(default_factory=list)
    team_members: List[dict] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

class ProjectListResponse(BaseSchema):
    """Schema für Project-Listen"""
    projects: List[ProjectResponse]
    total: int
    page: int
    page_size: int

class ProjectFilterParams(PaginationParams, SortParams, SearchParams):
    """Schema für Project-Filtering"""
    status: Optional[Literal["active", "completed", "archived"]] = None
    created_by: Optional[UUID] = None
    has_documents: Optional[bool] = None
    created_after: Optional[str] = None
    created_before: Optional[str] = None

class ProjectStatsResponse(BaseSchema):
    """Schema für Project Statistics"""
    total_projects: int
    active_projects: int
    completed_projects: int
    archived_projects: int
    projects_by_month: dict[str, int]
    average_documents_per_project: float
    most_active_projects: List[dict]

# ================================
# DOCUMENT SCHEMAS (schemas/document.py)
# ================================

class DocumentBase(BaseSchema):
    """Base Document Schema"""
    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    content: Optional[str] = Field(None, description="Document content")

class DocumentCreate(DocumentBase):
    """Schema für Document-Erstellung"""
    project_id: Optional[UUID] = Field(None, description="Associated project ID")
    tags: List[str] = Field(default_factory=list, description="Document tags")

class DocumentUpdate(BaseSchema):
    """Schema für Document-Updates"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    project_id: Optional[UUID] = None
    tags: Optional[List[str]] = None

class DocumentResponse(DocumentBase, TimestampMixin, AuditMixin):
    """Schema für Document-Responses"""
    id: UUID
    tenant_id: UUID
    project_id: Optional[UUID]
    
    # File Information
    file_path: Optional[str] = None
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = None
    
    # Additional metadata
    tags: List[str] = Field(default_factory=list)
    version: int = Field(default=1, description="Document version")

class DocumentDetailResponse(DocumentResponse):
    """Extended Document Response"""
    creator_name: Optional[str] = Field(None, description="Name of document creator")
    updater_name: Optional[str] = Field(None, description="Name of last updater")
    project_name: Optional[str] = Field(None, description="Associated project name")
    download_url: Optional[str] = Field(None, description="Download URL")
    preview_url: Optional[str] = Field(None, description="Preview URL")

class DocumentListResponse(BaseSchema):
    """Schema für Document-Listen"""
    documents: List[DocumentResponse]
    total: int
    page: int
    page_size: int

class DocumentFilterParams(PaginationParams, SortParams, SearchParams):
    """Schema für Document-Filtering"""
    project_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    mime_type: Optional[str] = None
    has_content: Optional[bool] = None
    tags: Optional[List[str]] = None
    file_size_min: Optional[int] = None
    file_size_max: Optional[int] = None

class DocumentUploadRequest(BaseSchema):
    """Schema für Document Upload"""
    title: str = Field(..., min_length=1, max_length=255)
    project_id: Optional[UUID] = None
    tags: List[str] = Field(default_factory=list)
    replace_existing: bool = Field(default=False, description="Replace existing document with same name")

class DocumentUploadResponse(BaseSchema):
    """Schema für Document Upload Response"""
    document_id: UUID
    upload_url: str = Field(..., description="Pre-signed upload URL")
    fields: dict = Field(..., description="Form fields for upload")
    expires_at: str = Field(..., description="Upload URL expiration")

class DocumentVersionResponse(BaseSchema, TimestampMixin):
    """Schema für Document Versions"""
    id: UUID
    document_id: UUID
    version_number: int
    title: str
    file_size: Optional[int]
    created_by: UUID
    creator_name: Optional[str]
    change_summary: Optional[str]

# ================================
# FILE MANAGEMENT SCHEMAS
# ================================

class FileUploadRequest(BaseSchema):
    """Schema für File Upload Request"""
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="File content type")
    file_size: int = Field(..., ge=1, description="File size in bytes")

class FileUploadResponse(BaseSchema):
    """Schema für File Upload Response"""
    file_id: UUID
    upload_url: str
    expires_in: int = Field(description="Upload URL expiry in seconds")

class FileDownloadResponse(BaseSchema):
    """Schema für File Download Response"""
    download_url: str
    expires_in: int = Field(description="Download URL expiry in seconds")
    file_size: int
    content_type: str

# ================================
# COLLABORATION SCHEMAS (Future Extension)
# ================================

class CommentBase(BaseSchema):
    """Base Comment Schema"""
    content: str = Field(..., min_length=1, max_length=1000, description="Comment content")
    parent_comment_id: Optional[UUID] = Field(None, description="Parent comment for replies")

class CommentCreate(CommentBase):
    """Schema für Comment Creation"""
    pass

class CommentResponse(CommentBase, TimestampMixin):
    """Schema für Comment Response"""
    id: UUID
    document_id: UUID
    author_id: UUID
    author_name: str
    replies: List['CommentResponse'] = Field(default_factory=list)
    is_resolved: bool = Field(default=False)

class ShareRequest(BaseSchema):
    """Schema für Resource Sharing"""
    resource_type: Literal["project", "document"] = Field(..., description="Type of resource to share")
    resource_id: UUID = Field(..., description="Resource ID")
    user_ids: List[UUID] = Field(..., min_items=1, description="User IDs to share with")
    permission_level: Literal["read", "write", "admin"] = Field(..., description="Permission level")
    expires_at: Optional[str] = Field(None, description="Share expiration")
    message: Optional[str] = Field(None, description="Optional message")

class ShareResponse(BaseSchema, TimestampMixin):
    """Schema für Share Response"""
    id: UUID
    resource_type: str
    resource_id: UUID
    shared_with_user_id: UUID
    shared_by_user_id: UUID
    permission_level: str
    expires_at: Optional[str]
    is_active: bool

# ================================
# ACTIVITY & NOTIFICATIONS SCHEMAS
# ================================

class ActivityBase(BaseSchema):
    """Base Activity Schema"""
    activity_type: str = Field(..., description="Type of activity")
    resource_type: str = Field(..., description="Type of resource (project, document, etc.)")
    resource_id: UUID = Field(..., description="Resource ID")
    description: str = Field(..., description="Activity description")

class ActivityResponse(ActivityBase, TimestampMixin):
    """Schema für Activity Response"""
    id: UUID
    user_id: UUID
    user_name: str
    tenant_id: UUID
    metadata: dict = Field(default_factory=dict, description="Additional activity metadata")

class ActivityFeedResponse(BaseSchema):
    """Schema für Activity Feed"""
    activities: List[ActivityResponse]
    total: int
    has_more: bool

class NotificationBase(BaseSchema):
    """Base Notification Schema"""
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    message: str = Field(..., min_length=1, max_length=1000, description="Notification message")
    notification_type: str = Field(..., description="Type of notification")
    priority: Literal["low", "medium", "high", "urgent"] = Field(default="medium")

class NotificationResponse(NotificationBase, TimestampMixin):
    """Schema für Notification Response"""
    id: UUID
    user_id: UUID
    is_read: bool = Field(default=False)
    read_at: Optional[str] = None
    action_url: Optional[str] = Field(None, description="URL for notification action")
    metadata: dict = Field(default_factory=dict)

class NotificationListResponse(BaseSchema):
    """Schema für Notification List"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int

class NotificationMarkReadRequest(BaseSchema):
    """Schema für Marking Notifications as Read"""
    notification_ids: List[UUID] = Field(..., min_items=1, description="Notification IDs to mark as read")

# ================================
# DASHBOARD & ANALYTICS SCHEMAS
# ================================

class DashboardStatsResponse(BaseSchema):
    """Schema für Dashboard Statistics"""
    total_projects: int
    active_projects: int
    total_documents: int
    recent_documents: int
    team_members: int
    storage_used: int = Field(description="Storage used in bytes")
    storage_limit: int = Field(description="Storage limit in bytes")

class ProjectAnalyticsResponse(BaseSchema):
    """Schema für Project Analytics"""
    project_id: UUID
    project_name: str
    total_documents: int
    active_contributors: int
    last_activity: Optional[str]
    creation_trend: List[dict] = Field(description="Document creation trend over time")
    contributor_activity: List[dict] = Field(description="Activity by contributors")

class DocumentAnalyticsResponse(BaseSchema):
    """Schema für Document Analytics"""
    document_id: UUID
    document_title: str
    view_count: int
    edit_count: int
    download_count: int
    last_accessed: Optional[str]
    access_trend: List[dict] = Field(description="Access trend over time")

class TenantAnalyticsResponse(BaseSchema):
    """Schema für Tenant Analytics"""
    tenant_id: UUID
    user_growth: List[dict] = Field(description="User growth over time")
    project_activity: List[dict] = Field(description="Project activity metrics")
    storage_usage: List[dict] = Field(description="Storage usage over time")
    feature_usage: dict = Field(description="Feature usage statistics")

# ================================
# SEARCH SCHEMAS
# ================================

class SearchRequest(BaseSchema):
    """Schema für Search Request"""
    query: str = Field(..., min_length=1, description="Search query")
    resource_types: List[Literal["project", "document", "user"]] = Field(default_factory=lambda: ["project", "document"], description="Types of resources to search")
    filters: dict = Field(default_factory=dict, description="Additional search filters")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results per resource type")

class SearchResultItem(BaseSchema):
    """Schema für Search Result Item"""
    id: UUID
    type: str = Field(description="Resource type")
    title: str
    description: Optional[str]
    url: str = Field(description="URL to the resource")
    relevance_score: float = Field(description="Search relevance score")
    metadata: dict = Field(default_factory=dict)

class SearchResponse(BaseSchema):
    """Schema für Search Response"""
    query: str
    total_results: int
    results_by_type: dict[str, List[SearchResultItem]]
    search_time_ms: int = Field(description="Search execution time in milliseconds")
    suggestions: List[str] = Field(default_factory=list, description="Search suggestions")

# ================================
# EXPORT & IMPORT SCHEMAS
# ================================

class ExportRequest(BaseSchema):
    """Schema für Export Request"""
    resource_type: Literal["project", "document", "tenant_data"] = Field(..., description="Type of data to export")
    resource_ids: Optional[List[UUID]] = Field(None, description="Specific resource IDs (if not provided, exports all)")
    export_format: Literal["json", "csv", "xlsx", "pdf"] = Field(default="json", description="Export format")
    include_metadata: bool = Field(default=True, description="Include metadata in export")
    include_content: bool = Field(default=True, description="Include content in export")

class ExportResponse(BaseSchema):
    """Schema für Export Response"""
    export_id: UUID
    status: Literal["pending", "processing", "completed", "failed"] = Field(..., description="Export status")
    download_url: Optional[str] = Field(None, description="Download URL when completed")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    expires_at: Optional[str] = Field(None, description="Download URL expiration")
    created_at: str

class ImportRequest(BaseSchema):
    """Schema für Import Request"""
    import_type: Literal["projects", "documents", "users"] = Field(..., description="Type of data to import")
    file_url: str = Field(..., description="URL of file to import")
    import_settings: dict = Field(default_factory=dict, description="Import configuration")
    merge_strategy: Literal["skip", "update", "replace"] = Field(default="skip", description="Strategy for existing data")

class ImportResponse(BaseSchema):
    """Schema für Import Response"""
    import_id: UUID
    status: Literal["pending", "processing", "completed", "failed"] = Field(..., description="Import status")
    total_records: Optional[int] = None
    processed_records: Optional[int] = None
    success_count: Optional[int] = None
    error_count: Optional[int] = None
    errors: List[dict] = Field(default_factory=list, description="Import errors")
    created_at: str

# ================================
# WORKFLOW & AUTOMATION SCHEMAS (Future Extension)
# ================================

class WorkflowTrigger(BaseSchema):
    """Schema für Workflow Trigger"""
    trigger_type: str = Field(..., description="Type of trigger")
    conditions: dict = Field(..., description="Trigger conditions")

class WorkflowAction(BaseSchema):
    """Schema für Workflow Action"""
    action_type: str = Field(..., description="Type of action")
    parameters: dict = Field(..., description="Action parameters")

class WorkflowRequest(BaseSchema):
    """Schema für Workflow Creation"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    triggers: List[WorkflowTrigger]
    actions: List[WorkflowAction]
    is_active: bool = Field(default=True)

class WorkflowResponse(WorkflowRequest, TimestampMixin):
    """Schema für Workflow Response"""
    id: UUID
    tenant_id: UUID
    created_by: UUID
    execution_count: int = Field(default=0)
    last_executed: Optional[str] = None

# ================================
# FORWARD REFERENCES
# ================================

# Update forward references for circular dependencies
ProjectDetailResponse.model_rebuild()
CommentResponse.model_rebuild()