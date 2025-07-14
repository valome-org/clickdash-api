"""
Unified Workflow Service for User Validation & Approval.

This service coordinates all Phase 7 components:
- Preview generation system
- User approval interfaces
- Feedback collection system
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging
import uuid

from core.workflow import (
    WorkflowContext,
    WorkflowStep,
    WorkflowState,
    ApprovalStatus,
    PreviewGenerator,
    PreviewRequest,
    PreviewResult,
    ApprovalWorkflow,
    ApprovalRequest,
    ApprovalResult,
    FeedbackCollector,
    UserFeedback,
    FeedbackType
)
from core.workflow.approval_workflow import ApprovalType
from models.dashboard import DashboardConfig
from database.models import User

logger = logging.getLogger(__name__)


class WorkflowService:
    """Main service for coordinating user validation and approval workflows."""

    def __init__(self):
        self.preview_generator = PreviewGenerator()
        self.approval_workflow = ApprovalWorkflow()
        self.feedback_collector = FeedbackCollector()

        # Active workflows
        self.active_workflows: Dict[str, WorkflowContext] = {}

        logger.info("Workflow service initialized")

    async def start_dashboard_approval_workflow(
        self,
        dashboard_config: DashboardConfig,
        data: Dict[str, Any],
        user: User,
        ai_analysis: Dict[str, Any],
        alternatives: Optional[List[DashboardConfig]] = None
    ) -> WorkflowContext:
        """
        Start a complete dashboard approval workflow.

        Args:
            dashboard_config: Dashboard configuration to approve
            data: Source data
            user: User requesting approval
            ai_analysis: AI analysis results
            alternatives: Alternative dashboard options

        Returns:
            WorkflowContext for tracking workflow progress
        """
        try:
            # Create workflow context
            context = WorkflowContext(
                user_id=getattr(user, 'user_id', None),
                current_step=WorkflowStep.PREVIEW_GENERATION,
                workflow_state=WorkflowState.IN_PROGRESS,
                source_data=data,
                analysis_context={
                    "dashboard_config": dashboard_config.dict(),
                    "ai_analysis": ai_analysis,
                    "alternatives": [alt.dict() for alt in alternatives] if alternatives else []
                }
            )

            # Store active workflow
            self.active_workflows[context.workflow_id] = context

            logger.info(f"Started dashboard approval workflow: {context.workflow_id}")
            return context

        except Exception as e:
            logger.error(f"Failed to start workflow: {str(e)}")
            raise

    async def generate_preview(
        self,
        workflow_id: str,
        preview_options: Optional[Dict[str, Any]] = None
    ) -> PreviewResult:
        """
        Generate dashboard preview for user review.

        Args:
            workflow_id: Workflow identifier
            preview_options: Preview generation options

        Returns:
            PreviewResult with generated preview
        """
        try:
            context = self.active_workflows.get(workflow_id)
            if not context:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Extract dashboard configuration
            dashboard_config_dict = (context.analysis_context or {}).get("dashboard_config")
            if not dashboard_config_dict:
                raise ValueError("Dashboard configuration not found in context")

            dashboard_config = DashboardConfig(**dashboard_config_dict)

            # Create preview request
            preview_request = PreviewRequest(
                dashboard_config=dashboard_config,
                data=context.source_data or {},
                user_id=context.user_id,
                **(preview_options or {})
            )

            # Generate preview
            result = await self.preview_generator.generate_preview(preview_request)

            if result.success:
                # Update workflow context
                context.current_step = WorkflowStep.USER_REVIEW
                if context.analysis_context is None:
                    context.analysis_context = {}
                context.analysis_context["preview"] = result.preview.dict() if result.preview else None

            logger.info(f"Generated preview for workflow {workflow_id}: {result.success}")
            return result

        except Exception as e:
            logger.error(f"Preview generation failed for workflow {workflow_id}: {str(e)}")
            raise

    async def request_user_approval(
        self,
        workflow_id: str,
        approval_options: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        Create approval request for user decision.

        Args:
            workflow_id: Workflow identifier
            approval_options: Approval request options

        Returns:
            ApprovalRequest for user review
        """
        try:
            context = self.active_workflows.get(workflow_id)
            if not context:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Extract data for approval
            dashboard_config_dict = (context.analysis_context or {}).get("dashboard_config")
            ai_analysis = (context.analysis_context or {}).get("ai_analysis", {})
            alternatives_dict = (context.analysis_context or {}).get("alternatives", [])

            if not dashboard_config_dict:
                raise ValueError("Dashboard configuration not found in context")
            dashboard_config = DashboardConfig(**dashboard_config_dict)
            alternatives = [DashboardConfig(**alt) for alt in alternatives_dict] if alternatives_dict else None

            # Generate approval items
            approval_items = await self.approval_workflow.generate_dashboard_approval_items(
                dashboard_config=dashboard_config,
                ai_analysis=ai_analysis,
                alternatives=alternatives or []
            )

            # Create approval request
            approval_request = await self.approval_workflow.create_approval_request(
                items=approval_items,
                request_type=ApprovalType.DASHBOARD_DESIGN,
                workflow_id=workflow_id,
                user_id=context.user_id,
                **(approval_options or {})
            )

            # Update workflow context
            context.current_step = WorkflowStep.USER_APPROVAL
            context.workflow_state = WorkflowState.WAITING_FOR_USER

            logger.info(f"Created approval request for workflow {workflow_id}: {approval_request.request_id}")
            return approval_request

        except Exception as e:
            logger.error(f"Approval request creation failed for workflow {workflow_id}: {str(e)}")
            raise

    async def process_user_approval(
        self,
        workflow_id: str,
        approval_request_id: str,
        decisions: List[Dict[str, Any]]
    ) -> ApprovalResult:
        """
        Process user approval decisions.

        Args:
            workflow_id: Workflow identifier
            approval_request_id: Approval request identifier
            decisions: User decisions

        Returns:
            ApprovalResult with processing results
        """
        try:
            context = self.active_workflows.get(workflow_id)
            if not context:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Convert decisions to proper format
            from core.workflow.approval_workflow import ApprovalDecision, DecisionType
            approval_decisions = []

            for decision_data in decisions:
                decision = ApprovalDecision(
                    item_id=decision_data["item_id"],
                    decision_type=DecisionType(decision_data["decision_type"]),
                    approval_status=ApprovalStatus(decision_data["approval_status"]),
                    user_notes=decision_data.get("user_notes"),
                    user_id=context.user_id
                )
                approval_decisions.append(decision)

            # Process decisions
            result = await self.approval_workflow.process_user_decisions(
                request_id=approval_request_id,
                decisions=approval_decisions
            )

            # Update workflow context based on result
            if result.overall_status == ApprovalStatus.APPROVED:
                context.current_step = WorkflowStep.DASHBOARD_GENERATION
                context.workflow_state = WorkflowState.APPROVED
            elif result.overall_status == ApprovalStatus.REJECTED:
                context.workflow_state = WorkflowState.REJECTED
            elif result.overall_status == ApprovalStatus.APPROVED_WITH_CHANGES:
                context.current_step = WorkflowStep.PREVIEW_GENERATION  # Regenerate with changes
                context.workflow_state = WorkflowState.IN_PROGRESS

            # Store approval history
            context.approval_history.append({
                "request_id": approval_request_id,
                "result": result.dict(),
                "timestamp": datetime.utcnow().isoformat()
            })

            logger.info(f"Processed approval for workflow {workflow_id}: {result.overall_status.value}")
            return result

        except Exception as e:
            logger.error(f"Approval processing failed for workflow {workflow_id}: {str(e)}")
            raise

    async def collect_feedback(
        self,
        workflow_id: str,
        feedback_data: Dict[str, Any]
    ) -> str:
        """
        Collect user feedback about the workflow.

        Args:
            workflow_id: Workflow identifier
            feedback_data: Feedback information

        Returns:
            Feedback ID
        """
        try:
            context = self.active_workflows.get(workflow_id)
            if not context:
                raise ValueError(f"Workflow {workflow_id} not found")

            # Create feedback object
            from core.workflow.feedback_collector import UsageContext

            usage_context = UsageContext(
                session_id=feedback_data.get("session_id", "unknown"),
                workflow_id=workflow_id,
                user_id=context.user_id,
                time_spent_ms=feedback_data.get("time_spent_ms"),
                device_type=feedback_data.get("device_type"),
                experience_level=feedback_data.get("experience_level")
            )

            feedback = UserFeedback(
                feedback_type=FeedbackType(feedback_data["feedback_type"]),
                category=feedback_data["category"],
                title=feedback_data["title"],
                description=feedback_data["description"],
                satisfaction_rating=feedback_data.get("satisfaction_rating"),
                numeric_rating=feedback_data.get("numeric_rating"),
                usage_context=usage_context,
                workflow_step=context.current_step,
                what_worked_well=feedback_data.get("what_worked_well", []),
                what_needs_improvement=feedback_data.get("what_needs_improvement", []),
                suggested_changes=feedback_data.get("suggested_changes", [])
            )

            # Collect feedback
            feedback_id = await self.feedback_collector.collect_feedback(feedback)

            # Update workflow context
            context.current_step = WorkflowStep.FEEDBACK_COLLECTION
            if context.workflow_state in [WorkflowState.APPROVED, WorkflowState.REJECTED]:
                context.workflow_state = WorkflowState.COMPLETED

            logger.info(f"Collected feedback for workflow {workflow_id}: {feedback_id}")
            return feedback_id

        except Exception as e:
            logger.error(f"Feedback collection failed for workflow {workflow_id}: {str(e)}")
            raise

    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get current workflow status and progress.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dictionary with workflow status information
        """
        context = self.active_workflows.get(workflow_id)
        if not context:
            return {"error": f"Workflow {workflow_id} not found"}

        return {
            "workflow_id": workflow_id,
            "current_step": context.current_step.value,
            "workflow_state": context.workflow_state.value,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "user_id": context.user_id,
            "step_history": context.step_history,
            "approval_history": context.approval_history,
            "has_preview": "preview" in (context.analysis_context or {}),
            "pending_approvals": len(self.approval_workflow.pending_requests)
        }

    async def get_pending_approvals(self, user_id: str) -> List[ApprovalRequest]:
        """
        Get pending approval requests for a user.

        Args:
            user_id: User identifier

        Returns:
            List of pending approval requests
        """
        return await self.approval_workflow.get_all_pending_requests(user_id)

    async def get_user_workflows(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all workflows for a user.

        Args:
            user_id: User identifier

        Returns:
            List of workflow summaries
        """
        user_workflows = []

        for workflow_id, context in self.active_workflows.items():
            if context.user_id == user_id:
                user_workflows.append({
                    "workflow_id": workflow_id,
                    "current_step": context.current_step.value,
                    "workflow_state": context.workflow_state.value,
                    "created_at": context.created_at.isoformat(),
                    "updated_at": context.updated_at.isoformat()
                })

        return user_workflows

    async def cancel_workflow(self, workflow_id: str, reason: str = "User cancelled") -> bool:
        """
        Cancel an active workflow.

        Args:
            workflow_id: Workflow identifier
            reason: Cancellation reason

        Returns:
            True if successfully cancelled
        """
        try:
            context = self.active_workflows.get(workflow_id)
            if not context:
                return False

            # Cancel any pending approval requests
            for request_id, request in self.approval_workflow.pending_requests.items():
                if request.workflow_id == workflow_id:
                    await self.approval_workflow.cancel_request(request_id, reason)

            # Update workflow state
            context.workflow_state = WorkflowState.CANCELLED
            context.updated_at = datetime.utcnow()

            # Remove from active workflows
            del self.active_workflows[workflow_id]

            logger.info(f"Cancelled workflow {workflow_id}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {str(e)}")
            return False

    async def complete_workflow(self, workflow_id: str) -> bool:
        """
        Mark workflow as completed.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if successfully completed
        """
        try:
            context = self.active_workflows.get(workflow_id)
            if not context:
                return False

            # Update workflow state
            context.workflow_state = WorkflowState.COMPLETED
            context.current_step = WorkflowStep.COMPLETED
            context.updated_at = datetime.utcnow()

            # Request post-workflow feedback
            feedback_request = await self.feedback_collector.request_feedback(
                request_type=FeedbackType.SATISFACTION,
                workflow_id=workflow_id,
                user_id=context.user_id,
                title="How was your dashboard creation experience?",
                description="Please share your feedback about the dashboard creation process"
            )

            logger.info(f"Completed workflow {workflow_id}, feedback requested: {feedback_request.request_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to complete workflow {workflow_id}: {str(e)}")
            return False

    async def get_workflow_analytics(self) -> Dict[str, Any]:
        """
        Get analytics about workflow usage and performance.

        Returns:
            Dictionary with workflow analytics
        """
        try:
            # Basic workflow metrics
            total_workflows = len(self.active_workflows)
            completed_workflows = sum(
                1 for context in self.active_workflows.values()
                if context.workflow_state == WorkflowState.COMPLETED
            )

            # Workflow states
            state_counts = {}
            for context in self.active_workflows.values():
                state = context.workflow_state.value
                state_counts[state] = state_counts.get(state, 0) + 1

            # Step distribution
            step_counts = {}
            for context in self.active_workflows.values():
                step = context.current_step.value
                step_counts[step] = step_counts.get(step, 0) + 1

            # Feedback analytics
            feedback_analysis = await self.feedback_collector.analyze_feedback()

            return {
                "workflow_metrics": {
                    "total_workflows": total_workflows,
                    "completed_workflows": completed_workflows,
                    "completion_rate": completed_workflows / total_workflows if total_workflows > 0 else 0,
                    "state_distribution": state_counts,
                    "step_distribution": step_counts
                },
                "approval_metrics": {
                    "pending_approvals": len(self.approval_workflow.pending_requests),
                    "approval_history": len(self.approval_workflow.approval_history)
                },
                "feedback_metrics": {
                    "total_feedback": feedback_analysis.total_feedback_count,
                    "average_satisfaction": feedback_analysis.average_satisfaction,
                    "top_improvement_areas": feedback_analysis.top_improvement_areas[:3]
                }
            }

        except Exception as e:
            logger.error(f"Failed to get workflow analytics: {str(e)}")
            return {"error": str(e)}


# Singleton instance
workflow_service = WorkflowService()
