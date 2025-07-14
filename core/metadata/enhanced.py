"""
User-enhanced metadata system.

This module provides capabilities for users to enrich automatically extracted metadata with:
- Business context and meaning
- Custom descriptions and labels
- Data privacy and sensitivity markings
- Custom metadata fields
- User-defined relationships and hierarchies
"""

from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid

from .base import MetadataInterface, MetadataType, MetadataStatus, MetadataLineage, MetadataContext, DataPrivacyLevel


class BusinessMeaning(BaseModel):
    """Business meaning and context for data elements."""

    primary_meaning: str = Field(..., description="Primary business meaning")
    secondary_meanings: List[str] = Field(default_factory=list, description="Alternative interpretations")
    business_rules: List[str] = Field(default_factory=list, description="Business rules governing this data")
    stakeholders: List[str] = Field(default_factory=list, description="Business stakeholders")
    use_cases: List[str] = Field(default_factory=list, description="Primary use cases")
    domain_context: Optional[str] = Field(None, description="Business domain context")
    glossary_terms: List[str] = Field(default_factory=list, description="Related glossary terms")
    examples: List[str] = Field(default_factory=list, description="Example values with context")


class SensitivityMarking(BaseModel):
    """Data sensitivity and privacy classification."""

    privacy_level: DataPrivacyLevel = Field(..., description="Privacy classification level")
    pii_indicators: List[str] = Field(default_factory=list, description="PII indicators present")
    compliance_tags: List[str] = Field(default_factory=list, description="Compliance requirements")
    access_restrictions: List[str] = Field(default_factory=list, description="Access restrictions")
    retention_policy: Optional[str] = Field(None, description="Data retention policy")
    anonymization_notes: Optional[str] = Field(None, description="Anonymization requirements")
    legal_basis: Optional[str] = Field(None, description="Legal basis for processing")


class CustomMetadataField(BaseModel):
    """User-defined custom metadata field."""

    field_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Field name")
    display_name: str = Field(..., description="Human-readable display name")
    field_type: str = Field(..., description="Field data type")
    description: Optional[str] = Field(None, description="Field description")
    allowed_values: Optional[List[str]] = Field(None, description="Allowed values for enumerated fields")
    default_value: Optional[Any] = Field(None, description="Default value")
    required: bool = Field(default=False, description="Whether field is required")
    validation_rules: List[str] = Field(default_factory=list, description="Validation rules")
    category: Optional[str] = Field(None, description="Field category")
    created_by: Optional[str] = Field(None, description="Field creator")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('field_type')
    def validate_field_type(cls, v):
        allowed_types = ['string', 'integer', 'float', 'boolean', 'date', 'datetime', 'enum', 'text', 'url', 'email']
        if v not in allowed_types:
            raise ValueError(f"Field type must be one of: {allowed_types}")
        return v


class UserEnhancedMetadata(BaseModel):
    """Complete user-enhanced metadata for a data element."""

    element_id: str = Field(..., description="Unique identifier for the data element")
    element_type: MetadataType = Field(..., description="Type of metadata element")

    # User-provided information
    display_name: Optional[str] = None
    description: Optional[str] = None
    business_meaning: Optional[BusinessMeaning] = None
    sensitivity_marking: Optional[SensitivityMarking] = None

    # Custom fields
    custom_fields: Dict[str, Any] = Field(default_factory=dict, description="User-defined custom fields")

    # Categorization and tagging
    tags: Set[str] = Field(default_factory=set, description="User-defined tags")
    categories: List[str] = Field(default_factory=list, description="Hierarchical categories")
    keywords: List[str] = Field(default_factory=list, description="Search keywords")

    # Quality and validation
    user_quality_rating: Optional[int] = None
    validation_notes: Optional[str] = None
    improvement_suggestions: List[str] = Field(default_factory=list, description="User improvement suggestions")

    # Relationships
    related_elements: List[str] = Field(default_factory=list, description="Related element IDs")
    parent_elements: List[str] = Field(default_factory=list, description="Parent element IDs")
    child_elements: List[str] = Field(default_factory=list, description="Child element IDs")

    # Metadata management
    status: MetadataStatus = Field(default=MetadataStatus.DRAFT)
    version: str = Field(default="1.0", description="Metadata version")
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    review_date: Optional[datetime] = None

    # Lineage
    lineage: List[MetadataLineage] = Field(default_factory=list, description="Enhancement history")

    @validator('user_quality_rating')
    def validate_quality_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Quality rating must be between 1 and 5")
        return v


class MetadataEnhancementRequest(BaseModel):
    """Request for enhancing metadata."""

    element_id: str = Field(..., description="Element to enhance")
    element_type: MetadataType = Field(..., description="Type of element")
    enhancements: Dict[str, Any] = Field(..., description="Enhancement data")
    user_id: Optional[str] = Field(None, description="User making the enhancement")
    notes: Optional[str] = Field(None, description="Enhancement notes")


