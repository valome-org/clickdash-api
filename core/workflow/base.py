"""
Base workflow interfaces and types.

This module defines the fundamental interfaces and data types used
throughout the user validation and approval workflow system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class WorkflowStep(str, Enum):
    """Steps in the user validation workflow."""
    DATA_INGESTION = "data_ingestion"
    AI_ANALYSIS = "ai_analysis"
    PREVIEW_GENERATION = "preview_generation"
    USER_REVIEW = "user_review"
    USER_APPROVAL = "user_approval"
    DASHBOARD_GENERATION = "dashboard_generation"
    FEEDBACK_COLLECTION = "feedback_collection"
    COMPLETED = "completed"


class WorkflowState(str, Enum):
    """Workflow execution states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_USER = "waiting_for_user"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    """User approval status for recommendations."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPROVED_WITH_CHANGES = "approved_with_changes"
    REQUIRES_REVISION = "requires_revision"


class WorkflowContext(BaseModel):
    """Context information for workflow execution."""

    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Workflow state
    current_step: WorkflowStep = Field(default=WorkflowStep.DATA_INGESTION)
    workflow_state: WorkflowState = Field(default=WorkflowState.PENDING)

    # Data context
    source_data: Optional[Dict[str, Any]] = None
    analysis_context: Optional[Dict[str, Any]] = None

    # User preferences
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    approval_requirements: Dict[str, Any] = Field(default_factory=dict)

    # Workflow metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # Progress tracking
    step_history: List[Dict[str, Any]] = Field(default_factory=list)
    approval_history: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseWorkflowStep(ABC):
    """
    Base class for all workflow steps.
    """

    def __init__(self, step_id: str, step_type: WorkflowStep):
        self.step_id = step_id
        self.step_type = step_type
        self.context: Optional[WorkflowContext] = None

    @abstractmethod
    async def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """Execute the workflow step."""
        pass

    @abstractmethod
    async def validate_inputs(self, context: WorkflowContext, **kwargs) -> bool:
        """Validate inputs before execution."""
        pass

    async def can_execute(self, context: WorkflowContext) -> bool:
        """Check if step can be executed in current context."""
        return context.current_step == self.step_type

    async def on_success(self, context: WorkflowContext, result: Dict[str, Any]):
        """Handle successful step execution."""
        context.step_history.append({
            "step": self.step_type.value,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "result_summary": self._summarize_result(result)
        })
        context.updated_at = datetime.utcnow()

    async def on_failure(self, context: WorkflowContext, error: Exception):
        """Handle failed step execution."""
        context.step_history.append({
            "step": self.step_type.value,
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(error)
        })
        context.workflow_state = WorkflowState.FAILED
        context.updated_at = datetime.utcnow()

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Generate a summary of the step result."""
        return f"Step {self.step_type.value} completed successfully"


class WorkflowValidator(ABC):
    """Base class for workflow validation."""

    @abstractmethod
    async def validate_step_transition(
        self,
        from_step: WorkflowStep,
        to_step: WorkflowStep,
        context: WorkflowContext
    ) -> bool:
        """Validate if step transition is allowed."""
        pass

    @abstractmethod
    async def validate_user_approval(
        self,
        approval_data: Dict[str, Any],
        context: WorkflowContext
    ) -> bool:
        """Validate user approval data."""
        pass


class WorkflowEventHandler(ABC):
    """Base class for workflow event handling."""

    @abstractmethod
    async def on_workflow_started(self, context: WorkflowContext):
        """Handle workflow start event."""
        pass

    @abstractmethod
    async def on_step_completed(self, step: WorkflowStep, context: WorkflowContext):
        """Handle step completion event."""
        pass

    @abstractmethod
    async def on_user_approval_required(self, context: WorkflowContext):
        """Handle user approval required event."""
        pass

    @abstractmethod
    async def on_workflow_completed(self, context: WorkflowContext):
        """Handle workflow completion event."""
        pass
