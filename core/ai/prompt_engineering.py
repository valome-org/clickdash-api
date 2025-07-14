"""
Context-Aware Prompt Engineering System.

This module provides rich context for better AI analysis including:
- Metadata-enriched prompt generation
- Business context integration
- User preference incorporation
- Industry-specific prompt templates
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import logging

from .base import AnalysisContext, RecommendationType

logger = logging.getLogger(__name__)


class PromptType(str, Enum):
    """Types of prompts for different analysis tasks."""
    CHART_RECOMMENDATION = "chart_recommendation"
    LAYOUT_ANALYSIS = "layout_analysis"
    COLOR_SELECTION = "color_selection"
    DATA_INSIGHT = "data_insight"
    VISUALIZATION_ENHANCEMENT = "visualization_enhancement"
    DASHBOARD_STRUCTURE = "dashboard_structure"


class IndustryDomain(str, Enum):
    """Industry domains for specialized prompts."""
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    EDUCATION = "education"
    TECHNOLOGY = "technology"
    MARKETING = "marketing"
    GENERAL = "general"


class PromptTemplate(BaseModel):
    """Template for generating context-aware prompts."""

    template_id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Human-readable template name")
    prompt_type: PromptType = Field(..., description="Type of analysis prompt")
    industry: IndustryDomain = Field(default=IndustryDomain.GENERAL)

    # Template content
    base_template: str = Field(..., description="Base prompt template with placeholders")
    context_sections: List[str] = Field(default_factory=list, description="Context sections to include")
    required_variables: List[str] = Field(default_factory=list, description="Required template variables")
    optional_variables: List[str] = Field(default_factory=list, description="Optional template variables")

    # Prompt configuration
    max_tokens: int = Field(default=4000, description="Maximum prompt tokens")
    temperature: float = Field(default=0.7, description="LLM temperature setting")
    system_message: Optional[str] = Field(None, description="System message for the prompt")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0")
    tags: List[str] = Field(default_factory=list)


class PromptValidationResult(BaseModel):
    """Result of prompt validation."""

    is_valid: bool = Field(..., description="Whether prompt is valid")
    token_count: int = Field(..., description="Estimated token count")
    issues: List[str] = Field(default_factory=list, description="Validation issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    completeness_score: float = Field(..., description="Context completeness score")


class ContextAwarePromptBuilder:
    """Builds context-aware prompts for AI analysis."""

    def __init__(self):
        self.template_registry = {}
        self.context_extractors = {
            'data_context': self._extract_data_context,
            'business_context': self._extract_business_context,
            'user_context': self._extract_user_context,
            'metadata_context': self._extract_metadata_context,
            'technical_context': self._extract_technical_context
        }
        self._load_default_templates()

    async def build_prompt(
        self,
        recommendation_type: RecommendationType,
        context: AnalysisContext,
        data: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Build a context-aware prompt for AI analysis.

        Args:
            recommendation_type: Type of recommendation needed
            context: Analysis context
            data: Data to analyze
            **kwargs: Additional prompt customization options

        Returns:
            Complete prompt string with rich context
        """
        try:
            # Select appropriate template
            template = await self._select_template(recommendation_type, context)

            # Extract context information
            context_data = await self._extract_all_context(context, data)

            # Build prompt sections
            prompt_sections = await self._build_prompt_sections(template, context_data, **kwargs)

            # Assemble final prompt
            final_prompt = await self._assemble_prompt(template, prompt_sections)

            # Validate and optimize prompt
            validation = await self.validate_prompt(final_prompt, template)
            if not validation.is_valid:
                logger.warning(f"Prompt validation issues: {validation.issues}")
                final_prompt = await self._optimize_prompt(final_prompt, validation)

            logger.info(f"Built prompt for {recommendation_type.value}: {validation.token_count} tokens")
            return final_prompt

        except Exception as e:
            logger.error(f"Prompt building failed: {str(e)}")
            return await self._build_fallback_prompt(recommendation_type, data)

    async def _select_template(self, rec_type: RecommendationType, context: AnalysisContext) -> PromptTemplate:
        """Select the best template for the analysis type and context."""

        # Map recommendation types to prompt types
        type_mapping = {
            RecommendationType.CHART_TYPE: PromptType.CHART_RECOMMENDATION,
            RecommendationType.LAYOUT_DESIGN: PromptType.LAYOUT_ANALYSIS,
            RecommendationType.COLOR_SCHEME: PromptType.COLOR_SELECTION,
            RecommendationType.INSIGHT_GENERATION: PromptType.DATA_INSIGHT,
            RecommendationType.VISUALIZATION_ENHANCEMENT: PromptType.VISUALIZATION_ENHANCEMENT,
            RecommendationType.DASHBOARD_STRUCTURE: PromptType.DASHBOARD_STRUCTURE
        }

        prompt_type = type_mapping.get(rec_type, PromptType.CHART_RECOMMENDATION)

        # Determine industry
        industry = IndustryDomain.GENERAL
        if context.business_domain:
            industry_mapping = {
                'finance': IndustryDomain.FINANCE,
                'healthcare': IndustryDomain.HEALTHCARE,
                'retail': IndustryDomain.RETAIL,
                'manufacturing': IndustryDomain.MANUFACTURING,
                'education': IndustryDomain.EDUCATION,
                'technology': IndustryDomain.TECHNOLOGY,
                'marketing': IndustryDomain.MARKETING
            }
            industry = industry_mapping.get(context.business_domain.lower(), IndustryDomain.GENERAL)

        # Look for specific template
        template_key = f"{prompt_type.value}_{industry.value}"
        if template_key in self.template_registry:
            return self.template_registry[template_key]

        # Fallback to general template
        general_key = f"{prompt_type.value}_general"
        return self.template_registry.get(general_key, self._get_default_template(prompt_type))

    async def _extract_all_context(self, context: AnalysisContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all relevant context information."""
        context_data = {}

        for context_type, extractor in self.context_extractors.items():
            try:
                context_data[context_type] = await extractor(context, data)
            except Exception as e:
                logger.warning(f"Failed to extract {context_type}: {str(e)}")
                context_data[context_type] = {}

        return context_data

    async def _extract_data_context(self, context: AnalysisContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data-specific context."""
        return {
            "column_count": context.column_count,
            "row_count": context.row_count,
            "data_types": context.data_types,
            "data_sample": self._get_data_sample(data),
            "data_summary": self._generate_data_summary(context, data)
        }

    async def _extract_business_context(self, context: AnalysisContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract business-specific context."""
        return {
            "domain": context.business_domain or "general",
            "use_case": context.use_case or "data analysis",
            "target_audience": context.target_audience or "general users",
            "business_objectives": self._infer_business_objectives(context)
        }

    async def _extract_user_context(self, context: AnalysisContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user preference context."""
        return {
            "preferences": context.user_preferences,
            "previous_choices": context.previous_choices,
            "experience_level": self._infer_experience_level(context),
            "preferred_complexity": self._infer_complexity_preference(context)
        }

    async def _extract_metadata_context(self, context: AnalysisContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata quality context."""
        return {
            "metadata_quality": context.metadata_quality,
            "completeness_score": context.completeness_score,
            "data_reliability": self._assess_data_reliability(context),
            "quality_issues": self._identify_quality_issues(context)
        }

    async def _extract_technical_context(self, context: AnalysisContext, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract technical constraint context."""
        return {
            "platform_constraints": context.platform_constraints,
            "performance_requirements": context.performance_requirements,
            "processing_time_limit": context.max_processing_time,
            "technical_limitations": self._identify_technical_limitations(context)
        }

    async def _build_prompt_sections(
        self,
        template: PromptTemplate,
        context_data: Dict[str, Any],
        **kwargs
    ) -> Dict[str, str]:
        """Build individual sections of the prompt."""
        sections = {}

        for section in template.context_sections:
            if section == "data_overview":
                sections[section] = await self._build_data_overview_section(context_data['data_context'])
            elif section == "business_context":
                sections[section] = await self._build_business_context_section(context_data['business_context'])
            elif section == "user_preferences":
                sections[section] = await self._build_user_preferences_section(context_data['user_context'])
            elif section == "quality_assessment":
                sections[section] = await self._build_quality_assessment_section(context_data['metadata_context'])
            elif section == "constraints":
                sections[section] = await self._build_constraints_section(context_data['technical_context'])
            elif section == "examples":
                sections[section] = await self._build_examples_section(template, context_data)
            else:
                sections[section] = f"<!-- {section} section -->"

        return sections

    async def _build_data_overview_section(self, data_context: Dict[str, Any]) -> str:
        """Build data overview section."""
        lines = [
            "## Data Overview",
            f"- Dataset contains {data_context.get('row_count', 0)} rows and {data_context.get('column_count', 0)} columns",
            f"- Data types: {', '.join(f'{k}: {v}' for k, v in data_context.get('data_types', {}).items())}",
        ]

        if data_context.get('data_sample'):
            lines.append(f"- Sample data: {data_context['data_sample']}")

        if data_context.get('data_summary'):
            lines.append(f"- Summary: {data_context['data_summary']}")

        return "\n".join(lines)

    async def _build_business_context_section(self, business_context: Dict[str, Any]) -> str:
        """Build business context section."""
        lines = [
            "## Business Context",
            f"- Domain: {business_context.get('domain', 'general')}",
            f"- Use Case: {business_context.get('use_case', 'data analysis')}",
            f"- Target Audience: {business_context.get('target_audience', 'general users')}"
        ]

        objectives = business_context.get('business_objectives', [])
        if objectives:
            lines.append(f"- Business Objectives: {', '.join(objectives)}")

        return "\n".join(lines)

    async def _build_user_preferences_section(self, user_context: Dict[str, Any]) -> str:
        """Build user preferences section."""
        lines = ["## User Preferences"]

        preferences = user_context.get('preferences', {})
        if preferences:
            for key, value in preferences.items():
                lines.append(f"- {key}: {value}")

        experience = user_context.get('experience_level', 'intermediate')
        lines.append(f"- Experience Level: {experience}")

        complexity = user_context.get('preferred_complexity', 'moderate')
        lines.append(f"- Preferred Complexity: {complexity}")

        return "\n".join(lines)

    async def _build_quality_assessment_section(self, metadata_context: Dict[str, Any]) -> str:
        """Build quality assessment section."""
        lines = [
            "## Data Quality Assessment",
            f"- Metadata Quality: {metadata_context.get('metadata_quality', 0.0):.2f}",
            f"- Completeness Score: {metadata_context.get('completeness_score', 0.0):.2f}",
            f"- Data Reliability: {metadata_context.get('data_reliability', 'unknown')}"
        ]

        issues = metadata_context.get('quality_issues', [])
        if issues:
            lines.append(f"- Quality Issues: {', '.join(issues)}")

        return "\n".join(lines)

    async def _build_constraints_section(self, technical_context: Dict[str, Any]) -> str:
        """Build constraints section."""
        lines = ["## Technical Constraints"]

        constraints = technical_context.get('platform_constraints', {})
        if constraints:
            for key, value in constraints.items():
                lines.append(f"- {key}: {value}")

        time_limit = technical_context.get('processing_time_limit', 30)
        lines.append(f"- Processing Time Limit: {time_limit} seconds")

        limitations = technical_context.get('technical_limitations', [])
        if limitations:
            lines.append(f"- Limitations: {', '.join(limitations)}")

        return "\n".join(lines)

    async def _build_examples_section(self, template: PromptTemplate, context_data: Dict[str, Any]) -> str:
        """Build examples section based on industry and type."""
        domain = context_data.get('business_context', {}).get('domain', 'general')

        examples = {
            'finance': [
                "For financial data, consider metrics like ROI, profit margins, and trend analysis",
                "Use clear, professional visualizations suitable for executive dashboards"
            ],
            'healthcare': [
                "Focus on patient outcomes, treatment effectiveness, and regulatory compliance",
                "Ensure data privacy and accessibility standards are met"
            ],
            'retail': [
                "Emphasize sales performance, customer behavior, and inventory metrics",
                "Use engaging visualizations that tell the customer story"
            ]
        }

        domain_examples = examples.get(domain, [
            "Focus on clear, informative visualizations",
            "Ensure accessibility and user experience best practices"
        ])

        lines = ["## Examples and Best Practices"] + [f"- {example}" for example in domain_examples]
        return "\n".join(lines)

    async def _assemble_prompt(self, template: PromptTemplate, sections: Dict[str, str]) -> str:
        """Assemble the final prompt from template and sections."""
        # Start with system message if provided
        prompt_parts = []

        if template.system_message:
            prompt_parts.append(f"System: {template.system_message}")

        # Build the main prompt
        main_prompt = template.base_template

        # Replace section placeholders
        for section_name, section_content in sections.items():
            placeholder = f"{{{section_name}}}"
            main_prompt = main_prompt.replace(placeholder, section_content)

        prompt_parts.append(main_prompt)

        # Add instructions
        prompt_parts.append("\nPlease provide your analysis in JSON format with the following structure:")
        prompt_parts.append('{"recommendation": {...}, "reasoning": "...", "confidence": 0.0-1.0}')

        return "\n".join(prompt_parts)

    async def validate_prompt(self, prompt: str, template: PromptTemplate) -> PromptValidationResult:
        """Validate the generated prompt."""
        issues = []
        suggestions = []

        # Check token count (rough estimate)
        token_count = len(prompt.split()) * 1.3  # Rough approximation

        if token_count > template.max_tokens:
            issues.append(f"Prompt exceeds max tokens: {token_count} > {template.max_tokens}")
            suggestions.append("Consider reducing context sections or using summarization")

        # Check for required variables
        for var in template.required_variables:
            if f"{{{var}}}" in prompt:
                issues.append(f"Required variable '{var}' not replaced")

        # Calculate completeness score
        total_sections = len(template.context_sections)
        included_sections = sum(1 for section in template.context_sections if section in prompt)
        completeness_score = included_sections / total_sections if total_sections > 0 else 1.0

        return PromptValidationResult(
            is_valid=len(issues) == 0,
            token_count=int(token_count),
            issues=issues,
            suggestions=suggestions,
            completeness_score=completeness_score
        )

    async def _optimize_prompt(self, prompt: str, validation: PromptValidationResult) -> str:
        """Optimize prompt based on validation results."""
        if validation.token_count > 4000:
            # Truncate sections if too long
            sections = prompt.split("## ")
            if len(sections) > 3:
                # Keep most important sections
                optimized_sections = sections[:3]
                prompt = "## ".join(optimized_sections)

        return prompt

    async def _build_fallback_prompt(self, rec_type: RecommendationType, data: Dict[str, Any]) -> str:
        """Build a simple fallback prompt when context building fails."""
        return f"""
        Please analyze the following data and provide a {rec_type.value} recommendation:

        Data: {json.dumps(data, indent=2)}

        Provide your recommendation in JSON format with reasoning and confidence score.
        """

    def _get_data_sample(self, data: Dict[str, Any]) -> str:
        """Get a representative sample of the data."""
        if not data:
            return "No data available"

        # Return first few items as sample
        sample = dict(list(data.items())[:3])
        return json.dumps(sample, indent=2)

    def _generate_data_summary(self, context: AnalysisContext, data: Dict[str, Any]) -> str:
        """Generate a summary of the data characteristics."""
        summary_parts = []

        if context.column_count > 0:
            summary_parts.append(f"Dataset with {context.column_count} columns")

        if context.row_count > 0:
            summary_parts.append(f"containing {context.row_count} records")

        if context.data_types:
            type_counts = {}
            for dtype in context.data_types.values():
                type_counts[dtype] = type_counts.get(dtype, 0) + 1

            type_summary = ", ".join(f"{count} {dtype}" for dtype, count in type_counts.items())
            summary_parts.append(f"with {type_summary} columns")

        return ". ".join(summary_parts) if summary_parts else "Limited data information available"

    def _infer_business_objectives(self, context: AnalysisContext) -> List[str]:
        """Infer business objectives from context."""
        objectives = []

        domain_objectives = {
            'finance': ['Financial performance analysis', 'Risk assessment', 'Investment insights'],
            'healthcare': ['Patient outcome improvement', 'Treatment effectiveness', 'Cost optimization'],
            'retail': ['Sales optimization', 'Customer satisfaction', 'Inventory management'],
            'marketing': ['Campaign effectiveness', 'Customer acquisition', 'Brand awareness']
        }

        if context.business_domain:
            objectives.extend(domain_objectives.get(context.business_domain.lower(), []))

        if context.use_case:
            objectives.append(f"Support {context.use_case}")

        return objectives or ['Data insights and visualization']

    def _infer_experience_level(self, context: AnalysisContext) -> str:
        """Infer user experience level from context."""
        preferences = context.user_preferences

        if 'experience_level' in preferences:
            return preferences['experience_level']

        # Infer from other preferences
        if preferences.get('simple_interface', False):
            return 'beginner'
        elif preferences.get('advanced_features', False):
            return 'advanced'
        else:
            return 'intermediate'

    def _infer_complexity_preference(self, context: AnalysisContext) -> str:
        """Infer complexity preference from context."""
        preferences = context.user_preferences

        if 'complexity' in preferences:
            return preferences['complexity']

        # Infer from other signals
        if context.target_audience == 'executives':
            return 'simple'
        elif context.target_audience == 'analysts':
            return 'complex'
        else:
            return 'moderate'

    def _assess_data_reliability(self, context: AnalysisContext) -> str:
        """Assess data reliability from metadata quality."""
        if context.metadata_quality >= 0.8:
            return 'high'
        elif context.metadata_quality >= 0.6:
            return 'moderate'
        elif context.metadata_quality >= 0.4:
            return 'low'
        else:
            return 'very_low'

    def _identify_quality_issues(self, context: AnalysisContext) -> List[str]:
        """Identify potential data quality issues."""
        issues = []

        if context.completeness_score < 0.8:
            issues.append('incomplete data')

        if context.metadata_quality < 0.6:
            issues.append('poor metadata quality')

        return issues

    def _identify_technical_limitations(self, context: AnalysisContext) -> List[str]:
        """Identify technical limitations from context."""
        limitations = []

        if context.max_processing_time < 10:
            limitations.append('strict time constraints')

        constraints = context.platform_constraints
        if constraints.get('memory_limited', False):
            limitations.append('memory constraints')

        if constraints.get('simple_visualizations_only', False):
            limitations.append('basic visualization support only')

        return limitations

    def _get_default_template(self, prompt_type: PromptType) -> PromptTemplate:
        """Get a default template for the given prompt type."""
        base_templates = {
            PromptType.CHART_RECOMMENDATION: """
                Given the following data and context, recommend the most appropriate chart type:

                {data_overview}
                {business_context}
                {user_preferences}

                Consider the data characteristics, business objectives, and user needs.
                """,
            PromptType.COLOR_SELECTION: """
                Based on the data and context provided, recommend an appropriate color scheme:

                {data_overview}
                {business_context}
                {constraints}

                Ensure accessibility and brand alignment.
                """
        }

        return PromptTemplate(
            template_id=f"default_{prompt_type.value}",
            name=f"Default {prompt_type.value} Template",
            prompt_type=prompt_type,
            base_template=base_templates.get(prompt_type, "Analyze the data and provide recommendations."),
            context_sections=["data_overview", "business_context", "user_preferences"],
            required_variables=[],
            system_message=None
        )

    def _load_default_templates(self):
        """Load default prompt templates."""
        # This would typically load from a database or config files
        for prompt_type in PromptType:
            for industry in IndustryDomain:
                template = self._create_industry_template(prompt_type, industry)
                key = f"{prompt_type.value}_{industry.value}"
                self.template_registry[key] = template

    def _create_industry_template(self, prompt_type: PromptType, industry: IndustryDomain) -> PromptTemplate:
        """Create an industry-specific template."""
        industry_context = {
            IndustryDomain.FINANCE: "Focus on financial KPIs, regulatory compliance, and risk assessment.",
            IndustryDomain.HEALTHCARE: "Prioritize patient privacy, clinical outcomes, and regulatory standards.",
            IndustryDomain.RETAIL: "Emphasize customer experience, sales metrics, and inventory insights."
        }

        base_template = f"""
        As an expert in {industry.value} data analysis, please analyze the provided data:

        {industry_context.get(industry, "Apply general best practices for data analysis.")}

        {{data_overview}}
        {{business_context}}
        {{user_preferences}}
        {{quality_assessment}}
        {{examples}}

        Provide specific recommendations suitable for {industry.value} industry needs.
        """

        return PromptTemplate(
            template_id=f"{prompt_type.value}_{industry.value}",
            name=f"{industry.value.title()} {prompt_type.value.replace('_', ' ').title()}",
            prompt_type=prompt_type,
            industry=industry,
            base_template=base_template,
            context_sections=["data_overview", "business_context", "user_preferences", "quality_assessment", "examples"],
            system_message=f"You are an expert data analyst specializing in {industry.value} industry visualizations."
        )


class IndustryPromptLibrary:
    """Library of industry-specific prompt templates and best practices."""

    def __init__(self):
        self.industry_guidelines = self._load_industry_guidelines()
        self.prompt_builder = ContextAwarePromptBuilder()

    def get_industry_prompts(self, industry: IndustryDomain) -> List[PromptTemplate]:
        """Get all available prompts for a specific industry."""
        return [
            template for template in self.prompt_builder.template_registry.values()
            if template.industry == industry
        ]

    def get_industry_guidelines(self, industry: IndustryDomain) -> Dict[str, Any]:
        """Get industry-specific guidelines and best practices."""
        return self.industry_guidelines.get(industry.value, {})

    def _load_industry_guidelines(self) -> Dict[str, Dict[str, Any]]:
        """Load industry-specific guidelines."""
        return {
            'finance': {
                'colors': ['professional blues', 'conservative greens', 'accent reds for alerts'],
                'chart_types': ['line charts for trends', 'bar charts for comparisons', 'tables for precision'],
                'metrics': ['ROI', 'profit margins', 'growth rates', 'risk indicators'],
                'compliance': ['SOX compliance', 'audit trails', 'data retention policies']
            },
            'healthcare': {
                'colors': ['calming blues', 'clean whites', 'safety oranges for warnings'],
                'chart_types': ['trend lines for patient progress', 'scatter plots for correlations'],
                'metrics': ['patient outcomes', 'treatment efficacy', 'cost per treatment'],
                'compliance': ['HIPAA compliance', 'patient privacy', 'medical accuracy']
            },
            'retail': {
                'colors': ['brand colors', 'seasonal palettes', 'high contrast for CTAs'],
                'chart_types': ['heat maps for geographic data', 'funnel charts for conversions'],
                'metrics': ['sales performance', 'customer lifetime value', 'inventory turnover'],
                'compliance': ['PCI compliance for payments', 'customer data protection']
            }
        }
