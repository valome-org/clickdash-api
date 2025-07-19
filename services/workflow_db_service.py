"""
Workflow Database Service - Handles database operations for all 8 phases.

This service ensures that all workflow operations are properly persisted to the database
and provides a unified interface for creating and managing workflow entities.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import uuid

from sqlalchemy.orm import Session
from database.models import User
from database.workflow_models import (
    Workflow, DataSource, DataProcessingJob, DataValidation,
    DataCleanup, Approval, DashboardVersion, ExportJob, Notification,
    WorkflowStatus, DataSourceType, ProcessingStatus, ApprovalStatus
)

logger = logging.getLogger(__name__)


class WorkflowDatabaseService:
    """Service for managing workflow database operations across all phases."""

    def __init__(self):
        logger.info("Workflow Database Service initialized")

    # Phase 1: Data Sources
    async def create_data_source(
        self,
        workflow_id: str,
        source_name: str,
        source_type: str,
        file_path: Optional[str] = None,
        connection_params: Optional[Dict[str, Any]] = None,
        schema_info: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Optional[DataSource]:
        """Create a data source record."""
        try:
            if not db:
                return None

            # Get workflow record
            workflow = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
            if not workflow:
                logger.error(f"Workflow {workflow_id} not found")
                return None

            # Map string to enum
            source_type_enum = DataSourceType.EXCEL  # Default
            try:
                source_type_enum = DataSourceType(source_type.lower())
            except ValueError:
                logger.warning(f"Unknown source type {source_type}, using EXCEL as default")

            data_source = DataSource(
                source_id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                name=source_name,
                source_type=source_type_enum,
                connection_params=connection_params or {},
                file_path=file_path,
                schema_info=schema_info or {},
                status="connected"
            )

            db.add(data_source)
            db.commit()
            db.refresh(data_source)

            logger.info(f"Created data source {data_source.source_id} for workflow {workflow_id}")
            return data_source

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to create data source: {str(e)}")
            return None

    # Phase 2: Data Processing
    async def create_processing_job(
        self,
        workflow_id: str,
        data_source_id: str,
        processing_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        input_rows: int = 0,
        output_rows: int = 0,
        quality_metrics: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Optional[DataProcessingJob]:
        """Create a data processing job record."""
        try:
            if not db:
                return None

            # Get workflow and data source
            workflow = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
            if not workflow:
                return None

            data_source = db.query(DataSource).filter(DataSource.source_id == data_source_id).first()
            if not data_source:
                return None

            processing_job = DataProcessingJob(
                job_id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                data_source_id=data_source.id,
                processing_type=processing_type,
                parameters=parameters or {},
                input_rows=input_rows,
                output_rows=output_rows,
                quality_metrics=quality_metrics or {},
                status=ProcessingStatus.COMPLETED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )

            db.add(processing_job)
            db.commit()
            db.refresh(processing_job)

            logger.info(f"Created processing job {processing_job.job_id} for workflow {workflow_id}")
            return processing_job

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to create processing job: {str(e)}")
            return None

    # Phase 3: Data Validation
    async def create_validation_record(
        self,
        workflow_id: str,
        processing_job_id: str,
        validation_results: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Optional[DataValidation]:
        """Create a data validation record."""
        try:
            if not db:
                return None

            # Get workflow and processing job
            workflow = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
            if not workflow:
                return None

            processing_job = db.query(DataProcessingJob).filter(DataProcessingJob.job_id == processing_job_id).first()
            if not processing_job:
                return None

            validation = DataValidation(
                validation_id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                processing_job_id=processing_job.id,
                validation_rules=validation_results.get("rules", {}),
                validation_scope="full",
                overall_quality_score=validation_results.get("overall_quality_score", 85.0),
                total_rows_validated=validation_results.get("total_rows", 0),
                valid_rows=validation_results.get("valid_rows", 0),
                invalid_rows=validation_results.get("invalid_rows", 0),
                validation_issues=validation_results.get("issues", []),
                recommendations=validation_results.get("recommendations", []),
                status="completed"
            )

            db.add(validation)
            db.commit()
            db.refresh(validation)

            logger.info(f"Created validation record {validation.validation_id} for workflow {workflow_id}")
            return validation

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to create validation record: {str(e)}")
            return None

    # Phase 4: Data Cleanup
    async def create_cleanup_record(
        self,
        workflow_id: str,
        validation_id: str,
        cleanup_results: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Optional[DataCleanup]:
        """Create a data cleanup record."""
        try:
            if not db:
                return None

            # Get workflow and validation
            workflow = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
            if not workflow:
                return None

            validation = db.query(DataValidation).filter(DataValidation.validation_id == validation_id).first()
            if not validation:
                return None

            cleanup = DataCleanup(
                cleanup_id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                validation_id=validation.id,
                cleanup_rules=cleanup_results.get("rules", {}),
                cleanup_strategy="guided",
                original_rows=cleanup_results.get("original_rows", 0),
                cleaned_rows=cleanup_results.get("cleaned_rows", 0),
                removed_rows=cleanup_results.get("removed_rows", 0),
                modified_rows=cleanup_results.get("modified_rows", 0),
                operations_performed=cleanup_results.get("operations", []),
                cleanup_summary=cleanup_results.get("summary", {}),
                status="completed"
            )

            db.add(cleanup)
            db.commit()
            db.refresh(cleanup)

            logger.info(f"Created cleanup record {cleanup.cleanup_id} for workflow {workflow_id}")
            return cleanup

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to create cleanup record: {str(e)}")
            return None

    # Phase 8: Dashboard Generation
    async def create_dashboard_version(
        self,
        workflow_id: str,
        dashboard_id: int,
        version_number: str,
        dashboard_config: Dict[str, Any],
        user_id: int,
        db: Optional[Session] = None
    ) -> Optional[DashboardVersion]:
        """Create a dashboard version record."""
        try:
            if not db:
                return None

            # Get workflow
            workflow = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
            if not workflow:
                return None

            dashboard_version = DashboardVersion(
                version_id=str(uuid.uuid4()),
                workflow_id=workflow.id,
                dashboard_id=dashboard_id,
                version_number=version_number,
                version_name=f"Generated via AI Workflow",
                description=f"Dashboard generated through 8-phase AI workflow",
                dashboard_config=dashboard_config,
                generation_params={"ai_generated": True, "workflow_id": workflow_id},
                ai_analysis=workflow.ai_analysis_results or {},
                status="published",
                is_current=True,
                created_by=user_id
            )

            db.add(dashboard_version)
            db.commit()
            db.refresh(dashboard_version)

            logger.info(f"Created dashboard version {dashboard_version.version_id} for workflow {workflow_id}")
            return dashboard_version

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to create dashboard version: {str(e)}")
            return None

    # Cross-phase utilities
    async def get_workflow_by_id(self, workflow_id: str, db: Session) -> Optional[Workflow]:
        """Get workflow record by workflow_id."""
        try:
            workflow = db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()
            return workflow
        except Exception as e:
            logger.error(f"Failed to get workflow: {str(e)}")
            return None

    async def update_workflow_status(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        current_phase: Optional[str] = None,
        db: Optional[Session] = None
    ) -> bool:
        """Update workflow status and phase."""
        try:
            if not db:
                return False

            workflow = await self.get_workflow_by_id(workflow_id, db)
            if not workflow:
                return False

            setattr(workflow, 'status', status)
            if current_phase:
                setattr(workflow, 'current_phase', current_phase)
                # Add to completed phases if not already there
                phases = getattr(workflow, 'phases_completed') or []
                if current_phase not in phases:
                    phases.append(current_phase)
                    setattr(workflow, 'phases_completed', phases)

            setattr(workflow, 'updated_at', datetime.utcnow())

            if status == WorkflowStatus.COMPLETED:
                setattr(workflow, 'completed_at', datetime.utcnow())

            db.commit()
            logger.info(f"Updated workflow {workflow_id} status to {status.value}")
            return True

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Failed to update workflow status: {str(e)}")
            return False

    async def get_workflow_summary(self, workflow_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get comprehensive workflow summary with all related records."""
        try:
            workflow = await self.get_workflow_by_id(workflow_id, db)
            if not workflow:
                return None

            # Get related records
            data_sources = db.query(DataSource).filter(DataSource.workflow_id == workflow.id).all()
            processing_jobs = db.query(DataProcessingJob).filter(DataProcessingJob.workflow_id == workflow.id).all()
            validations = db.query(DataValidation).filter(DataValidation.workflow_id == workflow.id).all()
            cleanups = db.query(DataCleanup).filter(DataCleanup.workflow_id == workflow.id).all()
            approvals = db.query(Approval).filter(Approval.workflow_id == workflow.id).all()
            dashboard_versions = db.query(DashboardVersion).filter(DashboardVersion.workflow_id == workflow.id).all()

            return {
                "workflow": workflow.to_dict(),
                "data_sources": [ds.source_id for ds in data_sources],
                "processing_jobs": [pj.job_id for pj in processing_jobs],
                "validations": [v.validation_id for v in validations],
                "cleanups": [c.cleanup_id for c in cleanups],
                "approvals": [a.approval_id for a in approvals],
                "dashboard_versions": [dv.version_id for dv in dashboard_versions],
                "total_records": {
                    "data_sources": len(data_sources),
                    "processing_jobs": len(processing_jobs),
                    "validations": len(validations),
                    "cleanups": len(cleanups),
                    "approvals": len(approvals),
                    "dashboard_versions": len(dashboard_versions)
                }
            }

        except Exception as e:
            logger.error(f"Failed to get workflow summary: {str(e)}")
            return None


# Create singleton instance
workflow_db_service = WorkflowDatabaseService()
