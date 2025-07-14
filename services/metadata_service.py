"""
Metadata management service that coordinates all metadata operations.

This service provides a unified interface for:
- Automatic metadata extraction
- User-enhanced metadata management
- Metadata validation and quality scoring
- Metadata search and discovery
- Metadata lineage tracking
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
from pydantic import BaseModel, Field
import uuid
import logging

from core.metadata import (
    MetadataExtractor,
    MetadataEnhancementService,
    MetadataValidator,
    DatasetMetadata,
    ColumnMetadata,
    UserEnhancedMetadata,
    MetadataExtractionResult,
    MetadataEnhancementResult,
    MetadataValidationResult,
    MetadataEnhancementRequest,
    MetadataContext,
    MetadataType,
    MetadataStatus,
    BusinessMeaning,
    SensitivityMarking,
    CustomMetadataField,
    MetadataTemplate
)

logger = logging.getLogger(__name__)


class MetadataSearchRequest(BaseModel):
    """Request for searching metadata."""

    query: str = Field(..., description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    limit: int = Field(default=50, description="Maximum results")
    offset: int = Field(default=0, description="Result offset for pagination")
    sort_by: str = Field(default="relevance", description="Sort criteria")
    include_lineage: bool = Field(default=False, description="Include lineage information")


class MetadataSearchResult(BaseModel):
    """Result of metadata search operation."""

    total_count: int = Field(..., description="Total matching results")
    results: List[Union[DatasetMetadata, UserEnhancedMetadata]] = Field(..., description="Search results")
    facets: Dict[str, Any] = Field(default_factory=dict, description="Search facets")
    query_time_ms: float = Field(..., description="Query execution time")


class MetadataLineageRequest(BaseModel):
    """Request for retrieving metadata lineage."""

    element_id: str = Field(..., description="Element ID to trace")
    direction: str = Field(default="both", description="Lineage direction: upstream, downstream, both")
    depth: int = Field(default=3, description="Maximum lineage depth")
    include_technical: bool = Field(default=True, description="Include technical lineage")
    include_business: bool = Field(default=True, description="Include business lineage")


class MetadataSummaryRequest(BaseModel):
    """Request for metadata summary statistics."""

    scope: str = Field(default="all", description="Summary scope: all, dataset, column")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters to apply")
    group_by: Optional[List[str]] = Field(None, description="Grouping dimensions")


class MetadataSummary(BaseModel):
    """Summary statistics for metadata."""

    total_elements: int = Field(default=0)
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_status: Dict[str, int] = Field(default_factory=dict)
    quality_distribution: Dict[str, int] = Field(default_factory=dict)
    completeness_stats: Dict[str, float] = Field(default_factory=dict)
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)
    top_domains: List[Dict[str, Any]] = Field(default_factory=list)
    coverage_metrics: Dict[str, float] = Field(default_factory=dict)


class MetadataService:
    """Unified metadata management service."""

    def __init__(self, context: Optional[MetadataContext] = None):
        self.context = context or MetadataContext()
        self.extractor = MetadataExtractor(self.context)
        self.enhancement_service = MetadataEnhancementService(self.context)
        self.validator = MetadataValidator(self.context)

        # In-memory storage (in production, this would use a database)
        self.metadata_store: Dict[str, Union[DatasetMetadata, UserEnhancedMetadata]] = {}
        self.templates: Dict[str, MetadataTemplate] = {}
        self.custom_fields: Dict[str, CustomMetadataField] = {}

        logger.info("Metadata service initialized")

    async def extract_metadata(self, data: Any, **kwargs) -> MetadataExtractionResult:
        """
        Extract metadata automatically from data source.

        Args:
            data: Data source to extract metadata from
            **kwargs: Additional extraction options

        Returns:
            MetadataExtractionResult with extracted metadata
        """
        try:
            logger.info(f"Starting metadata extraction for data type: {type(data)}")

            # Extract metadata using the extractor
            result = await self.extractor.extract_metadata(data, **kwargs)

            if result.success and result.dataset_metadata:
                # Store extracted metadata
                dataset_id = result.dataset_metadata.dataset_id
                self.metadata_store[dataset_id] = result.dataset_metadata

                # Also store individual column metadata as enhanced metadata
                for col_name, col_meta in result.dataset_metadata.columns.items():
                    enhanced_col = UserEnhancedMetadata(
                        element_id=f"{dataset_id}_{col_name}",
                        element_type=MetadataType.COLUMN
                    )
                    # Set optional fields
                    enhanced_col.display_name = col_meta.display_name or col_name
                    enhanced_col.description = col_meta.description
                    enhanced_col.status = MetadataStatus.DRAFT
                    enhanced_col.created_by = self.context.user_id

                    self.metadata_store[enhanced_col.element_id] = enhanced_col

                logger.info(f"Successfully extracted metadata for dataset {dataset_id}")
            else:
                logger.error(f"Metadata extraction failed: {result.errors}")

            return result

        except Exception as e:
            logger.error(f"Metadata extraction error: {str(e)}")
            return MetadataExtractionResult(
                success=False,
                dataset_metadata=None,
                errors=[str(e)]
            )

    async def enhance_metadata(self, request: MetadataEnhancementRequest) -> MetadataEnhancementResult:
        """
        Enhance metadata with user-provided information.

        Args:
            request: Enhancement request with user data

        Returns:
            MetadataEnhancementResult with enhanced metadata
        """
        try:
            logger.info(f"Enhancing metadata for element {request.element_id}")

            # Process enhancement through the enhancement service
            result = await self.enhancement_service.enhance_metadata(request)

            if result.success and result.enhanced_metadata:
                # Store enhanced metadata
                self.metadata_store[request.element_id] = result.enhanced_metadata
                logger.info(f"Successfully enhanced metadata for element {request.element_id}")
            else:
                logger.warning(f"Metadata enhancement had issues: {result.validation_results}")

            return result

        except Exception as e:
            logger.error(f"Metadata enhancement error: {str(e)}")
            return MetadataEnhancementResult(
                success=False,
                element_id=request.element_id,
                enhanced_metadata=None,
                validation_results=[f"Enhancement failed: {str(e)}"]
            )

    async def validate_metadata(self, element_id: str) -> MetadataValidationResult:
        """
        Validate metadata for quality and consistency.

        Args:
            element_id: ID of element to validate

        Returns:
            MetadataValidationResult with validation details
        """
        try:
            logger.info(f"Validating metadata for element {element_id}")

            # Get metadata to validate
            metadata = self.metadata_store.get(element_id)
            if not metadata:
                return MetadataValidationResult(
                    element_id=element_id,
                    element_type=MetadataType.DATASET
                )

            # Validate using the validator
            result = await self.validator.validate_metadata(metadata)

            logger.info(f"Validation completed for element {element_id} with score {result.overall_score:.2f}")
            return result

        except Exception as e:
            logger.error(f"Metadata validation error: {str(e)}")
            return MetadataValidationResult(
                element_id=element_id,
                element_type=MetadataType.DATASET
            )

    async def batch_validate_metadata(self, element_ids: List[str]) -> List[MetadataValidationResult]:
        """Validate multiple metadata elements."""
        try:
            logger.info(f"Batch validating {len(element_ids)} metadata elements")

            # Get metadata for all elements
            metadata_list = []
            for element_id in element_ids:
                metadata = self.metadata_store.get(element_id)
                if metadata:
                    metadata_list.append(metadata)

            if not metadata_list:
                logger.warning("No metadata found for batch validation")
                return []

            # Perform batch validation
            results = await self.validator.batch_validate(metadata_list)

            logger.info(f"Batch validation completed for {len(results)} elements")
            return results

        except Exception as e:
            logger.error(f"Batch validation error: {str(e)}")
            return []

    async def search_metadata(self, request: MetadataSearchRequest) -> MetadataSearchResult:
        """
        Search metadata based on query and filters.

        Args:
            request: Search request with query and filters

        Returns:
            MetadataSearchResult with matching metadata
        """
        try:
            start_time = datetime.utcnow()
            logger.info(f"Searching metadata with query: '{request.query}'")

            # Simple in-memory search implementation
            # In production, this would use a proper search engine like Elasticsearch
            results = []
            query_lower = request.query.lower()

            for metadata in self.metadata_store.values():
                # Search in different fields based on metadata type
                if isinstance(metadata, DatasetMetadata):
                    searchable_text = " ".join([
                        metadata.name or "",
                        metadata.description or "",
                        metadata.business_domain or "",
                        " ".join(metadata.use_cases),
                        " ".join(metadata.stakeholders)
                    ]).lower()

                elif isinstance(metadata, UserEnhancedMetadata):
                    searchable_text = " ".join([
                        metadata.display_name or "",
                        metadata.description or "",
                        " ".join(metadata.tags),
                        " ".join(metadata.keywords),
                        " ".join(metadata.categories)
                    ]).lower()
                else:
                    continue

                # Check if query matches
                if query_lower in searchable_text:
                    # Apply filters if provided
                    if request.filters and not self._matches_search_filters(metadata, request.filters):
                        continue

                    results.append(metadata)

            # Sort results
            results = self._sort_search_results(results, request.sort_by)

            # Apply pagination
            total_count = len(results)
            paginated_results = results[request.offset:request.offset + request.limit]

            # Calculate query time
            end_time = datetime.utcnow()
            query_time_ms = (end_time - start_time).total_seconds() * 1000

            # Generate facets
            facets = self._generate_search_facets(results)

            logger.info(f"Search completed: {total_count} results in {query_time_ms:.2f}ms")

            return MetadataSearchResult(
                total_count=total_count,
                results=paginated_results,
                facets=facets,
                query_time_ms=query_time_ms
            )

        except Exception as e:
            logger.error(f"Metadata search error: {str(e)}")
            return MetadataSearchResult(
                total_count=0,
                results=[],
                facets={},
                query_time_ms=0.0
            )

    async def get_metadata_lineage(self, request: MetadataLineageRequest) -> Dict[str, Any]:
        """Get lineage information for a metadata element."""
        try:
            logger.info(f"Getting lineage for element {request.element_id}")

            metadata = self.metadata_store.get(request.element_id)
            if not metadata:
                return {"error": f"Metadata not found for element {request.element_id}"}

            # Build lineage graph
            lineage_graph = {
                "nodes": [],
                "edges": [],
                "root_element": request.element_id
            }

            # Add the root element
            lineage_graph["nodes"].append({
                "id": request.element_id,
                "type": getattr(metadata, 'element_type', 'dataset'),
                "name": getattr(metadata, 'display_name', getattr(metadata, 'name', request.element_id)),
                "level": 0
            })

            # Trace upstream and downstream lineage
            if request.direction in ["upstream", "both"]:
                self._trace_upstream_lineage(request.element_id, lineage_graph, request.depth)

            if request.direction in ["downstream", "both"]:
                self._trace_downstream_lineage(request.element_id, lineage_graph, request.depth)

            logger.info(f"Lineage retrieved: {len(lineage_graph['nodes'])} nodes, {len(lineage_graph['edges'])} edges")
            return lineage_graph

        except Exception as e:
            logger.error(f"Lineage retrieval error: {str(e)}")
            return {"error": str(e)}

    async def get_metadata_summary(self, request: MetadataSummaryRequest) -> MetadataSummary:
        """Get summary statistics for metadata."""
        try:
            logger.info(f"Generating metadata summary with scope: {request.scope}")

            # Filter metadata based on scope and filters
            filtered_metadata = []
            for metadata in self.metadata_store.values():
                if request.filters and not self._matches_search_filters(metadata, request.filters):
                    continue

                if request.scope == "dataset" and not isinstance(metadata, DatasetMetadata):
                    continue
                elif request.scope == "column" and not (isinstance(metadata, UserEnhancedMetadata) and metadata.element_type == MetadataType.COLUMN):
                    continue

                filtered_metadata.append(metadata)

            # Calculate summary statistics
            summary = MetadataSummary(
                total_elements=len(filtered_metadata)
            )

            # Count by type
            for metadata in filtered_metadata:
                if isinstance(metadata, DatasetMetadata):
                    metadata_type = "dataset"
                elif isinstance(metadata, UserEnhancedMetadata):
                    metadata_type = metadata.element_type.value
                else:
                    metadata_type = "unknown"

                summary.by_type[metadata_type] = summary.by_type.get(metadata_type, 0) + 1

            # Count by status (for enhanced metadata)
            for metadata in filtered_metadata:
                if isinstance(metadata, UserEnhancedMetadata):
                    status = metadata.status.value
                    summary.by_status[status] = summary.by_status.get(status, 0) + 1

            # Quality distribution
            quality_ranges = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
            for range_key in quality_ranges:
                summary.quality_distribution[range_key] = 0

            for metadata in filtered_metadata:
                quality_score = getattr(metadata, 'quality_score', 0.0)
                range_idx = min(int(quality_score * 5), 4)
                range_key = quality_ranges[range_idx]
                summary.quality_distribution[range_key] += 1

            # Completeness stats
            completeness_scores = []
            for metadata in filtered_metadata:
                if hasattr(metadata, 'completeness'):
                    completeness_scores.append(metadata.completeness)

            if completeness_scores:
                summary.completeness_stats = {
                    "mean": sum(completeness_scores) / len(completeness_scores),
                    "min": min(completeness_scores),
                    "max": max(completeness_scores)
                }

            # Top domains
            domain_counts = {}
            for metadata in filtered_metadata:
                domain = None
                if isinstance(metadata, DatasetMetadata):
                    domain = metadata.business_domain
                elif isinstance(metadata, UserEnhancedMetadata) and metadata.business_meaning:
                    domain = metadata.business_meaning.domain_context

                if domain:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1

            summary.top_domains = [
                {"domain": domain, "count": count}
                for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ]

            # Coverage metrics
            total_possible = len(self.metadata_store)
            if total_possible > 0:
                summary.coverage_metrics = {
                    "documented_percentage": (len([m for m in filtered_metadata if getattr(m, 'description', None)]) / total_possible) * 100,
                    "tagged_percentage": (len([m for m in filtered_metadata if getattr(m, 'tags', None)]) / total_possible) * 100,
                    "business_context_percentage": (len([m for m in filtered_metadata if getattr(m, 'business_meaning', None)]) / total_possible) * 100
                }

            logger.info(f"Metadata summary generated: {summary.total_elements} elements analyzed")
            return summary

        except Exception as e:
            logger.error(f"Summary generation error: {str(e)}")
            return MetadataSummary()

    async def create_template(self, template: MetadataTemplate) -> str:
        """Create a new metadata enhancement template."""
        try:
            template_id = await self.enhancement_service.create_template(template)
            self.templates[template_id] = template
            logger.info(f"Created metadata template: {template.name}")
            return template_id
        except Exception as e:
            logger.error(f"Template creation error: {str(e)}")
            raise

    async def add_custom_field(self, field: CustomMetadataField) -> str:
        """Add a custom metadata field definition."""
        try:
            field_id = await self.enhancement_service.add_custom_field(field)
            self.custom_fields[field_id] = field
            logger.info(f"Added custom metadata field: {field.name}")
            return field_id
        except Exception as e:
            logger.error(f"Custom field creation error: {str(e)}")
            raise

    async def get_metadata(self, element_id: str) -> Optional[Union[DatasetMetadata, UserEnhancedMetadata]]:
        """Get metadata for a specific element."""
        return self.metadata_store.get(element_id)

    async def list_metadata(self, metadata_type: Optional[MetadataType] = None, limit: int = 100, offset: int = 0) -> List[Union[DatasetMetadata, UserEnhancedMetadata]]:
        """List metadata with optional filtering."""
        results = []

        for metadata in list(self.metadata_store.values())[offset:offset + limit]:
            if metadata_type:
                if isinstance(metadata, DatasetMetadata) and metadata_type != MetadataType.DATASET:
                    continue
                elif isinstance(metadata, UserEnhancedMetadata) and metadata.element_type != metadata_type:
                    continue

            results.append(metadata)

        return results

    async def delete_metadata(self, element_id: str) -> bool:
        """Delete metadata for an element."""
        try:
            if element_id in self.metadata_store:
                del self.metadata_store[element_id]
                logger.info(f"Deleted metadata for element {element_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Metadata deletion error: {str(e)}")
            return False

    def _matches_search_filters(self, metadata: Any, filters: Dict[str, Any]) -> bool:
        """Check if metadata matches search filters."""
        for key, value in filters.items():
            if key == "element_type":
                if isinstance(metadata, DatasetMetadata) and value != "dataset":
                    return False
                elif isinstance(metadata, UserEnhancedMetadata) and metadata.element_type.value != value:
                    return False

            elif key == "business_domain":
                domain = None
                if isinstance(metadata, DatasetMetadata):
                    domain = metadata.business_domain
                elif isinstance(metadata, UserEnhancedMetadata) and metadata.business_meaning:
                    domain = metadata.business_meaning.domain_context

                if domain != value:
                    return False

            elif key == "status" and isinstance(metadata, UserEnhancedMetadata):
                if metadata.status.value != value:
                    return False

            elif key == "quality_min":
                quality = getattr(metadata, 'quality_score', 0.0)
                if quality < value:
                    return False

        return True

    def _sort_search_results(self, results: List[Any], sort_by: str) -> List[Any]:
        """Sort search results by specified criteria."""
        if sort_by == "name":
            return sorted(results, key=lambda x: getattr(x, 'name', getattr(x, 'display_name', '')))
        elif sort_by == "quality":
            return sorted(results, key=lambda x: getattr(x, 'quality_score', 0.0), reverse=True)
        elif sort_by == "updated":
            return sorted(results, key=lambda x: getattr(x, 'updated_at', getattr(x, 'extracted_at', datetime.min)), reverse=True)
        else:  # relevance (default)
            return results

    def _generate_search_facets(self, results: List[Any]) -> Dict[str, Any]:
        """Generate search facets from results."""
        facets = {
            "types": {},
            "domains": {},
            "status": {},
            "quality_ranges": {}
        }

        for metadata in results:
            # Type facets
            if isinstance(metadata, DatasetMetadata):
                metadata_type = "dataset"
            elif isinstance(metadata, UserEnhancedMetadata):
                metadata_type = metadata.element_type.value
            else:
                metadata_type = "unknown"

            facets["types"][metadata_type] = facets["types"].get(metadata_type, 0) + 1

            # Domain facets
            domain = None
            if isinstance(metadata, DatasetMetadata):
                domain = metadata.business_domain
            elif isinstance(metadata, UserEnhancedMetadata) and metadata.business_meaning:
                domain = metadata.business_meaning.domain_context

            if domain:
                facets["domains"][domain] = facets["domains"].get(domain, 0) + 1

            # Status facets (for enhanced metadata)
            if isinstance(metadata, UserEnhancedMetadata):
                status = metadata.status.value
                facets["status"][status] = facets["status"].get(status, 0) + 1

            # Quality range facets
            quality = getattr(metadata, 'quality_score', 0.0)
            if quality < 0.4:
                range_key = "low"
            elif quality < 0.7:
                range_key = "medium"
            else:
                range_key = "high"

            facets["quality_ranges"][range_key] = facets["quality_ranges"].get(range_key, 0) + 1

        return facets

    def _trace_upstream_lineage(self, element_id: str, graph: Dict[str, Any], max_depth: int, current_depth: int = 0):
        """Trace upstream lineage for an element."""
        if current_depth >= max_depth:
            return

        metadata = self.metadata_store.get(element_id)
        if not metadata:
            return

        # For enhanced metadata, check parent elements
        if isinstance(metadata, UserEnhancedMetadata):
            for parent_id in metadata.parent_elements:
                if not any(node["id"] == parent_id for node in graph["nodes"]):
                    parent_metadata = self.metadata_store.get(parent_id)
                    if parent_metadata:
                        graph["nodes"].append({
                            "id": parent_id,
                            "type": getattr(parent_metadata, 'element_type', 'dataset'),
                            "name": getattr(parent_metadata, 'display_name', getattr(parent_metadata, 'name', parent_id)),
                            "level": -(current_depth + 1)
                        })

                graph["edges"].append({
                    "from": parent_id,
                    "to": element_id,
                    "type": "parent_child"
                })

                # Recursively trace upstream
                self._trace_upstream_lineage(parent_id, graph, max_depth, current_depth + 1)

    def _trace_downstream_lineage(self, element_id: str, graph: Dict[str, Any], max_depth: int, current_depth: int = 0):
        """Trace downstream lineage for an element."""
        if current_depth >= max_depth:
            return

        metadata = self.metadata_store.get(element_id)
        if not metadata:
            return

        # For enhanced metadata, check child elements
        if isinstance(metadata, UserEnhancedMetadata):
            for child_id in metadata.child_elements:
                if not any(node["id"] == child_id for node in graph["nodes"]):
                    child_metadata = self.metadata_store.get(child_id)
                    if child_metadata:
                        graph["nodes"].append({
                            "id": child_id,
                            "type": getattr(child_metadata, 'element_type', 'dataset'),
                            "name": getattr(child_metadata, 'display_name', getattr(child_metadata, 'name', child_id)),
                            "level": current_depth + 1
                        })

                graph["edges"].append({
                    "from": element_id,
                    "to": child_id,
                    "type": "parent_child"
                })

                # Recursively trace downstream
                self._trace_downstream_lineage(child_id, graph, max_depth, current_depth + 1)
