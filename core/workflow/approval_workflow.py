"""
User Approval Interface System.

This module provides step-by-step approval workflow including:
- Clear explanation of AI decisions
- Alternative option presentation
- Modification request handling
- Approval decision tracking
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import logging

from .base import BaseWorkflowStep, WorkflowStep, WorkflowContext, ApprovalStatus

logger = logging.getLogger(__name__)


class ApprovalType(str, Enum):
    """Types of approval requests."""
    DASHBOARD_DESIGN = "dashboard_design"
    CHART_CONFIGURATION = "chart_configuration"
    DATA_PROCESSING = "data_processing"
    LAYOUT_SELECTION = "layout_selection"
    PERFORMANCE_TRADEOFF = "performance_tradeoff"
    FINAL_IMPLEMENTATION = "final_implementation"


class DecisionType(str, Enum):
    """Types of user decisions."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"
    REQUEST_ALTERNATIVES = "request_alternatives"
    DEFER = "defer"


class ApprovalItem(BaseModel):
    """Individual item requiring approval."""

    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item_type: ApprovalType = Field(..., description="Type of approval item")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Detailed description")

    # Content to approve
    content: Dict[str, Any] = Field(..., description="Content requiring approval")
    alternatives: List[Dict[str, Any]] = Field(default_factory=list, description="Alternative options")

    # AI explanation
    ai_reasoning: str = Field(..., description="AI reasoning for this recommendation")
    confidence_score: float = Field(..., description="AI confidence (0-1)")
    risk_assessment: str = Field(default="low", description="Risk level: low, medium, high")

    # User guidance
    approval_guidance: List[str] = Field(default_factory=list, description="Guidance for approval decision")
    implications: List[str] = Field(default_factory=list, description="Implications of approval/rejection")

    # Approval metadata
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")
    estimated_effort: str = Field(default="medium", description="Implementation effort")
    reversible: bool = Field(default=True, description="Can this decision be easily reversed")

    # Dependencies
    depends_on: List[str] = Field(default_factory=list, description="Items this depends on")
    blocks: List[str] = Field(default_factory=list, description="Items this blocks")


class ModificationRequest(BaseModel):
    """User request for modifications."""

    item_id: str = Field(..., description="Item to modify")
    modification_type: str = Field(..., description="Type of modification")
    requested_changes: Dict[str, Any] = Field(..., description="Specific changes requested")
    user_explanation: str = Field(..., description="User explanation for changes")
    priority: str = Field(default="medium", description="Priority of modification")


class ApprovalDecision(BaseModel):
    """User's approval decision for an item."""

    item_id: str = Field(..., description="Item being decided on")
    decision_type: DecisionType = Field(..., description="Type of decision")
    approval_status: ApprovalStatus = Field(..., description="Final approval status")

    # Decision details
    user_notes: Optional[str] = Field(None, description="User notes about decision")
    conditions: List[str] = Field(default_factory=list, description="Conditions for approval")
    modifications: List[ModificationRequest] = Field(default_factory=list, description="Requested modifications")

    # Decision metadata
    decision_time: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    confidence_in_decision: float = Field(default=1.0, description="User confidence in their decision")