class MetadataEnhancementResult(BaseModel):
    """Result of metadata enhancement operation."""

    success: bool = Field(default=True)
    element_id: str = Field(..., description="Enhanced element ID")
    enhanced_metadata: Optional[UserEnhancedMetadata] = Field(None)
    validation_results: List[str] = Field(default_factory=list, description="Validation messages")
    warnings: List[str] = Field(default_factory=list, description="Enhancement warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class MetadataTemplate(BaseModel):
    """Template for consistent metadata enhancement."""

    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    domain: Optional[str] = Field(None, description="Business domain")
    element_type: MetadataType = Field(..., description="Applicable element type")

    # Template fields
    required_fields: List[str] = Field(default_factory=list, description="Required enhancement fields")
    recommended_fields: List[str] = Field(default_factory=list, description="Recommended fields")
    custom_field_definitions: List[CustomMetadataField] = Field(default_factory=list)

    # Default values
    default_tags: Set[str] = Field(default_factory=set)
    default_categories: List[str] = Field(default_factory=list)
    default_sensitivity: Optional[DataPrivacyLevel] = Field(None)

    # Validation rules
    validation_rules: List[str] = Field(default_factory=list)
    business_rules: List[str] = Field(default_factory=list)

    # Template metadata
    created_by: Optional[str] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0")
    active: bool = Field(default=True)


class MetadataEnhancementService(MetadataInterface):
    """Service for managing user-enhanced metadata."""

    def __init__(self, context: Optional[MetadataContext] = None):
        super().__init__(context)
        self.templates: Dict[str, MetadataTemplate] = {}
        self.custom_fields: Dict[str, CustomMetadataField] = {}
        self.enhanced_metadata: Dict[str, UserEnhancedMetadata] = {}

    async def enhance_metadata(self, request: MetadataEnhancementRequest) -> MetadataEnhancementResult:
        """
        Enhance metadata with user-provided information.

        Args:
            request: Enhancement request with user data

        Returns:
            MetadataEnhancementResult with enhanced metadata
        """
        try:
            # Get existing enhanced metadata or create new
            enhanced = self.enhanced_metadata.get(request.element_id)
            if enhanced is None:
                enhanced = UserEnhancedMetadata(
                    element_id=request.element_id,
                    element_type=request.element_type,
                    created_by=request.user_id
                )

            # Apply enhancements
            enhanced = await self._apply_enhancements(enhanced, request.enhancements, request.user_id)

            # Validate enhancements
            validation_results = await self._validate_enhancements(enhanced)

            # Apply templates if specified
            if 'template_id' in request.enhancements:
                template_id = request.enhancements['template_id']
                if template_id in self.templates:
                    enhanced = await self._apply_template(enhanced, self.templates[template_id])

            # Update metadata
            enhanced.updated_by = request.user_id
            enhanced.updated_at = datetime.utcnow()

            # Add lineage
            lineage = MetadataLineage(
                source_id=request.element_id,
                operation='user_enhancement',
                created_by=request.user_id,
                parent_lineage_id=None,
                metadata={
                    'enhancement_fields': list(request.enhancements.keys()),
                    'notes': request.notes
                }
            )
            enhanced.lineage.append(lineage)

            # Store enhanced metadata
            self.enhanced_metadata[request.element_id] = enhanced

            # Generate suggestions
            suggestions = await self._generate_enhancement_suggestions(enhanced)

            return MetadataEnhancementResult(
                success=True,
                element_id=request.element_id,
                enhanced_metadata=enhanced,
                validation_results=validation_results,
                suggestions=suggestions
            )

        except Exception as e:
            return MetadataEnhancementResult(
                success=False,
                element_id=request.element_id,
                enhanced_metadata=None,
                validation_results=[f"Enhancement failed: {str(e)}"]
            )

    async def _apply_enhancements(self, metadata: UserEnhancedMetadata, enhancements: Dict[str, Any], user_id: Optional[str]) -> UserEnhancedMetadata:
        """Apply enhancement data to metadata."""

        # Basic fields
        if 'display_name' in enhancements:
            metadata.display_name = enhancements['display_name']

        if 'description' in enhancements:
            metadata.description = enhancements['description']

        if 'tags' in enhancements:
            metadata.tags.update(enhancements['tags'])

        if 'categories' in enhancements:
            metadata.categories = enhancements['categories']

        if 'keywords' in enhancements:
            metadata.keywords = enhancements['keywords']

        # Business meaning
        if 'business_meaning' in enhancements:
            bm_data = enhancements['business_meaning']
            metadata.business_meaning = BusinessMeaning(**bm_data)

        # Sensitivity marking
        if 'sensitivity_marking' in enhancements:
            sm_data = enhancements['sensitivity_marking']
            metadata.sensitivity_marking = SensitivityMarking(**sm_data)

        # Custom fields
        if 'custom_fields' in enhancements:
            metadata.custom_fields.update(enhancements['custom_fields'])

        # Quality rating
        if 'user_quality_rating' in enhancements:
            metadata.user_quality_rating = enhancements['user_quality_rating']

        # Relationships
        if 'related_elements' in enhancements:
            metadata.related_elements = enhancements['related_elements']

        if 'parent_elements' in enhancements:
            metadata.parent_elements = enhancements['parent_elements']

        if 'child_elements' in enhancements:
            metadata.child_elements = enhancements['child_elements']

        return metadata

    async def _validate_enhancements(self, metadata: UserEnhancedMetadata) -> List[str]:
        """Validate enhanced metadata."""
        validation_results = []

        # Check required fields based on templates
        if metadata.element_type == MetadataType.COLUMN:
            if not metadata.display_name:
                validation_results.append("Display name is recommended for column metadata")

        # Validate business meaning consistency
        if metadata.business_meaning and metadata.description:
            # Check if description aligns with business meaning
            if len(metadata.description) < 10:
                validation_results.append("Description should provide more detail about business meaning")

        # Validate sensitivity marking
        if metadata.sensitivity_marking:
            if (metadata.sensitivity_marking.privacy_level in [DataPrivacyLevel.CONFIDENTIAL, DataPrivacyLevel.RESTRICTED]
                and not metadata.sensitivity_marking.access_restrictions):
                validation_results.append("Access restrictions should be specified for confidential/restricted data")

        # Validate custom fields
        for field_name, field_value in metadata.custom_fields.items():
            if field_name in self.custom_fields:
                field_def = self.custom_fields[field_name]
                if field_def.required and field_value is None:
                    validation_results.append(f"Required custom field '{field_name}' is missing")

        return validation_results

    async def _apply_template(self, metadata: UserEnhancedMetadata, template: MetadataTemplate) -> UserEnhancedMetadata:
        """Apply template defaults to metadata."""

        # Apply default tags
        metadata.tags.update(template.default_tags)

        # Apply default categories
        if not metadata.categories and template.default_categories:
            metadata.categories = template.default_categories.copy()

        # Apply default sensitivity
        if not metadata.sensitivity_marking and template.default_sensitivity:
            metadata.sensitivity_marking = SensitivityMarking(
                privacy_level=template.default_sensitivity,
                retention_policy=None,
                anonymization_notes=None,
                legal_basis=None
            )

        return metadata

    async def _generate_enhancement_suggestions(self, metadata: UserEnhancedMetadata) -> List[str]:
        """Generate suggestions for further enhancement."""
        suggestions = []

        # Suggest missing critical information
        if not metadata.description:
            suggestions.append("Consider adding a detailed description explaining the business purpose")

        if not metadata.business_meaning:
            suggestions.append("Add business meaning to help users understand the business context")

        if not metadata.tags:
            suggestions.append("Add tags to improve discoverability and organization")

        # Suggest quality improvements
        if metadata.user_quality_rating and metadata.user_quality_rating < 4:
            suggestions.append("Consider adding improvement suggestions to address quality concerns")

        # Suggest relationship mapping
        if not metadata.related_elements and metadata.element_type == MetadataType.COLUMN:
            suggestions.append("Consider mapping relationships to other related data elements")

        # Suggest privacy classification
        if not metadata.sensitivity_marking:
            suggestions.append("Add privacy classification to ensure proper data handling")

        return suggestions

    async def create_template(self, template: MetadataTemplate) -> str:
        """Create a new metadata enhancement template."""
        self.templates[template.template_id] = template
        return template.template_id

    async def add_custom_field(self, field: CustomMetadataField) -> str:
        """Add a new custom metadata field definition."""
        self.custom_fields[field.field_id] = field
        return field.field_id

    async def get_enhanced_metadata(self, element_id: str) -> Optional[UserEnhancedMetadata]:
        """Get enhanced metadata for an element."""
        return self.enhanced_metadata.get(element_id)

    async def search_enhanced_metadata(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[UserEnhancedMetadata]:
        """Search enhanced metadata."""
        results = []
        query_lower = query.lower()

        for metadata in self.enhanced_metadata.values():
            # Search in display name, description, tags, keywords
            searchable_text = " ".join([
                metadata.display_name or "",
                metadata.description or "",
                " ".join(metadata.tags),
                " ".join(metadata.keywords)
            ]).lower()

            if query_lower in searchable_text:
                # Apply filters if provided
                if filters:
                    if self._matches_filters(metadata, filters):
                        results.append(metadata)
                else:
                    results.append(metadata)

        return results

    def _matches_filters(self, metadata: UserEnhancedMetadata, filters: Dict[str, Any]) -> bool:
        """Check if metadata matches the provided filters."""

        if 'element_type' in filters and metadata.element_type != filters['element_type']:
            return False

        if 'privacy_level' in filters:
            if not metadata.sensitivity_marking or metadata.sensitivity_marking.privacy_level != filters['privacy_level']:
                return False

        if 'tags' in filters:
            required_tags = set(filters['tags'])
            if not required_tags.issubset(metadata.tags):
                return False

        if 'domain' in filters:
            if not metadata.business_meaning or metadata.business_meaning.domain_context != filters['domain']:
                return False

        return True

    async def extract_metadata(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Extract enhanced metadata from data source."""
        # This would typically interact with the automatic extractor
        # and then apply user enhancements
        return {}

    async def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate enhanced metadata structure."""
        try:
            # Validate that it can be parsed as UserEnhancedMetadata
            UserEnhancedMetadata(**metadata)
            return True
        except Exception:
            return False
