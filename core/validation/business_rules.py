"""
Business rule validation engine for complex data validation rules.

This module provides a flexible business rule validation system including:
- Rule definition and parsing
- Rule execution engine
- Rule conflict detection
- Industry-specific rule templates
- Performance optimization for rule execution
"""

import re
import ast
import operator
from typing import Any, Dict, List, Optional, Set, Callable, Union
from datetime import datetime, date
from enum import Enum
import pandas as pd
from pydantic import BaseModel, Field
import uuid

from .base import ValidatorInterface, ValidationResult, ValidationIssue, ValidationSeverity


class RuleOperator(str, Enum):
    """Supported operators for business rules."""
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX_MATCH = "regex_match"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"


class RuleCondition(BaseModel):
    """Individual condition within a business rule."""

    field: str = Field(..., description="Field name to validate")
    operator: RuleOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")
    case_sensitive: bool = Field(default=True, description="Whether string comparisons are case sensitive")


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""
    AND = "and"
    OR = "or"
    NOT = "not"


class BusinessRule(BaseModel):
    """Definition of a business validation rule."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(..., description="Detailed description of the rule")
    conditions: List[RuleCondition] = Field(..., description="List of conditions")
    logical_operator: LogicalOperator = Field(default=LogicalOperator.AND, description="How to combine conditions")
    severity: ValidationSeverity = Field(default=ValidationSeverity.ERROR, description="Severity of rule violations")
    category: str = Field(default="general", description="Rule category for organization")
    tags: Set[str] = Field(default_factory=set, description="Tags for rule classification")
    active: bool = Field(default=True, description="Whether rule is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Rule creation timestamp")
    created_by: Optional[str] = Field(None, description="Rule creator")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix for violations")
    custom_message: Optional[str] = Field(None, description="Custom violation message")
    priority: int = Field(default=100, description="Rule execution priority (lower = higher priority)")


class RuleValidationResult(ValidationResult):
    """Results of business rule validation."""

    rules_evaluated: int = Field(default=0, description="Number of rules evaluated")
    rules_passed: int = Field(default=0, description="Number of rules that passed")
    rules_failed: int = Field(default=0, description="Number of rules that failed")
    rule_performance: Dict[str, float] = Field(default_factory=dict, description="Execution time per rule")


class RuleConflict(BaseModel):
    """Represents a conflict between business rules."""

    rule1_id: str = Field(..., description="First conflicting rule ID")
    rule2_id: str = Field(..., description="Second conflicting rule ID")
    conflict_type: str = Field(..., description="Type of conflict")
    description: str = Field(..., description="Description of the conflict")
    severity: str = Field(..., description="Conflict severity")
    resolution_suggestion: Optional[str] = Field(None, description="Suggested resolution")


class IndustryTemplate(BaseModel):
    """Template of common rules for specific industries."""

    name: str = Field(..., description="Template name")
    industry: str = Field(..., description="Target industry")
    description: str = Field(..., description="Template description")
    rules: List[BusinessRule] = Field(..., description="List of rules in template")
    tags: Set[str] = Field(default_factory=set, description="Template tags")


class RuleExecutionContext(BaseModel):
    """Context for rule execution."""

    data_source: Optional[str] = Field(None, description="Data source identifier")
    business_context: Dict[str, Any] = Field(default_factory=dict, description="Business context variables")
    execution_mode: str = Field(default="strict", description="Execution mode (strict, lenient)")
    parallel_execution: bool = Field(default=True, description="Whether to execute rules in parallel")


class BusinessRuleEngine(ValidatorInterface):
    """Main business rule validation engine."""

    def __init__(self):
        self.rules: Dict[str, BusinessRule] = {}
        self.rule_groups: Dict[str, List[str]] = {}  # category -> rule_ids
        self.conflict_detector = RuleConflictDetector()

        # Operator mapping for evaluation
        self._operators = {
            RuleOperator.EQUALS: operator.eq,
            RuleOperator.NOT_EQUALS: operator.ne,
            RuleOperator.GREATER_THAN: operator.gt,
            RuleOperator.GREATER_THAN_OR_EQUAL: operator.ge,
            RuleOperator.LESS_THAN: operator.lt,
            RuleOperator.LESS_THAN_OR_EQUAL: operator.le,
        }

    def add_rule(self, rule: BusinessRule) -> None:
        """Add a business rule to the engine."""
        self.rules[rule.id] = rule

        # Add to category group
        if rule.category not in self.rule_groups:
            self.rule_groups[rule.category] = []
        self.rule_groups[rule.category].append(rule.id)

        # Check for conflicts with existing rules
        conflicts = self.conflict_detector.detect_conflicts(rule, list(self.rules.values()))
        if conflicts:
            # Log conflicts but don't prevent adding the rule
            print(f"Warning: Rule '{rule.name}' has {len(conflicts)} conflicts with existing rules")

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a business rule from the engine."""
        if rule_id not in self.rules:
            return False

        rule = self.rules[rule_id]
        del self.rules[rule_id]

        # Remove from category group
        if rule.category in self.rule_groups:
            if rule_id in self.rule_groups[rule.category]:
                self.rule_groups[rule.category].remove(rule_id)

        return True

    def get_rule(self, rule_id: str) -> Optional[BusinessRule]:
        """Get a business rule by ID."""
        return self.rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> List[BusinessRule]:
        """Get all rules in a specific category."""
        rule_ids = self.rule_groups.get(category, [])
        return [self.rules[rule_id] for rule_id in rule_ids if rule_id in self.rules]

    async def validate(self, data: pd.DataFrame, context: Optional[RuleExecutionContext] = None, **kwargs) -> RuleValidationResult:
        """
        Validate data against business rules.

        Args:
            data: DataFrame to validate
            context: Execution context for rules
            **kwargs: Additional validation parameters

        Returns:
            RuleValidationResult with validation outcome
        """
        start_time = datetime.utcnow()

        if context is None:
            context = RuleExecutionContext(data_source=None)

        result = RuleValidationResult(is_valid=True, execution_time_ms=0)

        # Get active rules sorted by priority
        active_rules = [rule for rule in self.rules.values() if rule.active]
        active_rules.sort(key=lambda r: r.priority)

        # Execute rules
        for rule in active_rules:
            rule_start = datetime.utcnow()

            try:
                violations = await self._evaluate_rule(rule, data, context)
                result.rules_evaluated += 1

                if violations:
                    result.rules_failed += 1
                    result.issues.extend(violations)
                    if any(v.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] for v in violations):
                        result.is_valid = False
                else:
                    result.rules_passed += 1

            except Exception as e:
                # Rule execution failed
                result.rules_failed += 1
                result.add_issue(ValidationIssue(
                    id=str(uuid.uuid4()),
                    severity=ValidationSeverity.ERROR,
                    message=f"Rule '{rule.name}' execution failed: {str(e)}",
                    field="",
                    row=None,
                    value=None,
                    suggested_fix="Check rule configuration and data compatibility",
                    metadata={"rule_id": rule.id, "exception": str(e)}
                ))

            # Track performance
            rule_end = datetime.utcnow()
            result.rule_performance[rule.id] = (rule_end - rule_start).total_seconds() * 1000

        # Calculate execution time
        end_time = datetime.utcnow()
        result.execution_time_ms = (end_time - start_time).total_seconds() * 1000

        return result

    async def _evaluate_rule(self, rule: BusinessRule, data: pd.DataFrame, context: RuleExecutionContext) -> List[ValidationIssue]:
        """Evaluate a single business rule against the data."""
        violations = []

        # Evaluate conditions for each row
        for index, row in data.iterrows():
            if await self._evaluate_conditions(rule.conditions, row, rule.logical_operator, context):
                continue  # Rule passed for this row

            # Rule failed - create violation
            violation_message = rule.custom_message or f"Business rule '{rule.name}' violation"

            violations.append(ValidationIssue(
                id=str(uuid.uuid4()),
                severity=rule.severity,
                message=violation_message,
                field="",
                row=None if not isinstance(index, (int, str)) else (int(index) if str(index).replace(".", "").replace("-", "").isdigit() else None),
                value=None,
                suggested_fix=rule.suggested_fix,
                metadata={
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "rule_category": rule.category
                }
            ))

        return violations

    async def _evaluate_conditions(self, conditions: List[RuleCondition], row: pd.Series,
                                 logical_op: LogicalOperator, context: RuleExecutionContext) -> bool:
        """Evaluate list of conditions against a single row."""
        if not conditions:
            return True

        results = []
        for condition in conditions:
            result = await self._evaluate_single_condition(condition, row, context)
            results.append(result)

        # Apply logical operator
        if logical_op == LogicalOperator.AND:
            return all(results)
        elif logical_op == LogicalOperator.OR:
            return any(results)
        elif logical_op == LogicalOperator.NOT:
            return not all(results)

        return False

    async def _evaluate_single_condition(self, condition: RuleCondition, row: pd.Series,
                                       context: RuleExecutionContext) -> bool:
        """Evaluate a single condition against a row."""
        field_value = row.get(condition.field)
        compare_value = condition.value

        # Handle null values
        if pd.isna(field_value):
            if condition.operator == RuleOperator.IS_NULL:
                return True
            elif condition.operator == RuleOperator.IS_NOT_NULL:
                return False
            else:
                return False  # Most operations fail on null values

        if condition.operator == RuleOperator.IS_NULL:
            return False
        elif condition.operator == RuleOperator.IS_NOT_NULL:
            return True

        # String operations
        if isinstance(field_value, str) and not condition.case_sensitive:
            field_value = field_value.lower()
            if isinstance(compare_value, str):
                compare_value = compare_value.lower()

        # Apply operator
        if condition.operator in self._operators:
            try:
                return self._operators[condition.operator](field_value, compare_value)
            except (TypeError, ValueError):
                return False

        elif condition.operator == RuleOperator.CONTAINS:
            return isinstance(field_value, str) and isinstance(compare_value, str) and compare_value in field_value

        elif condition.operator == RuleOperator.NOT_CONTAINS:
            return isinstance(field_value, str) and isinstance(compare_value, str) and compare_value not in field_value

        elif condition.operator == RuleOperator.STARTS_WITH:
            return isinstance(field_value, str) and isinstance(compare_value, str) and field_value.startswith(compare_value)

        elif condition.operator == RuleOperator.ENDS_WITH:
            return isinstance(field_value, str) and isinstance(compare_value, str) and field_value.endswith(compare_value)

        elif condition.operator == RuleOperator.REGEX_MATCH:
            if isinstance(field_value, str) and isinstance(compare_value, str):
                try:
                    return bool(re.match(compare_value, field_value))
                except re.error:
                    return False
            return False

        elif condition.operator == RuleOperator.IN:
            if isinstance(compare_value, (list, tuple, set)):
                return field_value in compare_value
            return False

        elif condition.operator == RuleOperator.NOT_IN:
            if isinstance(compare_value, (list, tuple, set)):
                return field_value not in compare_value
            return True

        elif condition.operator == RuleOperator.BETWEEN:
            if isinstance(compare_value, (list, tuple)) and len(compare_value) == 2:
                return compare_value[0] <= field_value <= compare_value[1]
            return False

        elif condition.operator == RuleOperator.NOT_BETWEEN:
            if isinstance(compare_value, (list, tuple)) and len(compare_value) == 2:
                return not (compare_value[0] <= field_value <= compare_value[1])
            return True

        return False

    def get_validator_info(self) -> Dict[str, Any]:
        """Get information about this validator."""
        return {
            "name": "BusinessRuleEngine",
            "version": "1.0.0",
            "description": "Validates data against configurable business rules",
            "supported_operators": [op.value for op in RuleOperator],
            "total_rules": len(self.rules),
            "active_rules": len([r for r in self.rules.values() if r.active]),
            "rule_categories": list(self.rule_groups.keys())
        }


