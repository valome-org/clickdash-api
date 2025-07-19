"""
User Validation & Approval Workflow Router.

API endpoints for Phase 7 workflows including:
- Dashboard preview generation
- User approval processes
- Feedback collection
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import User
from database.connection import get_db
from dependencies.auth import get_current_active_user
from services.workflow_service import workflow_service
from models.dashboard import DashboardConfig
from utils.serialization import CustomJSONResponse
import logging
from services.workflow_db_service import workflow_db_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class StartWorkflowRequest(BaseModel):
    """Request to start a new workflow."""
    dashboard_config: DashboardConfig
    data: Dict[str, Any]
    ai_analysis: Dict[str, Any]
    alternatives: Optional[List[DashboardConfig]] = None


class WorkflowResponse(BaseModel):
    """Response with workflow information."""
    workflow_id: str
    current_step: str
    workflow_state: str
    created_at: str


class PreviewRequest(BaseModel):
    """Request for dashboard preview generation."""
    workflow_id: str
    preview_type: str = "interactive"
    quality: str = "medium"
    include_alternatives: bool = True


class ApprovalDecisionRequest(BaseModel):
    """Request for approval decision."""
    item_id: str
    decision_type: str
    approval_status: str
    user_notes: Optional[str] = None


class ProcessApprovalRequest(BaseModel):
    """Request to process approval decisions."""
    workflow_id: str
    approval_request_id: str
    decisions: List[ApprovalDecisionRequest]


class FeedbackRequest(BaseModel):
    """Request to submit feedback."""
    workflow_id: str
    feedback_type: str
    category: str
    title: str
    description: str
    satisfaction_rating: Optional[str] = None
    numeric_rating: Optional[float] = None
    what_worked_well: List[str] = Field(default_factory=list)
    what_needs_improvement: List[str] = Field(default_factory=list)
    suggested_changes: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    device_type: Optional[str] = None
    experience_level: Optional[str] = None
    time_spent_ms: Optional[float] = None


# Workflow Management Endpoints

@router.post("/workflow/start", response_model=WorkflowResponse)
async def start_workflow(
    request: StartWorkflowRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start a new dashboard approval workflow."""
    try:
        logger.info(f"Starting workflow for user {current_user.user_id}")

        context = await workflow_service.start_dashboard_approval_workflow(
            dashboard_config=request.dashboard_config,
            data=request.data,
            user=current_user,
            ai_analysis=request.ai_analysis,
            alternatives=request.alternatives,
            db=db
        )

        return WorkflowResponse(
            workflow_id=context.workflow_id,
            current_step=context.current_step.value,
            workflow_state=context.workflow_state.value,
            created_at=context.created_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to start workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )


@router.get("/workflow/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current workflow status."""
    try:
        status_info = await workflow_service.get_workflow_status(workflow_id, db)

        if "error" in status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=status_info["error"]
            )

        # Verify user owns this workflow
        if status_info.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workflow"
            )

        return CustomJSONResponse(content=status_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow status: {str(e)}"
        )


@router.get("/workflows/my")
async def get_my_workflows(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all workflows for the current user."""
    try:
        # Try database first, fallback to service method
        workflows = await workflow_service.get_user_workflows_from_db(getattr(current_user, 'user_id', ''), db)
        if not workflows:
            workflows = await workflow_service.get_user_workflows(getattr(current_user, 'user_id', ''))

        return CustomJSONResponse(content={
            "workflows": workflows,
            "total": len(workflows)
        })

    except Exception as e:
        logger.error(f"Failed to get user workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user workflows: {str(e)}"
        )


@router.delete("/workflow/{workflow_id}")
async def cancel_workflow(
    workflow_id: str,
    reason: str = "User requested cancellation",
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a workflow."""
    try:
        # Verify user owns this workflow
        status_info = await workflow_service.get_workflow_status(workflow_id)
        if "error" in status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        if status_info.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workflow"
            )

        success = await workflow_service.cancel_workflow(workflow_id, reason)

        if success:
            return CustomJSONResponse(content={
                "message": "Workflow cancelled successfully",
                "workflow_id": workflow_id
            })
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel workflow"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel workflow: {str(e)}"
        )


# Preview Generation Endpoints