class ApprovalRequest(BaseModel):
    """Request for user approval on multiple items."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str = Field(..., description="Associated workflow ID")

    # Approval items
    items: List[ApprovalItem] = Field(..., description="Items requiring approval")

    # Request context
    request_type: ApprovalType = Field(..., description="Primary type of approval")
    urgency: str = Field(default="medium", description="Urgency level")
    deadline: Optional[datetime] = Field(None, description="Approval deadline")

    # User context
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Presentation options
    show_alternatives: bool = Field(default=True, description="Show alternative options")
    allow_modifications: bool = Field(default=True, description="Allow modification requests")
    require_all_items: bool = Field(default=False, description="Require approval of all items")

    # Request metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(None, description="Request expiration")


class ApprovalResult(BaseModel):
    """Result of approval process."""

    request_id: str = Field(..., description="Original request ID")
    success: bool = Field(..., description="Whether approval process completed")

    # Decisions
    decisions: List[ApprovalDecision] = Field(default_factory=list, description="User decisions")
    overall_status: ApprovalStatus = Field(..., description="Overall approval status")

    # Processing results
    approved_items: List[str] = Field(default_factory=list, description="Approved item IDs")
    rejected_items: List[str] = Field(default_factory=list, description="Rejected item IDs")
    modified_items: List[str] = Field(default_factory=list, description="Items requiring modification")

    # Next steps
    next_actions: List[str] = Field(default_factory=list, description="Required next actions")
    implementation_plan: List[str] = Field(default_factory=list, description="Implementation steps")

    # Metadata
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    total_time_ms: float = Field(default=0.0, description="Total approval time")


class ApprovalWorkflow(BaseWorkflowStep):
    """Main approval workflow manager."""

    def __init__(self):
        super().__init__("approval_workflow", WorkflowStep.USER_APPROVAL)
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.approval_history: List[ApprovalResult] = []

    async def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """Execute approval workflow step."""
        try:
            # Extract approval request data
            request_data = kwargs.get('approval_request')
            if not request_data:
                raise ValueError("Approval request data is required")

            # Create approval request
            if isinstance(request_data, dict):
                approval_request = ApprovalRequest(**request_data)
            else:
                approval_request = request_data

            # Store pending request
            self.pending_requests[approval_request.request_id] = approval_request

            # Update workflow context
            context.workflow_state = context.workflow_state.WAITING_FOR_USER
            context.approval_requirements = {
                "request_id": approval_request.request_id,
                "items_count": len(approval_request.items),
                "urgency": approval_request.urgency,
                "deadline": approval_request.deadline.isoformat() if approval_request.deadline else None
            }

            return {
                "step": "user_approval",
                "request_id": approval_request.request_id,
                "items_count": len(approval_request.items),
                "status": "waiting_for_user",
                "next_action": "await_user_decision"
            }

        except Exception as e:
            logger.error(f"Approval workflow execution failed: {str(e)}")
            raise

    async def validate_inputs(self, context: WorkflowContext, **kwargs) -> bool:
        """Validate inputs for approval workflow."""
        request_data = kwargs.get('approval_request')
        if not request_data:
            return False

        if isinstance(request_data, dict):
            return 'items' in request_data and len(request_data['items']) > 0

        return hasattr(request_data, 'items') and len(request_data.items) > 0

    async def create_approval_request(
        self,
        items: List[ApprovalItem],
        request_type: ApprovalType,
        workflow_id: str,
        **kwargs
    ) -> ApprovalRequest:
        """Create a new approval request."""

        # Set deadline if not provided
        deadline = kwargs.get('deadline')
        if not deadline and kwargs.get('urgency') == 'high':
            deadline = datetime.utcnow() + timedelta(hours=24)
        elif not deadline:
            deadline = datetime.utcnow() + timedelta(days=3)

        request = ApprovalRequest(
            workflow_id=workflow_id,
            items=items,
            request_type=request_type,
            urgency=kwargs.get('urgency', 'medium'),
            deadline=deadline,
            user_id=kwargs.get('user_id'),
            session_id=kwargs.get('session_id'),
            show_alternatives=kwargs.get('show_alternatives', True),
            allow_modifications=kwargs.get('allow_modifications', True),
            require_all_items=kwargs.get('require_all_items', False),
            expires_at=None
        )

        # Store pending request
        self.pending_requests[request.request_id] = request

        logger.info(f"Created approval request {request.request_id} with {len(items)} items")
        return request

    async def process_user_decisions(
        self,
        request_id: str,
        decisions: List[ApprovalDecision]
    ) -> ApprovalResult:
        """Process user approval decisions."""

        start_time = datetime.utcnow()

        try:
            # Get original request
            request = self.pending_requests.get(request_id)
            if not request:
                raise ValueError(f"Approval request {request_id} not found")

            # Validate decisions
            item_ids = {item.item_id for item in request.items}
            decision_ids = {decision.item_id for decision in decisions}

            if not decision_ids.issubset(item_ids):
                invalid_ids = decision_ids - item_ids
                raise ValueError(f"Invalid item IDs in decisions: {invalid_ids}")

            # Process decisions
            approved_items = []
            rejected_items = []
            modified_items = []
            overall_status = ApprovalStatus.PENDING

            for decision in decisions:
                if decision.approval_status == ApprovalStatus.APPROVED:
                    approved_items.append(decision.item_id)
                elif decision.approval_status == ApprovalStatus.REJECTED:
                    rejected_items.append(decision.item_id)
                elif decision.approval_status == ApprovalStatus.APPROVED_WITH_CHANGES:
                    modified_items.append(decision.item_id)

            # Determine overall status
            if len(approved_items) == len(request.items):
                overall_status = ApprovalStatus.APPROVED
            elif len(rejected_items) == len(request.items):
                overall_status = ApprovalStatus.REJECTED
            elif modified_items:
                overall_status = ApprovalStatus.APPROVED_WITH_CHANGES
            else:
                overall_status = ApprovalStatus.REQUIRES_REVISION

            # Generate next actions
            next_actions = await self._generate_next_actions(decisions, request)
            implementation_plan = await self._generate_implementation_plan(decisions, request)

            # Calculate processing time
            end_time = datetime.utcnow()
            total_time_ms = (end_time - start_time).total_seconds() * 1000

            # Create result
            result = ApprovalResult(
                request_id=request_id,
                success=True,
                decisions=decisions,
                overall_status=overall_status,
                approved_items=approved_items,
                rejected_items=rejected_items,
                modified_items=modified_items,
                next_actions=next_actions,
                implementation_plan=implementation_plan,
                total_time_ms=total_time_ms
            )

            # Clean up pending request
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]

            # Store in history
            self.approval_history.append(result)

            logger.info(f"Processed approval decisions for {request_id}: {overall_status.value}")
            return result

        except Exception as e:
            logger.error(f"Failed to process approval decisions: {str(e)}")

            return ApprovalResult(
                request_id=request_id,
                success=False,
                decisions=[],
                overall_status=ApprovalStatus.REJECTED,
                next_actions=[f"Error processing decisions: {str(e)}"]
            )

    async def get_pending_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a pending approval request."""
        return self.pending_requests.get(request_id)

    async def get_all_pending_requests(self, user_id: Optional[str] = None) -> List[ApprovalRequest]:
        """Get all pending approval requests for a user."""
        requests = list(self.pending_requests.values())

        if user_id:
            requests = [req for req in requests if req.user_id == user_id]

        return requests

    async def cancel_request(self, request_id: str, reason: str = "User cancelled") -> bool:
        """Cancel a pending approval request."""
        if request_id in self.pending_requests:
            del self.pending_requests[request_id]
            logger.info(f"Cancelled approval request {request_id}: {reason}")
            return True
        return False

    async def extend_deadline(self, request_id: str, new_deadline: datetime) -> bool:
        """Extend the deadline for an approval request."""
        request = self.pending_requests.get(request_id)
        if request:
            request.deadline = new_deadline
            logger.info(f"Extended deadline for request {request_id} to {new_deadline}")
            return True
        return False

    async def _generate_next_actions(
        self,
        decisions: List[ApprovalDecision],
        request: ApprovalRequest
    ) -> List[str]:
        """Generate next actions based on approval decisions."""
        actions = []

        # Count decision types
        approved_count = sum(1 for d in decisions if d.approval_status == ApprovalStatus.APPROVED)
        rejected_count = sum(1 for d in decisions if d.approval_status == ApprovalStatus.REJECTED)
        modified_count = sum(1 for d in decisions if d.approval_status == ApprovalStatus.APPROVED_WITH_CHANGES)

        if approved_count == len(decisions):
            actions.append("Proceed with dashboard implementation")
        elif rejected_count == len(decisions):
            actions.append("Review AI recommendations and regenerate proposals")
        elif modified_count > 0:
            actions.append("Apply requested modifications and regenerate affected components")
            actions.append("Request user review of modified components")

        # Add specific actions based on modifications
        for decision in decisions:
            if decision.modifications:
                for mod in decision.modifications:
                    actions.append(f"Apply modification: {mod.modification_type}")

        return actions

    async def _generate_implementation_plan(
        self,
        decisions: List[ApprovalDecision],
        request: ApprovalRequest
    ) -> List[str]:
        """Generate implementation plan based on decisions."""
        plan = []

        # Get approved items
        approved_decisions = [d for d in decisions if d.approval_status == ApprovalStatus.APPROVED]
        modified_decisions = [d for d in decisions if d.approval_status == ApprovalStatus.APPROVED_WITH_CHANGES]

        if approved_decisions:
            plan.append(f"Implement {len(approved_decisions)} approved components")

        if modified_decisions:
            plan.append(f"Apply modifications to {len(modified_decisions)} components")
            plan.append("Regenerate affected dashboard elements")
            plan.append("Validate modifications meet requirements")

        # Add priority-based ordering
        high_priority_items = [
            item for item in request.items
            if item.priority == "high" or item.priority == "critical"
        ]

        if high_priority_items:
            plan.insert(0, f"Prioritize implementation of {len(high_priority_items)} high-priority items")

        # Add final steps
        plan.append("Generate final dashboard configuration")
        plan.append("Perform quality validation")
        plan.append("Deploy dashboard for user review")

        return plan

    async def generate_dashboard_approval_items(
        self,
        dashboard_config: Any,
        ai_analysis: Dict[str, Any],
        alternatives: List[Any] = []
    ) -> List[ApprovalItem]:
        """Generate approval items for dashboard configuration."""
        items = []

        # Main dashboard design approval
        items.append(ApprovalItem(
            item_type=ApprovalType.DASHBOARD_DESIGN,
            title="Dashboard Design Approval",
            description="Overall dashboard layout, theme, and structure",
            content={"dashboard_config": dashboard_config.dict() if hasattr(dashboard_config, 'dict') else dashboard_config},
            alternatives=[alt.dict() if hasattr(alt, 'dict') else alt for alt in (alternatives or [])],
            ai_reasoning=ai_analysis.get("design_reasoning", "AI recommended this design based on data characteristics"),
            confidence_score=ai_analysis.get("confidence", 0.8),
            approval_guidance=[
                "Review the overall layout and visual structure",
                "Consider if the design meets your business requirements",
                "Check if the theme aligns with your brand guidelines"
            ],
            implications=[
                "Approved design will be used as the foundation for the dashboard",
                "Layout changes after approval may require significant rework"
            ],
            priority="high"
        ))

        # Individual chart approvals
        if hasattr(dashboard_config, 'charts'):
            for i, chart in enumerate(dashboard_config.charts):
                items.append(ApprovalItem(
                    item_type=ApprovalType.CHART_CONFIGURATION,
                    title=f"Chart {i+1}: {getattr(chart, 'title', f'Chart {i+1}')}",
                    description=f"Configuration for {getattr(chart, 'chart_type', 'chart')} visualization",
                    content={"chart_config": chart.dict() if hasattr(chart, 'dict') else chart},
                    ai_reasoning=f"This chart type was selected based on the data characteristics and visualization best practices",
                    confidence_score=0.7,
                    approval_guidance=[
                        "Verify the chart type is appropriate for your data",
                        "Check if the title and labels are clear",
                        "Consider if the chart provides valuable insights"
                    ],
                    implications=[
                        "Chart configuration will affect how data is displayed",
                        "Changes may impact dashboard performance"
                    ],
                    priority="medium"
                ))

        return items