class RuleConflictDetector:
    """Detects conflicts between business rules."""

    def detect_conflicts(self, new_rule: BusinessRule, existing_rules: List[BusinessRule]) -> List[RuleConflict]:
        """Detect conflicts between a new rule and existing rules."""
        conflicts = []

        for existing_rule in existing_rules:
            if existing_rule.id == new_rule.id:
                continue

            # Check for direct contradictions
            contradiction = self._check_contradiction(new_rule, existing_rule)
            if contradiction:
                conflicts.append(contradiction)

            # Check for overlapping fields with different constraints
            overlap = self._check_field_overlap(new_rule, existing_rule)
            if overlap:
                conflicts.append(overlap)

        return conflicts

    def _check_contradiction(self, rule1: BusinessRule, rule2: BusinessRule) -> Optional[RuleConflict]:
        """Check if two rules directly contradict each other."""
        # Get fields used by both rules
        fields1 = {condition.field for condition in rule1.conditions}
        fields2 = {condition.field for condition in rule2.conditions}

        common_fields = fields1.intersection(fields2)
        if not common_fields:
            return None

        # Look for contradictory conditions on the same field
        for field in common_fields:
            conditions1 = [c for c in rule1.conditions if c.field == field]
            conditions2 = [c for c in rule2.conditions if c.field == field]

            for c1 in conditions1:
                for c2 in conditions2:
                    if self._are_contradictory(c1, c2):
                        return RuleConflict(
                            rule1_id=rule1.id,
                            rule2_id=rule2.id,
                            conflict_type="contradiction",
                            description=f"Rules have contradictory conditions on field '{field}'",
                            severity="high",
                            resolution_suggestion="Review and reconcile the contradictory conditions"
                        )

        return None

    def _check_field_overlap(self, rule1: BusinessRule, rule2: BusinessRule) -> Optional[RuleConflict]:
        """Check if rules have overlapping field constraints that might conflict."""
        fields1 = {condition.field for condition in rule1.conditions}
        fields2 = {condition.field for condition in rule2.conditions}

        common_fields = fields1.intersection(fields2)
        if not common_fields:
            return None

        # Check for potentially conflicting severity levels
        if rule1.severity != rule2.severity and len(common_fields) > 0:
            return RuleConflict(
                rule1_id=rule1.id,
                rule2_id=rule2.id,
                conflict_type="severity_mismatch",
                description=f"Rules validate same fields but have different severity levels",
                severity="medium",
                resolution_suggestion="Consider standardizing severity levels for related rules"
            )

        return None

    def _are_contradictory(self, condition1: RuleCondition, condition2: RuleCondition) -> bool:
        """Check if two conditions are contradictory."""
        if condition1.field != condition2.field:
            return False

        # Simple contradiction detection
        contradictions = [
            (RuleOperator.EQUALS, RuleOperator.NOT_EQUALS),
            (RuleOperator.IS_NULL, RuleOperator.IS_NOT_NULL),
            (RuleOperator.CONTAINS, RuleOperator.NOT_CONTAINS),
        ]

        for op1, op2 in contradictions:
            if ((condition1.operator == op1 and condition2.operator == op2) or
                (condition1.operator == op2 and condition2.operator == op1)):
                # Check if they're testing the same value
                if condition1.value == condition2.value:
                    return True

        return False


