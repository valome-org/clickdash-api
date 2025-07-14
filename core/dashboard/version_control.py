"""
Version Control & Updates System.

This module provides comprehensive version control and update management including:
- Dashboard version tracking with full history
- Change history maintenance and diff generation
- Update notification system
- Rollback capabilities with data preservation
"""

from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import json
import uuid
import hashlib
import logging

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Types of changes that can be made to dashboards."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    RESTORED = "restored"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    LAYOUT_CHANGED = "layout_changed"
    DATA_UPDATED = "data_updated"
    COMPONENT_ADDED = "component_added"
    COMPONENT_REMOVED = "component_removed"
    COMPONENT_MODIFIED = "component_modified"
    SETTINGS_CHANGED = "settings_changed"
    PERMISSIONS_CHANGED = "permissions_changed"


class VersionStatus(str, Enum):
    """Status of dashboard versions."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"
    ROLLBACK = "rollback"


class NotificationType(str, Enum):
    """Types of update notifications."""
    VERSION_CREATED = "version_created"
    VERSION_PUBLISHED = "version_published"
    DATA_UPDATED = "data_updated"
    BREAKING_CHANGE = "breaking_change"
    SCHEDULED_UPDATE = "scheduled_update"
    ROLLBACK_PERFORMED = "rollback_performed"


class DashboardVersion(BaseModel):
    """Represents a version of a dashboard."""

    version_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dashboard_id: str = Field(..., description="Parent dashboard ID")

    # Version information
    version_number: str = Field(..., description="Semantic version (e.g., 1.2.3)")
    version_name: Optional[str] = Field(None, description="Human-readable version name")
    status: VersionStatus = Field(default=VersionStatus.DRAFT)

    # Content
    dashboard_config: Dict[str, Any] = Field(..., description="Complete dashboard configuration")
    layout_specification: Dict[str, Any] = Field(..., description="Layout specification")
    component_definitions: List[Dict[str, Any]] = Field(default_factory=list)

    # Metadata
    created_by: str = Field(..., description="User who created this version")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    # Change tracking
    change_summary: str = Field(..., description="Summary of changes in this version")
    change_details: List[Dict[str, Any]] = Field(default_factory=list)
    parent_version_id: Optional[str] = None

    # Technical details
    content_hash: str = Field(..., description="Hash of dashboard content for integrity")
    size_bytes: int = Field(default=0, description="Size of version data")

    # Compatibility and dependencies
    api_version: str = Field(default="1.0", description="API version compatibility")
    dependencies: List[str] = Field(default_factory=list, description="External dependencies")
    breaking_changes: List[str] = Field(default_factory=list, description="Breaking changes from previous version")

    # Performance and quality metrics
    performance_score: Optional[float] = None
    quality_score: Optional[float] = None
    test_results: Dict[str, Any] = Field(default_factory=dict)


class ChangeRecord(BaseModel):
    """Records a specific change made to a dashboard."""

    change_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dashboard_id: str = Field(..., description="Dashboard that was changed")
    version_id: str = Field(..., description="Version where change occurred")

    # Change details
    change_type: ChangeType = Field(..., description="Type of change")
    component_id: Optional[str] = None
    field_path: Optional[str] = None  # JSON path to changed field

    # Change content
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    diff: Optional[Dict[str, Any]] = None

    # Context
    change_reason: Optional[str] = None
    user_id: str = Field(..., description="User who made the change")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Impact assessment
    impact_level: str = Field(default="low", description="low, medium, high, critical")
    affected_components: List[str] = Field(default_factory=list)
    validation_status: str = Field(default="pending", description="pending, passed, failed")


class UpdateNotification(BaseModel):
    """Notification about dashboard updates."""

    notification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dashboard_id: str = Field(..., description="Dashboard that was updated")

    # Notification details
    notification_type: NotificationType = Field(..., description="Type of notification")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")

    # Targeting
    recipients: List[str] = Field(..., description="User IDs to notify")
    channels: List[str] = Field(default_factory=list, description="Notification channels")

    # Content
    version_info: Optional[Dict[str, Any]] = None
    change_summary: Optional[str] = None
    action_required: bool = Field(default=False)
    action_deadline: Optional[datetime] = None

    # Status
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    read_receipts: Dict[str, datetime] = Field(default_factory=dict)

    # Metadata
    priority: str = Field(default="normal", description="low, normal, high, urgent")
    category: str = Field(default="update", description="Notification category")


class VersionManager:
    """Manages dashboard versions and version control operations."""

    def __init__(self):
        self.versions: Dict[str, List[DashboardVersion]] = {}  # dashboard_id -> versions
        self.change_tracker = ChangeTracker()
        self.update_notifier = UpdateNotifier()

    async def create_version(
        self,
        dashboard_id: str,
        dashboard_config: Dict[str, Any],
        user_id: str,
        change_summary: str,
        version_name: Optional[str] = None
    ) -> DashboardVersion:
        """Create a new version of a dashboard."""
        try:
            # Get current versions for this dashboard
            dashboard_versions = self.versions.get(dashboard_id, [])

            # Determine version number
            if not dashboard_versions:
                version_number = "1.0.0"
                parent_version_id = None
            else:
                # Get latest version and increment
                latest_version = max(dashboard_versions, key=lambda v: v.created_at)
                version_number = self._increment_version(latest_version.version_number)
                parent_version_id = latest_version.version_id

            # Generate content hash
            content_str = json.dumps(dashboard_config, sort_keys=True)
            content_hash = hashlib.sha256(content_str.encode()).hexdigest()

            # Create version
            version = DashboardVersion(
                dashboard_id=dashboard_id,
                version_number=version_number,
                version_name=version_name,
                dashboard_config=dashboard_config,
                layout_specification=dashboard_config.get("layout", {}),
                created_by=user_id,
                change_summary=change_summary,
                parent_version_id=parent_version_id,
                content_hash=content_hash,
                size_bytes=len(content_str.encode())
            )

            # Track changes if this isn't the first version
            if parent_version_id:
                latest_config = dashboard_versions[-1].dashboard_config
                changes = await self.change_tracker.detect_changes(
                    dashboard_id, version.version_id, latest_config, dashboard_config, user_id
                )
                version.change_details = [change.dict() for change in changes]

            # Store version
            if dashboard_id not in self.versions:
                self.versions[dashboard_id] = []
            self.versions[dashboard_id].append(version)

            logger.info(f"Created version {version_number} for dashboard {dashboard_id}")

            # Send notification
            await self.update_notifier.notify_version_created(version)

            return version

        except Exception as e:
            logger.error(f"Failed to create version: {str(e)}")
            raise

    async def publish_version(
        self,
        dashboard_id: str,
        version_id: str,
        user_id: str
    ) -> bool:
        """Publish a version to make it active."""
        try:
            version = await self.get_version(dashboard_id, version_id)
            if not version:
                raise ValueError(f"Version {version_id} not found")

            # Deactivate current active version
            await self._deactivate_current_version(dashboard_id)

            # Activate this version
            version.status = VersionStatus.ACTIVE
            version.published_at = datetime.utcnow()

            logger.info(f"Published version {version.version_number} for dashboard {dashboard_id}")

            # Send notification
            await self.update_notifier.notify_version_published(version)

            return True

        except Exception as e:
            logger.error(f"Failed to publish version: {str(e)}")
            return False

    async def rollback_to_version(
        self,
        dashboard_id: str,
        target_version_id: str,
        user_id: str,
        reason: str
    ) -> DashboardVersion:
        """Rollback dashboard to a previous version."""
        try:
            target_version = await self.get_version(dashboard_id, target_version_id)
            if not target_version:
                raise ValueError(f"Target version {target_version_id} not found")

            # Create new version based on target version
            rollback_version = await self.create_version(
                dashboard_id=dashboard_id,
                dashboard_config=target_version.dashboard_config,
                user_id=user_id,
                change_summary=f"Rollback to version {target_version.version_number}: {reason}",
                version_name=f"Rollback to {target_version.version_number}"
            )

            # Mark as rollback
            rollback_version.status = VersionStatus.ROLLBACK

            # Publish the rollback version
            await self.publish_version(dashboard_id, rollback_version.version_id, user_id)

            logger.info(f"Rolled back dashboard {dashboard_id} to version {target_version.version_number}")

            # Send notification
            await self.update_notifier.notify_rollback_performed(rollback_version, target_version)

            return rollback_version

        except Exception as e:
            logger.error(f"Failed to rollback: {str(e)}")
            raise

    async def get_version(
        self,
        dashboard_id: str,
        version_id: str
    ) -> Optional[DashboardVersion]:
        """Get a specific version of a dashboard."""
        dashboard_versions = self.versions.get(dashboard_id, [])
        for version in dashboard_versions:
            if version.version_id == version_id:
                return version
        return None

    async def get_active_version(self, dashboard_id: str) -> Optional[DashboardVersion]:
        """Get the currently active version of a dashboard."""
        dashboard_versions = self.versions.get(dashboard_id, [])
        for version in dashboard_versions:
            if version.status == VersionStatus.ACTIVE:
                return version
        return None

    async def get_version_history(
        self,
        dashboard_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[DashboardVersion]:
        """Get version history for a dashboard."""
        dashboard_versions = self.versions.get(dashboard_id, [])
        dashboard_versions.sort(key=lambda v: v.created_at, reverse=True)
        return dashboard_versions[offset:offset + limit]

    async def compare_versions(
        self,
        dashboard_id: str,
        version_id_1: str,
        version_id_2: str
    ) -> Dict[str, Any]:
        """Compare two versions and return differences."""
        version_1 = await self.get_version(dashboard_id, version_id_1)
        version_2 = await self.get_version(dashboard_id, version_id_2)

        if not version_1 or not version_2:
            raise ValueError("One or both versions not found")

        return await self.change_tracker.compare_configurations(
            version_1.dashboard_config,
            version_2.dashboard_config
        )

    async def delete_version(
        self,
        dashboard_id: str,
        version_id: str,
        user_id: str
    ) -> bool:
        """Delete a version (if not active)."""
        try:
            dashboard_versions = self.versions.get(dashboard_id, [])
            version_to_delete = None

            for i, version in enumerate(dashboard_versions):
                if version.version_id == version_id:
                    if version.status == VersionStatus.ACTIVE:
                        raise ValueError("Cannot delete active version")
                    version_to_delete = (i, version)
                    break

            if not version_to_delete:
                raise ValueError(f"Version {version_id} not found")

            # Remove version
            dashboard_versions.pop(version_to_delete[0])

            logger.info(f"Deleted version {version_to_delete[1].version_number} for dashboard {dashboard_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete version: {str(e)}")
            return False

    def _increment_version(self, current_version: str) -> str:
        """Increment version number using semantic versioning."""
        try:
            major, minor, patch = map(int, current_version.split('.'))
            return f"{major}.{minor}.{patch + 1}"
        except:
            return "1.0.1"  # Fallback

    async def _deactivate_current_version(self, dashboard_id: str) -> None:
        """Deactivate currently active version."""
        dashboard_versions = self.versions.get(dashboard_id, [])
        for version in dashboard_versions:
            if version.status == VersionStatus.ACTIVE:
                version.status = VersionStatus.ARCHIVED
                version.archived_at = datetime.utcnow()


class ChangeTracker:
    """Tracks and analyzes changes between dashboard versions."""

    def __init__(self):
        self.change_history: Dict[str, List[ChangeRecord]] = {}

    async def detect_changes(
        self,
        dashboard_id: str,
        version_id: str,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        user_id: str
    ) -> List[ChangeRecord]:
        """Detect changes between two dashboard configurations."""
        changes = []

        # Compare top-level properties
        for key in set(old_config.keys()) | set(new_config.keys()):
            if key not in old_config:
                # New field added
                changes.append(ChangeRecord(
                    dashboard_id=dashboard_id,
                    version_id=version_id,
                    change_type=ChangeType.COMPONENT_ADDED,
                    field_path=key,
                    old_value=None,
                    new_value=new_config[key],
                    user_id=user_id,
                    impact_level=self._assess_impact_level(key, None, new_config[key])
                ))
            elif key not in new_config:
                # Field removed
                changes.append(ChangeRecord(
                    dashboard_id=dashboard_id,
                    version_id=version_id,
                    change_type=ChangeType.COMPONENT_REMOVED,
                    field_path=key,
                    old_value=old_config[key],
                    new_value=None,
                    user_id=user_id,
                    impact_level=self._assess_impact_level(key, old_config[key], None)
                ))
            elif old_config[key] != new_config[key]:
                # Field modified
                changes.append(ChangeRecord(
                    dashboard_id=dashboard_id,
                    version_id=version_id,
                    change_type=ChangeType.COMPONENT_MODIFIED,
                    field_path=key,
                    old_value=old_config[key],
                    new_value=new_config[key],
                    user_id=user_id,
                    impact_level=self._assess_impact_level(key, old_config[key], new_config[key])
                ))

        # Store changes
        if dashboard_id not in self.change_history:
            self.change_history[dashboard_id] = []
        self.change_history[dashboard_id].extend(changes)

        return changes

    async def compare_configurations(
        self,
        config_1: Dict[str, Any],
        config_2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare two configurations and return detailed diff."""
        return {
            "added": self._find_added_items(config_1, config_2),
            "removed": self._find_removed_items(config_1, config_2),
            "modified": self._find_modified_items(config_1, config_2),
            "unchanged": self._find_unchanged_items(config_1, config_2)
        }

    def _assess_impact_level(
        self,
        field_path: str,
        old_value: Any,
        new_value: Any
    ) -> str:
        """Assess the impact level of a change."""
        # Critical changes
        if field_path in ["charts", "layout", "data_sources"]:
            return "high"

        # Medium impact changes
        if field_path in ["title", "filters", "styling"]:
            return "medium"

        # Low impact changes
        return "low"

    def _find_added_items(self, config_1: Dict, config_2: Dict) -> Dict[str, Any]:
        """Find items added in config_2 that weren't in config_1."""
        added = {}
        for key, value in config_2.items():
            if key not in config_1:
                added[key] = value
        return added

    def _find_removed_items(self, config_1: Dict, config_2: Dict) -> Dict[str, Any]:
        """Find items removed in config_2 that were in config_1."""
        removed = {}
        for key, value in config_1.items():
            if key not in config_2:
                removed[key] = value
        return removed

    def _find_modified_items(self, config_1: Dict, config_2: Dict) -> Dict[str, Any]:
        """Find items modified between configs."""
        modified = {}
        for key in config_1.keys() & config_2.keys():
            if config_1[key] != config_2[key]:
                modified[key] = {
                    "old": config_1[key],
                    "new": config_2[key]
                }
        return modified

    def _find_unchanged_items(self, config_1: Dict, config_2: Dict) -> List[str]:
        """Find items that remained unchanged."""
        unchanged = []
        for key in config_1.keys() & config_2.keys():
            if config_1[key] == config_2[key]:
                unchanged.append(key)
        return unchanged


