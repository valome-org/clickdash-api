"""
Unified Dashboard Generation Service.

This service integrates all Phase 8 components to provide complete dashboard generation:
- Dynamic dashboard building with template-based generation
- Export and integration capabilities
- Version control and change tracking
- Update notifications and collaboration
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging
import uuid

from core.dashboard.dashboard_builder import (
    DashboardBuilder, DashboardGenerationRequest, DashboardGenerationResult, GenerationStrategy
)
from core.dashboard.export_system import (
    ExportManager, ExportRequest, ExportResult, ExportFormat, IntegrationPlatform
)
from core.dashboard.version_control import (
    VersionManager, DashboardVersion, ChangeType, VersionStatus
)
from models.dashboard import DashboardConfig
from database.models import User

logger = logging.getLogger(__name__)


class DashboardGenerationService:
    """Main service coordinating complete dashboard generation workflow."""

    def __init__(self):
        self.dashboard_builder = DashboardBuilder()
        self.export_manager = ExportManager()
        self.version_manager = VersionManager()

        # Track active generation sessions
        self.active_generations: Dict[str, Dict[str, Any]] = {}

        logger.info("Dashboard generation service initialized")

    async def generate_dashboard_from_workflow(
        self,
        workflow_id: str,
        dashboard_config: DashboardConfig,
        data: Dict[str, Any],
        user: User,
        generation_options: Optional[Dict[str, Any]] = None
    ) -> DashboardGenerationResult:
        """
        Generate dashboard from approved workflow with version control.

        Args:
            workflow_id: Source workflow ID
            dashboard_config: Approved dashboard configuration
            data: Source data
            user: User requesting generation
            generation_options: Additional generation options

        Returns:
            DashboardGenerationResult with complete dashboard
        """
        try:
            generation_id = str(uuid.uuid4())
            user_id = getattr(user, 'user_id', None) or "unknown"

            logger.info(f"Starting dashboard generation from workflow {workflow_id} for user {user_id}")

            # Create generation request
            generation_request = DashboardGenerationRequest(
                dashboard_config=dashboard_config,
                data=data,
                user_id=user_id,
                session_id=workflow_id,
                generation_id=generation_id,
                **(generation_options or {})
            )

            # Track generation session
            self.active_generations[generation_id] = {
                "workflow_id": workflow_id,
                "user_id": user_id,
                "started_at": datetime.utcnow(),
                "status": "generating"
            }

            # Generate dashboard
            result = await self.dashboard_builder.generate_dashboard(generation_request)

            if result.success:
                # Create version in version control
                version = await self.version_manager.create_version(
                    dashboard_id=result.dashboard_id,
                    dashboard_config=dashboard_config.dict(),
                    user_id=user_id,
                    change_summary=f"Dashboard created from workflow {workflow_id}",
                    version_name="Initial Version"
                )

                # Publish the initial version
                await self.version_manager.publish_version(
                    result.dashboard_id, version.version_id, user_id
                )

                # Update session status
                self.active_generations[generation_id]["status"] = "completed"
                self.active_generations[generation_id]["dashboard_id"] = result.dashboard_id
                self.active_generations[generation_id]["version_id"] = version.version_id

                logger.info(f"Dashboard generation completed: {result.dashboard_id}")

            return result

        except Exception as e:
            logger.error(f"Dashboard generation failed: {str(e)}")

            # Update session status
            if generation_id in self.active_generations:
                self.active_generations[generation_id]["status"] = "failed"
                self.active_generations[generation_id]["error"] = str(e)

            raise

    async def update_dashboard(
        self,
        dashboard_id: str,
        updated_config: DashboardConfig,
        user: User,
        change_summary: str,
        data: Optional[Dict[str, Any]] = None
    ) -> DashboardGenerationResult:
        """
        Update existing dashboard with version control.

        Args:
            dashboard_id: Dashboard to update
            updated_config: Updated dashboard configuration
            user: User making the update
            change_summary: Summary of changes
            data: Updated data (optional)

        Returns:
            DashboardGenerationResult with updated dashboard
        """
        try:
            user_id = getattr(user, 'user_id', None) or "unknown"

            logger.info(f"Updating dashboard {dashboard_id} by user {user_id}")

            # Get current active version
            current_version = await self.version_manager.get_active_version(dashboard_id)
            if not current_version:
                raise ValueError(f"No active version found for dashboard {dashboard_id}")

            # Create new version
            new_version = await self.version_manager.create_version(
                dashboard_id=dashboard_id,
                dashboard_config=updated_config.dict(),
                user_id=user_id,
                change_summary=change_summary
            )

            # Regenerate dashboard with new configuration
            generation_request = DashboardGenerationRequest(
                dashboard_config=updated_config,
                data=data or {},
                user_id=user_id,
                strategy=GenerationStrategy.AI_OPTIMIZED
            )

            result = await self.dashboard_builder.generate_dashboard(generation_request)

            if result.success:
                # Publish the new version
                await self.version_manager.publish_version(
                    dashboard_id, new_version.version_id, user_id
                )

                # Update result with version info
                result.dashboard_id = dashboard_id

                logger.info(f"Dashboard updated: {dashboard_id}, new version: {new_version.version_number}")

            return result

        except Exception as e:
            logger.error(f"Dashboard update failed: {str(e)}")
            raise

    async def rollback_dashboard(
        self,
        dashboard_id: str,
        target_version_id: str,
        user: User,
        rollback_reason: str
    ) -> DashboardGenerationResult:
        """
        Rollback dashboard to a previous version.

        Args:
            dashboard_id: Dashboard to rollback
            target_version_id: Version to rollback to
            user: User performing rollback
            rollback_reason: Reason for rollback

        Returns:
            DashboardGenerationResult with rolled back dashboard
        """
        try:
            user_id = getattr(user, 'user_id', None) or "unknown"

            logger.info(f"Rolling back dashboard {dashboard_id} to version {target_version_id}")

            # Perform rollback
            rollback_version = await self.version_manager.rollback_to_version(
                dashboard_id, target_version_id, user_id, rollback_reason
            )

            # Regenerate dashboard with rollback configuration
            target_version = await self.version_manager.get_version(dashboard_id, target_version_id)
            if not target_version:
                raise ValueError(f"Target version {target_version_id} not found")
            dashboard_config = DashboardConfig(**target_version.dashboard_config)

            generation_request = DashboardGenerationRequest(
                dashboard_config=dashboard_config,
                data={},  # Would need to restore data as well
                user_id=user_id,
                strategy=GenerationStrategy.TEMPLATE_BASED
            )

            result = await self.dashboard_builder.generate_dashboard(generation_request)
            result.dashboard_id = dashboard_id

            logger.info(f"Dashboard rollback completed: {dashboard_id}")

            return result

        except Exception as e:
            logger.error(f"Dashboard rollback failed: {str(e)}")
            raise

    async def export_dashboard(
        self,
        dashboard_id: str,
        export_format: ExportFormat,
        user: User,
        export_options: Optional[Dict[str, Any]] = None
    ) -> ExportResult:
        """
        Export dashboard in specified format.

        Args:
            dashboard_id: Dashboard to export
            export_format: Export format
            user: User requesting export
            export_options: Additional export options

        Returns:
            ExportResult with exported content
        """
        try:
            user_id = getattr(user, 'user_id', None)

            logger.info(f"Exporting dashboard {dashboard_id} as {export_format.value}")

            # Create export request
            export_request = ExportRequest(
                dashboard_id=dashboard_id,
                export_format=export_format,
                user_id=user_id,
                **(export_options or {})
            )

            # Perform export
            result = await self.export_manager.export_dashboard(export_request)

            logger.info(f"Dashboard export completed: {result.export_id}")

            return result

        except Exception as e:
            logger.error(f"Dashboard export failed: {str(e)}")
            raise

    async def create_integration(
        self,
        dashboard_id: str,
        platform: IntegrationPlatform,
        user: User,
        integration_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create integration with external platform.

        Args:
            dashboard_id: Dashboard to integrate
            platform: Integration platform
            user: User creating integration
            integration_config: Platform-specific configuration

        Returns:
            Integration details
        """
        try:
            user_id = getattr(user, 'user_id', None) or "unknown"

            logger.info(f"Creating {platform.value} integration for dashboard {dashboard_id}")

            # Create integration
            integration_result = await self.export_manager.integration_manager.create_integration(
                platform, dashboard_id, integration_config
            )

            # Track integration creation
            await self.version_manager.change_tracker.detect_changes(
                dashboard_id=dashboard_id,
                version_id="current",  # Would need to get actual version
                old_config={},
                new_config={"integration": {platform.value: integration_result}},
                user_id=user_id
            )

            logger.info(f"Integration created: {platform.value} for dashboard {dashboard_id}")

            return integration_result

        except Exception as e:
            logger.error(f"Integration creation failed: {str(e)}")
            raise

    async def get_dashboard_versions(
        self,
        dashboard_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[DashboardVersion]:
        """Get version history for a dashboard."""
        return await self.version_manager.get_version_history(dashboard_id, limit, offset)

    async def compare_dashboard_versions(
        self,
        dashboard_id: str,
        version_id_1: str,
        version_id_2: str
    ) -> Dict[str, Any]:
        """Compare two versions of a dashboard."""
        return await self.version_manager.compare_versions(dashboard_id, version_id_1, version_id_2)

    async def get_generation_status(self, generation_id: str) -> Dict[str, Any]:
        """Get status of an active generation."""
        if generation_id in self.active_generations:
            session = self.active_generations[generation_id]

            # Calculate duration
            duration = (datetime.utcnow() - session["started_at"]).total_seconds()

            return {
                "generation_id": generation_id,
                "status": session["status"],
                "duration_seconds": duration,
                "workflow_id": session.get("workflow_id"),
                "dashboard_id": session.get("dashboard_id"),
                "version_id": session.get("version_id"),
                "error": session.get("error")
            }

        return {"error": f"Generation {generation_id} not found"}

    async def subscribe_to_dashboard_updates(
        self,
        dashboard_id: str,
        user: User
    ) -> bool:
        """Subscribe user to dashboard update notifications."""
        user_id = getattr(user, 'user_id', None) or "unknown"
        return await self.version_manager.update_notifier.subscribe_to_updates(dashboard_id, user_id)

    async def unsubscribe_from_dashboard_updates(
        self,
        dashboard_id: str,
        user: User
    ) -> bool:
        """Unsubscribe user from dashboard update notifications."""
        user_id = getattr(user, 'user_id', None) or "unknown"
        return await self.version_manager.update_notifier.unsubscribe_from_updates(dashboard_id, user_id)

    async def get_user_notifications(
        self,
        user: User,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get notifications for a user."""
        user_id = getattr(user, 'user_id', None) or "unknown"
        notifications = await self.version_manager.update_notifier.get_notifications_for_user(
            user_id, limit, unread_only
        )

        return [notification.dict() for notification in notifications]

    async def mark_notification_read(
        self,
        notification_id: str,
        user: User
    ) -> bool:
        """Mark notification as read."""
        user_id = getattr(user, 'user_id', None) or "unknown"
        return await self.version_manager.update_notifier.mark_notification_read(notification_id, user_id)

    async def generate_embed_code(
        self,
        dashboard_id: str,
        platform: str,
        embed_options: Dict[str, Any]
    ) -> str:
        """Generate embed code for dashboard."""
        return await self.export_manager.embedding_generator.generate_embed_code(
            dashboard_id, platform, embed_options
        )

    async def create_api_endpoints(
        self,
        dashboard_id: str,
        api_options: Dict[str, Any]
    ) -> Dict[str, str]:
        """Create API endpoints for dashboard data access."""
        return await self.export_manager.api_generator.create_dashboard_api(dashboard_id, api_options)

    async def get_dashboard_analytics(self) -> Dict[str, Any]:
        """Get analytics about dashboard generation and usage."""
        try:
            # Get generation statistics
            total_generations = len(self.active_generations)
            completed_generations = sum(
                1 for session in self.active_generations.values()
                if session.get("status") == "completed"
            )
            failed_generations = sum(
                1 for session in self.active_generations.values()
                if session.get("status") == "failed"
            )

            # Get version statistics
            total_dashboards = len(self.version_manager.versions)
            total_versions = sum(
                len(versions) for versions in self.version_manager.versions.values()
            )

            # Get export statistics
            total_exports = len(self.export_manager.export_history)
            successful_exports = sum(
                1 for export in self.export_manager.export_history
                if export.success
            )

            # Get notification statistics
            total_notifications = len(self.version_manager.update_notifier.notification_history)
            total_subscribers = sum(
                len(subscribers) for subscribers in self.version_manager.update_notifier.subscribers.values()
            )

            return {
                "dashboard_metrics": {
                    "total_dashboards": total_dashboards,
                    "total_versions": total_versions,
                    "avg_versions_per_dashboard": total_versions / total_dashboards if total_dashboards > 0 else 0
                },
                "generation_metrics": {
                    "total_generations": total_generations,
                    "completed_generations": completed_generations,
                    "failed_generations": failed_generations,
                    "success_rate": completed_generations / total_generations if total_generations > 0 else 0
                },
                "export_metrics": {
                    "total_exports": total_exports,
                    "successful_exports": successful_exports,
                    "export_success_rate": successful_exports / total_exports if total_exports > 0 else 0
                },
                "notification_metrics": {
                    "total_notifications": total_notifications,
                    "total_subscribers": total_subscribers,
                    "avg_notifications_per_dashboard": total_notifications / total_dashboards if total_dashboards > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Failed to get dashboard analytics: {str(e)}")
            return {"error": str(e)}


# Singleton instance
dashboard_generation_service = DashboardGenerationService()