class ApprovalPresenter:
    """Formats approval requests for user presentation."""

    async def format_for_web_ui(self, request: ApprovalRequest) -> Dict[str, Any]:
        """Format approval request for web UI presentation."""
        return {
            "request_id": request.request_id,
            "title": f"Approval Required: {request.request_type.value.replace('_', ' ').title()}",
            "summary": f"{len(request.items)} items require your approval",
            "urgency": request.urgency,
            "deadline": request.deadline.isoformat() if request.deadline else None,
            "items": [await self._format_item_for_ui(item) for item in request.items],
            "options": {
                "show_alternatives": request.show_alternatives,
                "allow_modifications": request.allow_modifications,
                "require_all_items": request.require_all_items
            }
        }

    async def _format_item_for_ui(self, item: ApprovalItem) -> Dict[str, Any]:
        """Format individual approval item for UI."""
        return {
            "item_id": item.item_id,
            "title": item.title,
            "description": item.description,
            "type": item.item_type.value,
            "priority": item.priority,
            "confidence": item.confidence_score,
            "risk": item.risk_assessment,
            "guidance": item.approval_guidance,
            "implications": item.implications,
            "alternatives_count": len(item.alternatives),
            "reversible": item.reversible,
            "estimated_effort": item.estimated_effort
        }

    async def format_decision_summary(self, result: ApprovalResult) -> Dict[str, Any]:
        """Format approval result summary."""
        return {
            "request_id": result.request_id,
            "overall_status": result.overall_status.value,
            "summary": {
                "approved": len(result.approved_items),
                "rejected": len(result.rejected_items),
                "modified": len(result.modified_items),
                "total": len(result.decisions)
            },
            "next_actions": result.next_actions,
            "implementation_plan": result.implementation_plan,
            "completion_time": result.completed_at.isoformat()
        }
