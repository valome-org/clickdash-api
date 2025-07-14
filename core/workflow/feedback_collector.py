"""
Feedback Collection System.

This module provides user feedback collection and analysis including:
- User satisfaction scoring
- Decision rationale capture
- Improvement suggestion collection
- Usage pattern analysis
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import logging

from .base import BaseWorkflowStep, WorkflowStep, WorkflowContext, ApprovalStatus

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of feedback."""
    SATISFACTION = "satisfaction"
    USABILITY = "usability"
    ACCURACY = "accuracy"
    PERFORMANCE = "performance"
    FEATURE_REQUEST = "feature_request"
    BUG_REPORT = "bug_report"
    GENERAL = "general"


class FeedbackCategory(str, Enum):
    """Categories for feedback organization."""
    AI_RECOMMENDATIONS = "ai_recommendations"
    USER_INTERFACE = "user_interface"
    DATA_PROCESSING = "data_processing"
    WORKFLOW = "workflow"
    VISUALIZATION = "visualization"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"


class SatisfactionLevel(str, Enum):
    """Satisfaction rating levels."""
    VERY_DISSATISFIED = "very_dissatisfied"  # 1
    DISSATISFIED = "dissatisfied"            # 2
    NEUTRAL = "neutral"                      # 3
    SATISFIED = "satisfied"                  # 4
    VERY_SATISFIED = "very_satisfied"        # 5


class UsageContext(BaseModel):
    """Context information about usage patterns."""

    session_id: str = Field(..., description="Session identifier")
    workflow_id: Optional[str] = None
    step_name: Optional[str] = None

    # User context
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    experience_level: Optional[str] = None

    # Technical context
    browser: Optional[str] = None
    device_type: Optional[str] = None
    screen_size: Optional[str] = None

    # Interaction context
    time_spent_ms: Optional[float] = None
    clicks_count: Optional[int] = None
    scroll_depth: Optional[float] = None

    # Data context
    dataset_size: Optional[int] = None
    complexity_score: Optional[float] = None


class UserFeedback(BaseModel):
    """Individual piece of user feedback."""

    feedback_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    category: FeedbackCategory = Field(..., description="Feedback category")

    # Core feedback content
    title: str = Field(..., description="Feedback title or summary")
    description: str = Field(..., description="Detailed feedback description")
    satisfaction_rating: Optional[SatisfactionLevel] = None
    numeric_rating: Optional[float] = Field(None, description="Numeric rating (1-5)")

    # Context information
    usage_context: UsageContext = Field(..., description="Usage context when feedback was given")
    workflow_step: Optional[WorkflowStep] = None
    related_items: List[str] = Field(default_factory=list, description="Related workflow items")

    # Feedback details
    what_worked_well: List[str] = Field(default_factory=list, description="Positive aspects")
    what_needs_improvement: List[str] = Field(default_factory=list, description="Areas for improvement")
    suggested_changes: List[str] = Field(default_factory=list, description="Specific change suggestions")

    # Decision rationale (for approval feedback)
    decision_reasoning: Optional[str] = None
    alternative_preferences: Dict[str, float] = Field(default_factory=dict, description="Preference scores for alternatives")

    # Metadata
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    priority: str = Field(default="medium", description="Priority: low, medium, high")
    actionable: bool = Field(default=True, description="Whether feedback is actionable")

    # Follow-up
    follow_up_requested: bool = Field(default=False)
    contact_allowed: bool = Field(default=False)