@router.post("/workflow/preview")
async def generate_preview(
    request: PreviewRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Generate dashboard preview for user review."""
    try:
        # Verify user owns this workflow
        status_info = await workflow_service.get_workflow_status(request.workflow_id)
        if "error" in status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        if status_info.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workflow"
            )

        result = await workflow_service.generate_preview(
            workflow_id=request.workflow_id,
            preview_options={
                "preview_type": request.preview_type,
                "quality": request.quality,
                "include_alternatives": request.include_alternatives
            }
        )

        return CustomJSONResponse(content={
            "success": result.success,
            "preview": result.preview.dict() if result.preview else None,
            "generation_time_ms": result.generation_time_ms,
            "quality_score": result.quality_score,
            "issues": result.issues,
            "warnings": result.warnings,
            "recommendations": result.recommendations
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate preview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate preview: {str(e)}"
        )


# Approval Process Endpoints

@router.get("/workflow/{workflow_id}/approval-request")
async def get_approval_request(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get approval request for a workflow."""
    try:
        # Verify user owns this workflow
        status_info = await workflow_service.get_workflow_status(workflow_id)
        if "error" in status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        if status_info.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workflow"
            )

        approval_request = await workflow_service.request_user_approval(workflow_id)

        return CustomJSONResponse(content={
            "request_id": approval_request.request_id,
            "workflow_id": approval_request.workflow_id,
            "request_type": approval_request.request_type.value,
            "items": [
                {
                    "item_id": item.item_id,
                    "title": item.title,
                    "description": item.description,
                    "type": item.item_type.value,
                    "ai_reasoning": item.ai_reasoning,
                    "confidence_score": item.confidence_score,
                    "risk_assessment": item.risk_assessment,
                    "approval_guidance": item.approval_guidance,
                    "implications": item.implications,
                    "priority": item.priority,
                    "reversible": item.reversible,
                    "alternatives_count": len(item.alternatives)
                }
                for item in approval_request.items
            ],
            "urgency": approval_request.urgency,
            "deadline": approval_request.deadline.isoformat() if approval_request.deadline else None,
            "show_alternatives": approval_request.show_alternatives,
            "allow_modifications": approval_request.allow_modifications
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get approval request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get approval request: {str(e)}"
        )


@router.post("/workflow/approval/process")
async def process_approval(
    request: ProcessApprovalRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Process user approval decisions."""
    try:
        # Verify user owns this workflow
        status_info = await workflow_service.get_workflow_status(request.workflow_id)
        if "error" in status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )

        if status_info.get("user_id") != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this workflow"
            )

        # Convert decisions to dict format
        decisions = [decision.dict() for decision in request.decisions]

        result = await workflow_service.process_user_approval(
            workflow_id=request.workflow_id,
            approval_request_id=request.approval_request_id,
            decisions=decisions
        )

        return CustomJSONResponse(content={
            "success": result.success,
            "overall_status": result.overall_status.value,
            "approved_items": result.approved_items,
            "rejected_items": result.rejected_items,
            "modified_items": result.modified_items,
            "next_actions": result.next_actions,
            "implementation_plan": result.implementation_plan,
            "total_time_ms": result.total_time_ms
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process approval: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process approval: {str(e)}"
        )


@router.get("/approvals/pending")
async def get_pending_approvals(
    current_user: User = Depends(get_current_active_user)
):
    """Get all pending approval requests for the current user."""
    try:
        pending_approvals = await workflow_service.get_pending_approvals(getattr(current_user, 'user_id', ''))

        return CustomJSONResponse(content={
            "pending_approvals": [
                {
                    "request_id": req.request_id,
                    "workflow_id": req.workflow_id,
                    "request_type": req.request_type.value,
                    "items_count": len(req.items),
                    "urgency": req.urgency,
                    "deadline": req.deadline.isoformat() if req.deadline else None,
                    "created_at": req.created_at.isoformat()
                }
                for req in pending_approvals
            ],
            "total": len(pending_approvals)
        })

    except Exception as e:
        logger.error(f"Failed to get pending approvals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending approvals: {str(e)}"
        )


# Feedback Collection Endpoints

@router.post("/workflow/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Submit user feedback about a workflow."""
    try:
        feedback_data = request.dict()
        feedback_data["user_id"] = current_user.user_id

        feedback_id = await workflow_service.collect_feedback(
            workflow_id=request.workflow_id,
            feedback_data=feedback_data
        )

        return CustomJSONResponse(content={
            "message": "Feedback submitted successfully",
            "feedback_id": feedback_id,
            "workflow_id": request.workflow_id
        })

    except Exception as e:
        logger.error(f"Failed to submit feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/feedback/analytics")
async def get_feedback_analytics(
    current_user: User = Depends(get_current_active_user)
):
    """Get feedback analytics (admin only for now)."""
    try:
        # For now, return workflow analytics which includes feedback metrics
        analytics = await workflow_service.get_workflow_analytics()

        return CustomJSONResponse(content=analytics)

    except Exception as e:
        logger.error(f"Failed to get feedback analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feedback analytics: {str(e)}"
        )


# Utility Endpoints

@router.get("/workflow/health")
async def workflow_health_check():
    """Health check for workflow service."""
    try:
        analytics = await workflow_service.get_workflow_analytics()

        return CustomJSONResponse(content={
            "status": "healthy",
            "service": "workflow_service",
            "metrics": {
                "active_workflows": analytics.get("workflow_metrics", {}).get("total_workflows", 0),
                "pending_approvals": analytics.get("approval_metrics", {}).get("pending_approvals", 0)
            },
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Workflow health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow service unhealthy: {str(e)}"
        )

# Test endpoint for database verification
@router.get("/workflow/{workflow_id}/database-summary")
async def get_workflow_database_summary(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive workflow database summary to verify persistence."""
    try:
        summary = await workflow_db_service.get_workflow_summary(workflow_id, db)

        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found in database"
            )

        return CustomJSONResponse(content={
            "workflow_id": workflow_id,
            "database_summary": summary,
            "verification": {
                "workflow_persisted": True,
                "total_related_records": sum(summary["total_records"].values()),
                "phases_with_data": [
                    phase for phase, count in summary["total_records"].items()
                    if count > 0
                ]
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow database summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow database summary: {str(e)}"
        )