class UpdateNotifier:
    """Manages notifications about dashboard updates."""

    def __init__(self):
        self.notification_history: List[UpdateNotification] = []
        self.subscribers: Dict[str, List[str]] = {}  # dashboard_id -> user_ids

    async def subscribe_to_updates(
        self,
        dashboard_id: str,
        user_id: str,
        notification_types: Optional[List[NotificationType]] = None
    ) -> bool:
        """Subscribe a user to dashboard update notifications."""
        if dashboard_id not in self.subscribers:
            self.subscribers[dashboard_id] = []

        if user_id not in self.subscribers[dashboard_id]:
            self.subscribers[dashboard_id].append(user_id)

        logger.info(f"User {user_id} subscribed to updates for dashboard {dashboard_id}")
        return True

    async def unsubscribe_from_updates(
        self,
        dashboard_id: str,
        user_id: str
    ) -> bool:
        """Unsubscribe a user from dashboard update notifications."""
        if dashboard_id in self.subscribers and user_id in self.subscribers[dashboard_id]:
            self.subscribers[dashboard_id].remove(user_id)
            logger.info(f"User {user_id} unsubscribed from updates for dashboard {dashboard_id}")
            return True
        return False

    async def notify_version_created(self, version: DashboardVersion) -> None:
        """Send notification when a new version is created."""
        recipients = self.subscribers.get(version.dashboard_id, [])
        if not recipients:
            return

        notification = UpdateNotification(
            dashboard_id=version.dashboard_id,
            notification_type=NotificationType.VERSION_CREATED,
            title=f"New version created: {version.version_number}",
            message=f"Version {version.version_number} has been created for dashboard {version.dashboard_id}. Changes: {version.change_summary}",
            recipients=recipients,
            version_info={
                "version_id": version.version_id,
                "version_number": version.version_number,
                "change_summary": version.change_summary
            }
        )

        await self._send_notification(notification)

    async def notify_version_published(self, version: DashboardVersion) -> None:
        """Send notification when a version is published."""
        recipients = self.subscribers.get(version.dashboard_id, [])
        if not recipients:
            return

        notification = UpdateNotification(
            dashboard_id=version.dashboard_id,
            notification_type=NotificationType.VERSION_PUBLISHED,
            title=f"Dashboard updated to version {version.version_number}",
            message=f"Dashboard {version.dashboard_id} has been updated to version {version.version_number}",
            recipients=recipients,
            priority="high",
            version_info={
                "version_id": version.version_id,
                "version_number": version.version_number,
                "published_at": version.published_at.isoformat() if version.published_at else None
            }
        )

        await self._send_notification(notification)

    async def notify_rollback_performed(
        self,
        rollback_version: DashboardVersion,
        target_version: DashboardVersion
    ) -> None:
        """Send notification when a rollback is performed."""
        recipients = self.subscribers.get(rollback_version.dashboard_id, [])
        if not recipients:
            return

        notification = UpdateNotification(
            dashboard_id=rollback_version.dashboard_id,
            notification_type=NotificationType.ROLLBACK_PERFORMED,
            title=f"Dashboard rolled back to version {target_version.version_number}",
            message=f"Dashboard {rollback_version.dashboard_id} has been rolled back to version {target_version.version_number}",
            recipients=recipients,
            priority="urgent",
            action_required=True,
            version_info={
                "rollback_version": rollback_version.version_number,
                "target_version": target_version.version_number
            }
        )

        await self._send_notification(notification)

    async def _send_notification(self, notification: UpdateNotification) -> None:
        """Send notification to recipients."""
        # In a real implementation, this would integrate with email, Slack, etc.
        notification.sent_at = datetime.utcnow()
        self.notification_history.append(notification)

        logger.info(f"Sent notification {notification.notification_type.value} for dashboard {notification.dashboard_id} to {len(notification.recipients)} recipients")

    async def get_notifications_for_user(
        self,
        user_id: str,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[UpdateNotification]:
        """Get notifications for a specific user."""
        user_notifications = [
            notif for notif in self.notification_history
            if user_id in notif.recipients
        ]

        if unread_only:
            user_notifications = [
                notif for notif in user_notifications
                if user_id not in notif.read_receipts
            ]

        user_notifications.sort(key=lambda n: n.created_at, reverse=True)
        return user_notifications[:limit]

    async def mark_notification_read(
        self,
        notification_id: str,
        user_id: str
    ) -> bool:
        """Mark a notification as read by a user."""
        for notification in self.notification_history:
            if notification.notification_id == notification_id:
                notification.read_receipts[user_id] = datetime.utcnow()
                return True
        return False
