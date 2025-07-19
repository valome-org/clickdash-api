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

from sqlalchemy.orm import Session
from database.models import User
from database.workflow_models import (
    Workflow, DataSource, DataProcessingJob, DataValidation,
    DataCleanup, Approval, DashboardVersion, ExportJob, Notification,
    WorkflowStatus, DataSourceType, ProcessingStatus, ApprovalStatus as DbApprovalStatus
)
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

logger = logging.getLogger(__name__)


class WorkflowService:
    """Main service for coordinating user validation and approval workflows."""

    def __init__(self):
        self.preview_generator = PreviewGenerator()
        self.approval_workflow = ApprovalWorkflow()
        self.feedback_collector = FeedbackCollector()

        # Active workflows (for backward compatibility, but now we use DB)
        self.active_workflows: Dict[str, WorkflowContext] = {}

        logger.info("Workflow service initialized with database persistence")

    async def start_dashboard_approval_workflow(
        self,
        dashboard_config: DashboardConfig,
        data: Dict[str, Any],
        user: User,
        ai_analysis: Dict[str, Any],
        alternatives: Optional[List[DashboardConfig]] = None,
        db: Optional[Session] = None
    ) -> WorkflowContext:
        """
        Start a complete dashboard approval workflow and save to database.

        Args:
            dashboard_config: Dashboard configuration to approve
            data: Source data
            user: User requesting approval
            ai_analysis: AI analysis results
            alternatives: Alternative dashboard options
            db: Database session

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

            # Save workflow to database if db session provided
            if db:
                workflow_record = await self._create_workflow_record(
                    context=context,
                    user=user,
                    dashboard_config=dashboard_config,
                    ai_analysis=ai_analysis,
                    db=db
                )
                logger.info(f"Workflow saved to database with ID: {workflow_record.id}")

            # Store active workflow (for backward compatibility)
            self.active_workflows[context.workflow_id] = context

            logger.info(f"Started dashboard approval workflow: {context.workflow_id}")
            return context

        except Exception as e:
            logger.error(f"Failed to start workflow: {str(e)}")
            raise

    async def _create_workflow_record(
        self,
        context: WorkflowContext,
        user: User,
        dashboard_config: DashboardConfig,
        ai_analysis: Dict[str, Any],
        db: Session
    ) -> Workflow:
        """Create workflow record in database."""
        try:
            # Create main workflow record
            workflow_record = Workflow(
                workflow_id=context.workflow_id,
                name=f"Dashboard Creation - {dashboard_config.title}",
                description=f"AI-powered dashboard creation workflow for {user.username}",
                status=WorkflowStatus.IN_PROGRESS,
                current_phase="phase_7",  # Starting at approval phase
                phases_completed=["phase_1", "phase_2", "phase_3", "phase_4", "phase_5", "phase_6"],
                configuration={
                    "dashboard_config": dashboard_config.dict(),
                    "workflow_options": context.analysis_context
                },
                ai_analysis_results=ai_analysis,
                user_id=user.id
            )

            db.add(workflow_record)
            db.commit()
            db.refresh(workflow_record)

            # Create initial data source record (assuming file upload)
            data_source_record = DataSource(
                source_id=str(uuid.uuid4()),
                workflow_id=workflow_record.id,
                name="User Uploaded Data",
                source_type=DataSourceType.EXCEL,  # Default, should be detected
                schema_info=(context.source_data or {}).get("schema", {}),
                row_count=(context.source_data or {}).get("row_count", 0),
                column_count=(context.source_data or {}).get("column_count", 0),
                data_preview=(context.source_data or {}).get("preview", {}),
                status="processed"
            )

            db.add(data_source_record)
            db.commit()
            db.refresh(data_source_record)

            # Create processing job record
            processing_job_record = DataProcessingJob(
                job_id=str(uuid.uuid4()),
                workflow_id=workflow_record.id,
                data_source_id=data_source_record.id,
                processing_type="comprehensive_analysis",
                parameters={"quality_check": True, "ai_analysis": True},
                input_rows=(context.source_data or {}).get("row_count", 0),
                output_rows=(context.source_data or {}).get("row_count", 0),
                processing_duration_ms=1000,  # Placeholder
                quality_metrics=ai_analysis.get("quality_metrics", {}),
                status=ProcessingStatus.COMPLETED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )

            db.add(processing_job_record)
            db.commit()
            db.refresh(processing_job_record)

            # Create validation record
            validation_record = DataValidation(
                validation_id=str(uuid.uuid4()),
                workflow_id=workflow_record.id,
                processing_job_id=processing_job_record.id,
                validation_rules={"basic_validation": True},
                validation_scope="full",
                overall_quality_score=ai_analysis.get("quality_score", 85.0),
                total_rows_validated=(context.source_data or {}).get("row_count", 0),
                valid_rows=(context.source_data or {}).get("row_count", 0),
                invalid_rows=0,
                validation_issues=ai_analysis.get("validation_issues", []),
                recommendations=ai_analysis.get("recommendations", []),
                status="completed"
            )

            db.add(validation_record)
            db.commit()
            db.refresh(validation_record)

            # Create cleanup record
            cleanup_record = DataCleanup(
                cleanup_id=str(uuid.uuid4()),
                workflow_id=workflow_record.id,
                validation_id=validation_record.id,
                cleanup_rules={"auto_cleanup": True},
                cleanup_strategy="guided",
                original_rows=(context.source_data or {}).get("row_count", 0),
                cleaned_rows=(context.source_data or {}).get("row_count", 0),
                removed_rows=0,
                modified_rows=0,
                operations_performed=["data_type_conversion", "missing_value_handling"],
                cleanup_summary={"status": "completed", "issues_fixed": 0},
                status="completed"
            )

            db.add(cleanup_record)

            db.commit()

            logger.info(f"Created complete workflow record chain for workflow {workflow_record.workflow_id}")
            return workflow_record

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create workflow record: {str(e)}")
            raise

    async def get_workflow_from_db(self, workflow_id: str, db: Session) -> Optional[Workflow]:
        """Get workflow record from database."""
        try:
            workflow = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
            return workflow
        except Exception as e:
            logger.error(f"Failed to get workflow from database: {str(e)}")
            return None

    async def update_workflow_phase(
        self,
        workflow_id: str,
        new_phase: str,
        phase_data: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> bool:
        """Update workflow phase in database."""
        try:
            if not db:
                return False

            workflow = await self.get_workflow_from_db(workflow_id, db)
            if not workflow:
                return False

            setattr(workflow, 'current_phase', new_phase)
            phases = getattr(workflow, 'phases_completed') or []
            if new_phase not in phases:
                phases.append(new_phase)
                setattr(workflow, 'phases_completed', phases)

            if phase_data:
                analysis_results = getattr(workflow, 'ai_analysis_results') or {}
                analysis_results[new_phase] = phase_data
                setattr(workflow, 'ai_analysis_results', analysis_results)

            setattr(workflow, 'updated_at', datetime.utcnow())

            if new_phase == "phase_8" or new_phase == "completed":
                setattr(workflow, 'status', WorkflowStatus.COMPLETED)
                setattr(workflow, 'completed_at', datetime.utcnow())

            db.commit()
            logger.info(f"Updated workflow {workflow_id} to phase {new_phase}")
            return True

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to update workflow phase: {str(e)}")
            return False

    async def create_approval_request(
        self,
        workflow_id: str,
        approval_data: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Optional[str]:
        """Create approval request in database."""
        try:
            if not db:
                return None

            workflow = await self.get_workflow_from_db(workflow_id, db)
            if not workflow:
                return None

            approval_record = Approval(
                approval_id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                approval_type="dashboard_config",
                phase="phase_7",
                item_description=approval_data.get("description", "Dashboard approval required"),
                request_data=approval_data,
                ai_recommendations=approval_data.get("ai_recommendations", {}),
                status=DbApprovalStatus.PENDING,
                approver_id=workflow.user_id
            )

            db.add(approval_record)
            db.commit()
            db.refresh(approval_record)

            logger.info(f"Created approval request {approval_record.approval_id} for workflow {workflow_id}")
            return getattr(approval_record, 'approval_id')

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to create approval request: {str(e)}")
            return None

    async def process_approval_decision(
        self,
        approval_id: str,
        decision: str,
        decision_data: Dict[str, Any],
        db: Optional[Session] = None
    ) -> bool:
        """Process approval decision in database."""
        try:
            if not db:
                return False

            approval = db.query(Approval).filter(Approval.approval_id == approval_id).first()
            if not approval:
                return False

            if decision == "approve":
                setattr(approval, 'status', DbApprovalStatus.APPROVED)
            elif decision == "reject":
                setattr(approval, 'status', DbApprovalStatus.REJECTED)
            else:
                setattr(approval, 'status', DbApprovalStatus.PENDING)

            setattr(approval, 'decision_notes', decision_data.get("notes", ""))
            setattr(approval, 'decision_data', decision_data)
            setattr(approval, 'responded_at', datetime.utcnow())

            db.commit()
            logger.info(f"Processed approval decision for {approval_id}: {decision}")
            return True

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to process approval decision: {str(e)}")
            return False

    async def create_notification(
        self,
        user_id: int,
        workflow_id: str,
        notification_type: str,
        title: str,
        message: str,
        db: Optional[Session] = None
    ) -> Optional[str]:
        """Create notification in database."""
        try:
            if not db:
                return None

            workflow = await self.get_workflow_from_db(workflow_id, db)
            if not workflow:
                return None

            notification = Notification(
                notification_id=str(uuid.uuid4()),
                user_id=user_id,
                workflow_id=workflow.id,
                notification_type=notification_type,
                title=title,
                message=message,
                channels=["in_app"],
                is_read=False,
                is_sent=True,
                sent_at=datetime.utcnow()
            )

            db.add(notification)
            db.commit()
            db.refresh(notification)

            logger.info(f"Created notification {notification.notification_id} for user {user_id}")
            return getattr(notification, 'notification_id')

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to create notification: {str(e)}")
            return None

    async def get_user_workflows_from_db(self, user_id: str, db: Session) -> List[Dict[str, Any]]:
        """Get user workflows from database."""
        try:
            # First try to find user by user_id string
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return []

            workflows = db.query(Workflow).filter(Workflow.user_id == user.id).all()

            result = []
            for workflow in workflows:
                status_val = getattr(workflow, 'status')
                created_at_val = getattr(workflow, 'created_at')
                updated_at_val = getattr(workflow, 'updated_at')
                completed_at_val = getattr(workflow, 'completed_at')

                result.append({
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "description": workflow.description,
                    "status": status_val.value if status_val else "unknown",
                    "current_phase": workflow.current_phase,
                    "phases_completed": workflow.phases_completed or [],
                    "created_at": created_at_val.isoformat() if created_at_val else None,
                    "updated_at": updated_at_val.isoformat() if updated_at_val else None,
                    "completed_at": completed_at_val.isoformat() if completed_at_val else None
                })

            return result

        except Exception as e:
            logger.error(f"Failed to get user workflows from database: {str(e)}")
            return []

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

    async def get_workflow_status(self, workflow_id: str, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Get current workflow status and progress.

        Args:
            workflow_id: Workflow identifier
            db: Database session

        Returns:
            Dictionary with workflow status information
        """
        # First try database if available
        if db:
            workflow = await self.get_workflow_from_db(workflow_id, db)
            if workflow:
                status_val = getattr(workflow, 'status')
                created_at_val = getattr(workflow, 'created_at')
                updated_at_val = getattr(workflow, 'updated_at')
                completed_at_val = getattr(workflow, 'completed_at')

                return {
                    "workflow_id": workflow_id,
                    "current_step": workflow.current_phase,
                    "workflow_state": status_val.value if status_val else "unknown",
                    "created_at": created_at_val.isoformat() if created_at_val else None,
                    "updated_at": updated_at_val.isoformat() if updated_at_val else None,
                    "completed_at": completed_at_val.isoformat() if completed_at_val else None,
                    "user_id": workflow.user.user_id if workflow.user else None,
                    "name": workflow.name,
                    "description": workflow.description,
                    "phases_completed": workflow.phases_completed or [],
                    "configuration": workflow.configuration or {},
                    "ai_analysis_results": workflow.ai_analysis_results or {}
                }

        # Fallback to in-memory storage
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