class FeedbackRequest(BaseModel):
    """Request for user feedback."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_type: FeedbackType = Field(..., description="Type of feedback requested")

    # Context
    workflow_id: str = Field(..., description="Associated workflow ID")
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Request details
    title: str = Field(..., description="Feedback request title")
    description: str = Field(..., description="What feedback is being requested")
    specific_questions: List[str] = Field(default_factory=list, description="Specific questions to ask")

    # Request configuration
    required_fields: List[str] = Field(default_factory=list, description="Required feedback fields")
    optional_fields: List[str] = Field(default_factory=list, description="Optional feedback fields")
    allow_anonymous: bool = Field(default=True, description="Allow anonymous feedback")

    # Timing
    show_after_step: Optional[WorkflowStep] = None
    delay_minutes: int = Field(default=0, description="Delay before showing request")
    expires_at: Optional[datetime] = None

    # Request metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    priority: str = Field(default="medium")


class FeedbackAnalysis(BaseModel):
    """Analysis results from collected feedback."""

    analysis_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analysis_period: Tuple[datetime, datetime] = Field(..., description="Analysis time period")

    # Overall metrics
    total_feedback_count: int = Field(default=0)
    average_satisfaction: float = Field(default=0.0, description="Average satisfaction rating")
    response_rate: float = Field(default=0.0, description="Feedback response rate")

    # Satisfaction breakdown
    satisfaction_distribution: Dict[str, int] = Field(default_factory=dict)
    category_satisfaction: Dict[str, float] = Field(default_factory=dict)
    workflow_step_satisfaction: Dict[str, float] = Field(default_factory=dict)

    # Common themes
    top_positive_themes: List[Dict[str, Any]] = Field(default_factory=list)
    top_improvement_areas: List[Dict[str, Any]] = Field(default_factory=list)
    frequent_suggestions: List[Dict[str, Any]] = Field(default_factory=list)

    # Usage patterns
    usage_patterns: Dict[str, Any] = Field(default_factory=dict)
    user_segments: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Actionable insights
    priority_improvements: List[str] = Field(default_factory=list)
    recommended_changes: List[Dict[str, Any]] = Field(default_factory=list)
    success_factors: List[str] = Field(default_factory=list)

    # Analysis metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_version: str = Field(default="1.0")


class FeedbackCollector(BaseWorkflowStep):
    """Main feedback collection and analysis service."""

    def __init__(self):
        super().__init__("feedback_collector", WorkflowStep.FEEDBACK_COLLECTION)
        self.feedback_store: List[UserFeedback] = []
        self.feedback_requests: Dict[str, FeedbackRequest] = {}
        self.analysis_cache: Dict[str, FeedbackAnalysis] = {}

    async def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """Execute feedback collection step."""
        try:
            # Create feedback request
            feedback_request = await self._create_post_workflow_feedback_request(context)

            # Store the request
            self.feedback_requests[feedback_request.request_id] = feedback_request

            # Update context
            context.workflow_state = context.workflow_state.COMPLETED

            return {
                "step": "feedback_collection",
                "feedback_request_id": feedback_request.request_id,
                "status": "feedback_requested",
                "next_action": "await_user_feedback"
            }

        except Exception as e:
            logger.error(f"Feedback collection execution failed: {str(e)}")
            raise

    async def validate_inputs(self, context: WorkflowContext, **kwargs) -> bool:
        """Validate inputs for feedback collection."""
        # Feedback collection can always proceed
        return True

    async def collect_feedback(self, feedback: UserFeedback) -> str:
        """Collect and store user feedback."""
        try:
            # Validate feedback
            if not await self._validate_feedback(feedback):
                raise ValueError("Invalid feedback data")

            # Store feedback
            self.feedback_store.append(feedback)

            # Update related workflow context if available
            await self._update_workflow_context(feedback)

            # Trigger immediate analysis if needed
            if feedback.priority == "high" or feedback.feedback_type == FeedbackType.BUG_REPORT:
                await self._trigger_immediate_analysis(feedback)

            logger.info(f"Collected feedback: {feedback.feedback_id} ({feedback.feedback_type.value})")
            return feedback.feedback_id

        except Exception as e:
            logger.error(f"Failed to collect feedback: {str(e)}")
            raise

    async def request_feedback(
        self,
        request_type: FeedbackType,
        workflow_id: str,
        **kwargs
    ) -> FeedbackRequest:
        """Create a feedback request."""

        request = FeedbackRequest(
            request_type=request_type,
            workflow_id=workflow_id,
            user_id=kwargs.get('user_id'),
            session_id=kwargs.get('session_id'),
            title=kwargs.get('title', f"Feedback Request: {request_type.value}"),
            description=kwargs.get('description', "We'd appreciate your feedback on this workflow"),
            specific_questions=kwargs.get('questions', []),
            show_after_step=kwargs.get('show_after_step'),
            delay_minutes=kwargs.get('delay_minutes', 0),
            expires_at=kwargs.get('expires_at')
        )

        self.feedback_requests[request.request_id] = request
        logger.info(f"Created feedback request: {request.request_id}")
        return request

    async def analyze_feedback(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[FeedbackCategory] = None
    ) -> FeedbackAnalysis:
        """Analyze collected feedback for insights."""

        # Set default date range
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)  # Last 30 days

        # Filter feedback
        filtered_feedback = [
            fb for fb in self.feedback_store
            if start_date <= fb.submitted_at <= end_date
            and (not category or fb.category == category)
        ]

        if not filtered_feedback:
            return FeedbackAnalysis(
                analysis_period=(start_date, end_date),
                total_feedback_count=0
            )

        # Calculate overall metrics
        total_count = len(filtered_feedback)
        numeric_ratings = [fb.numeric_rating for fb in filtered_feedback if fb.numeric_rating]
        avg_satisfaction = sum(numeric_ratings) / len(numeric_ratings) if numeric_ratings else 0.0

        # Satisfaction distribution
        satisfaction_dist = {}
        for fb in filtered_feedback:
            if fb.satisfaction_rating:
                level = fb.satisfaction_rating.value
                satisfaction_dist[level] = satisfaction_dist.get(level, 0) + 1

        # Category satisfaction
        category_satisfaction = await self._calculate_category_satisfaction(filtered_feedback)

        # Workflow step satisfaction
        step_satisfaction = await self._calculate_step_satisfaction(filtered_feedback)

        # Extract themes
        positive_themes = await self._extract_positive_themes(filtered_feedback)
        improvement_areas = await self._extract_improvement_areas(filtered_feedback)
        suggestions = await self._extract_suggestions(filtered_feedback)

        # Usage patterns
        usage_patterns = await self._analyze_usage_patterns(filtered_feedback)

        # Generate insights
        priority_improvements = await self._identify_priority_improvements(filtered_feedback)
        recommended_changes = await self._generate_recommended_changes(filtered_feedback)
        success_factors = await self._identify_success_factors(filtered_feedback)

        analysis = FeedbackAnalysis(
            analysis_period=(start_date, end_date),
            total_feedback_count=total_count,
            average_satisfaction=avg_satisfaction,
            satisfaction_distribution=satisfaction_dist,
            category_satisfaction=category_satisfaction,
            workflow_step_satisfaction=step_satisfaction,
            top_positive_themes=positive_themes,
            top_improvement_areas=improvement_areas,
            frequent_suggestions=suggestions,
            usage_patterns=usage_patterns,
            priority_improvements=priority_improvements,
            recommended_changes=recommended_changes,
            success_factors=success_factors
        )

        # Cache analysis
        cache_key = f"{start_date.isoformat()}_{end_date.isoformat()}_{category.value if category else 'all'}"
        self.analysis_cache[cache_key] = analysis

        logger.info(f"Analyzed {total_count} feedback items, avg satisfaction: {avg_satisfaction:.2f}")
        return analysis

    async def get_feedback_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get feedback trends over time."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Group feedback by day
        daily_feedback = {}
        for fb in self.feedback_store:
            if start_date <= fb.submitted_at <= end_date:
                day = fb.submitted_at.date()
                if day not in daily_feedback:
                    daily_feedback[day] = []
                daily_feedback[day].append(fb)

        # Calculate daily metrics
        trends = {
            "dates": [],
            "feedback_count": [],
            "average_satisfaction": [],
            "categories": {}
        }

        for day in sorted(daily_feedback.keys()):
            day_feedback = daily_feedback[day]
            trends["dates"].append(day.isoformat())
            trends["feedback_count"].append(len(day_feedback))

            # Calculate average satisfaction
            ratings = [fb.numeric_rating for fb in day_feedback if fb.numeric_rating]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            trends["average_satisfaction"].append(avg_rating)

            # Count by category
            for fb in day_feedback:
                category = fb.category.value
                if category not in trends["categories"]:
                    trends["categories"][category] = []

                # Pad with zeros if needed
                while len(trends["categories"][category]) < len(trends["dates"]) - 1:
                    trends["categories"][category].append(0)

                if len(trends["categories"][category]) == len(trends["dates"]) - 1:
                    trends["categories"][category].append(1)
                else:
                    trends["categories"][category][-1] += 1

        # Pad all category arrays to match dates
        for category in trends["categories"]:
            while len(trends["categories"][category]) < len(trends["dates"]):
                trends["categories"][category].append(0)

        return trends

    async def _create_post_workflow_feedback_request(self, context: WorkflowContext) -> FeedbackRequest:
        """Create feedback request after workflow completion."""
        return FeedbackRequest(
            request_type=FeedbackType.SATISFACTION,
            workflow_id=context.workflow_id,
            user_id=context.user_id,
            title="How was your dashboard creation experience?",
            description="Please share your feedback about the dashboard creation process",
            specific_questions=[
                "How satisfied are you with the AI recommendations?",
                "Was the approval process clear and helpful?",
                "Did the final dashboard meet your expectations?",
                "What could we improve for next time?"
            ],
            required_fields=["satisfaction_rating", "description"],
            optional_fields=["suggested_changes", "what_worked_well"],
            expires_at=datetime.utcnow() + timedelta(days=7)
        )

    async def _validate_feedback(self, feedback: UserFeedback) -> bool:
        """Validate feedback data."""
        # Basic validation
        if not feedback.title or not feedback.description:
            return False

        # Rating validation
        if feedback.numeric_rating and not (1 <= feedback.numeric_rating <= 5):
            return False

        return True

    async def _update_workflow_context(self, feedback: UserFeedback):
        """Update workflow context based on feedback."""
        # In a full implementation, this would update the workflow context
        # to incorporate feedback for future improvements
        pass

    async def _trigger_immediate_analysis(self, feedback: UserFeedback):
        """Trigger immediate analysis for high-priority feedback."""
        if feedback.feedback_type == FeedbackType.BUG_REPORT:
            logger.warning(f"Bug report received: {feedback.title}")
            # In a full implementation, this would trigger bug tracking workflows

        if feedback.priority == "high":
            logger.info(f"High-priority feedback received: {feedback.title}")
            # In a full implementation, this would notify relevant teams

    async def _calculate_category_satisfaction(self, feedback_list: List[UserFeedback]) -> Dict[str, float]:
        """Calculate satisfaction by category."""
        category_ratings = {}

        for fb in feedback_list:
            if fb.numeric_rating and fb.category:
                category = fb.category.value
                if category not in category_ratings:
                    category_ratings[category] = []
                category_ratings[category].append(fb.numeric_rating)

        return {
            category: sum(ratings) / len(ratings)
            for category, ratings in category_ratings.items()
        }

    async def _calculate_step_satisfaction(self, feedback_list: List[UserFeedback]) -> Dict[str, float]:
        """Calculate satisfaction by workflow step."""
        step_ratings = {}

        for fb in feedback_list:
            if fb.numeric_rating and fb.workflow_step:
                step = fb.workflow_step.value
                if step not in step_ratings:
                    step_ratings[step] = []
                step_ratings[step].append(fb.numeric_rating)

        return {
            step: sum(ratings) / len(ratings)
            for step, ratings in step_ratings.items()
        }

    async def _extract_positive_themes(self, feedback_list: List[UserFeedback]) -> List[Dict[str, Any]]:
        """Extract common positive themes from feedback."""
        themes = {}

        for fb in feedback_list:
            for item in fb.what_worked_well:
                # Simple keyword extraction (in production, use NLP)
                key_words = item.lower().split()
                for word in key_words:
                    if len(word) > 3:  # Skip short words
                        themes[word] = themes.get(word, 0) + 1

        # Return top themes
        sorted_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)
        return [
            {"theme": theme, "frequency": count, "sentiment": "positive"}
            for theme, count in sorted_themes[:5]
        ]

    async def _extract_improvement_areas(self, feedback_list: List[UserFeedback]) -> List[Dict[str, Any]]:
        """Extract common improvement areas from feedback."""
        areas = {}

        for fb in feedback_list:
            for item in fb.what_needs_improvement:
                # Simple keyword extraction
                key_words = item.lower().split()
                for word in key_words:
                    if len(word) > 3:
                        areas[word] = areas.get(word, 0) + 1

        sorted_areas = sorted(areas.items(), key=lambda x: x[1], reverse=True)
        return [
            {"area": area, "frequency": count, "priority": "high" if count > 2 else "medium"}
            for area, count in sorted_areas[:5]
        ]

    async def _extract_suggestions(self, feedback_list: List[UserFeedback]) -> List[Dict[str, Any]]:
        """Extract frequent suggestions from feedback."""
        suggestions = {}

        for fb in feedback_list:
            for suggestion in fb.suggested_changes:
                # Group similar suggestions (simplified)
                key = suggestion.lower()[:50]  # First 50 chars as key
                if key not in suggestions:
                    suggestions[key] = {"text": suggestion, "count": 0}
                suggestions[key]["count"] += 1

        sorted_suggestions = sorted(suggestions.values(), key=lambda x: x["count"], reverse=True)
        return [
            {"suggestion": item["text"], "frequency": item["count"]}
            for item in sorted_suggestions[:5]
        ]

    async def _analyze_usage_patterns(self, feedback_list: List[UserFeedback]) -> Dict[str, Any]:
        """Analyze usage patterns from feedback context."""
        patterns = {
            "device_types": {},
            "average_session_time": 0,
            "common_workflows": {},
            "user_experience_levels": {}
        }

        total_time = 0
        time_count = 0

        for fb in feedback_list:
            context = fb.usage_context

            # Device types
            if context.device_type:
                device = context.device_type
                patterns["device_types"][device] = patterns["device_types"].get(device, 0) + 1

            # Session times
            if context.time_spent_ms:
                total_time += context.time_spent_ms
                time_count += 1

            # Experience levels
            if context.experience_level:
                level = context.experience_level
                patterns["user_experience_levels"][level] = patterns["user_experience_levels"].get(level, 0) + 1

        if time_count > 0:
            patterns["average_session_time"] = total_time / time_count

        return patterns

    async def _identify_priority_improvements(self, feedback_list: List[UserFeedback]) -> List[str]:
        """Identify priority improvements based on feedback."""
        improvements = []

        # Count dissatisfied users
        dissatisfied_count = sum(
            1 for fb in feedback_list
            if fb.satisfaction_rating in [SatisfactionLevel.DISSATISFIED, SatisfactionLevel.VERY_DISSATISFIED]
        )

        if dissatisfied_count > len(feedback_list) * 0.2:  # More than 20% dissatisfied
            improvements.append("Address overall user satisfaction issues")

        # Look for common improvement themes
        improvement_items = []
        for fb in feedback_list:
            improvement_items.extend(fb.what_needs_improvement)

        if len(improvement_items) > 0:
            improvements.append("Focus on commonly mentioned improvement areas")

        return improvements

    async def _generate_recommended_changes(self, feedback_list: List[UserFeedback]) -> List[Dict[str, Any]]:
        """Generate specific recommended changes based on feedback."""
        changes = []

        # Analyze suggestion frequency
        suggestion_counts = {}
        for fb in feedback_list:
            for suggestion in fb.suggested_changes:
                suggestion_counts[suggestion] = suggestion_counts.get(suggestion, 0) + 1

        # Recommend high-frequency suggestions
        for suggestion, count in suggestion_counts.items():
            if count >= 2:  # Suggested by multiple users
                changes.append({
                    "change": suggestion,
                    "frequency": count,
                    "priority": "high" if count >= 3 else "medium"
                })

        return changes[:10]  # Top 10 recommendations

    async def _identify_success_factors(self, feedback_list: List[UserFeedback]) -> List[str]:
        """Identify factors that contribute to user success."""
        factors = []

        # Analyze positive feedback from highly satisfied users
        satisfied_feedback = [
            fb for fb in feedback_list
            if fb.satisfaction_rating in [SatisfactionLevel.SATISFIED, SatisfactionLevel.VERY_SATISFIED]
        ]

        if satisfied_feedback:
            # Extract common positive elements
            positive_items = []
            for fb in satisfied_feedback:
                positive_items.extend(fb.what_worked_well)

            if positive_items:
                factors.append("Maintain elements that users consistently appreciate")

        return factors