class IndustryTemplates:
    """Provides industry-specific rule templates."""

    @staticmethod
    def get_financial_template() -> IndustryTemplate:
        """Get financial industry rule template."""
        rules = [
            BusinessRule(
                name="Positive Account Balance",
                description="Account balances should be positive",
                conditions=[
                    RuleCondition(field="balance", operator=RuleOperator.GREATER_THAN_OR_EQUAL, value=0)
                ],
                severity=ValidationSeverity.WARNING,
                category="financial",
                tags={"finance", "balance"},
                created_by=None,
                suggested_fix=None,
                custom_message=None
            ),
            BusinessRule(
                name="Valid Transaction Amount",
                description="Transaction amounts should be greater than zero",
                conditions=[
                    RuleCondition(field="amount", operator=RuleOperator.GREATER_THAN, value=0)
                ],
                severity=ValidationSeverity.ERROR,
                category="financial",
                tags={"finance", "transaction"},
                created_by=None,
                suggested_fix=None,
                custom_message=None
            ),
            BusinessRule(
                name="Currency Code Format",
                description="Currency codes should be 3 uppercase letters",
                conditions=[
                    RuleCondition(field="currency", operator=RuleOperator.REGEX_MATCH, value="^[A-Z]{3}$")
                ],
                severity=ValidationSeverity.ERROR,
                category="financial",
                tags={"finance", "currency"},
                created_by=None,
                suggested_fix=None,
                custom_message=None
            )
        ]

        return IndustryTemplate(
            name="Financial Services",
            industry="financial",
            description="Common validation rules for financial data",
            rules=rules,
            tags={"finance", "banking", "transactions"}
        )

    @staticmethod
    def get_healthcare_template() -> IndustryTemplate:
        """Get healthcare industry rule template."""
        rules = [
            BusinessRule(
                name="Valid Patient Age",
                description="Patient age should be reasonable (0-150 years)",
                conditions=[
                    RuleCondition(field="age", operator=RuleOperator.BETWEEN, value=[0, 150])
                ],
                severity=ValidationSeverity.ERROR,
                category="healthcare",
                tags={"healthcare", "patient", "age"},
                created_by=None,
                suggested_fix=None,
                custom_message=None

            ),
            BusinessRule(
                name="Valid Blood Pressure",
                description="Systolic pressure should be higher than diastolic",
                conditions=[
                    RuleCondition(field="systolic_bp", operator=RuleOperator.GREATER_THAN, value="diastolic_bp")
                ],
                severity=ValidationSeverity.WARNING,
                category="healthcare",
                tags={"healthcare", "vitals", "blood_pressure"},
                created_by=None,
                suggested_fix=None,
                custom_message=None
            )
        ]

        return IndustryTemplate(
            name="Healthcare",
            industry="healthcare",
            description="Common validation rules for healthcare data",
            rules=rules,
            tags={"healthcare", "medical", "patient"}
        )

    @staticmethod
    def get_retail_template() -> IndustryTemplate:
        """Get retail industry rule template."""
        rules = [
            BusinessRule(
                name="Positive Product Price",
                description="Product prices should be positive",
                conditions=[
                    RuleCondition(field="price", operator=RuleOperator.GREATER_THAN, value=0)
                ],
                severity=ValidationSeverity.ERROR,
                category="retail",
                tags={"retail", "pricing"},
                created_by=None,
                suggested_fix=None,
                custom_message=None
            ),
            BusinessRule(
                name="Valid SKU Format",
                description="SKU should follow standard format",
                conditions=[
                    RuleCondition(field="sku", operator=RuleOperator.REGEX_MATCH, value="^[A-Z0-9]{6,12}$")
                ],
                severity=ValidationSeverity.WARNING,
                category="retail",
                tags={"retail", "inventory", "sku"},
                created_by=None,
                suggested_fix=None,
                custom_message=None
            )
        ]

        return IndustryTemplate(
            name="Retail",
            industry="retail",
            description="Common validation rules for retail data",
            rules=rules,
            tags={"retail", "ecommerce", "inventory"}
        )
