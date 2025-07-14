"""
Core workflow management system.

This module provides workflow components for user validation and approval including:
- Preview generation system
- User approval interfaces
- Feedback collection system
"""

# Import base classes first
from .base import (
    WorkflowStep,
    WorkflowState,
    ApprovalStatus,
    WorkflowContext,
    BaseWorkflowStep
)

# Import specific modules
try:
    from .preview_generator import (
        PreviewGenerator,
        DashboardPreview,
        PreviewRequest,
        PreviewResult
    )
except ImportError:
    pass

try:
    from .approval_workflow import (
        ApprovalWorkflow,
        ApprovalRequest,
        ApprovalDecision,
        ApprovalResult,
        ApprovalType
    )
except ImportError:
    pass

try:
    from .feedback_collector import (
        FeedbackCollector,
        UserFeedback,
        FeedbackRequest,
        FeedbackAnalysis,
        FeedbackType
    )
except ImportError:
    pass

__all__ = [
    # Base workflow components
    "WorkflowStep",
    "WorkflowState",
    "ApprovalStatus",
    "WorkflowContext",
    "BaseWorkflowStep",

    # Preview generation
    "PreviewGenerator",
    "DashboardPreview",
    "PreviewRequest",
    "PreviewResult",

    # Approval workflow
    "ApprovalWorkflow",
    "ApprovalRequest",
    "ApprovalDecision",
    "ApprovalResult",
    "ApprovalType",

    # Feedback collection
    "FeedbackCollector",
    "UserFeedback",
    "FeedbackRequest",
    "FeedbackAnalysis",
    "FeedbackType"
]
