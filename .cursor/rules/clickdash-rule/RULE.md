---
alwaysApply: true
---

# Cursor Project Rules — ClickDash (AI Data → Dashboard)

## Project Purpose (Read This First)

ClickDash is an **AI-powered data-to-dashboard system**.

**Primary goal:**

> A user uploads structured data (Excel / CSV / SQL / API) and automatically receives a **correct, validated, production-ready dashboard**.

This is **NOT** a chatbot.
This is **NOT** free-form analytics.
This is a **deterministic analytics system with AI-assisted planning**.

---

## Core Philosophy (Non-Negotiable)

1. **LLMs plan, systems execute**

   - LLMs may suggest charts, aggregations, and insights
   - LLMs must NEVER calculate numbers or act as ground truth

2. **Truth is deterministic**

   - All metrics, aggregations, and validations are computed in backend code (SQL / Pandas)

3. **Everything must be testable**

   - Every AI output must be validated
   - Manual eyeballing is unacceptable

4. **AI is replaceable**

   - The system must still work with rule-based logic
   - LLMs are an enhancement, not a dependency

---

## What Cursor Should Optimize For

When generating or modifying code, Cursor should prioritize:

- ✅ Correctness over creativity
- ✅ Deterministic behavior
- ✅ Explicit validation rules
- ✅ JSON contracts between layers
- ✅ Benchmarkability

Avoid:

- ❌ Hidden logic
- ❌ Implicit assumptions
- ❌ LLM-based computation
- ❌ UI-first decisions

---

## Supported Data Flow (Strict)

User Data Source
↓
Ingestion Layer
↓
Normalization & Canonicalization
↓
Schema & Metadata Extraction
↓
Semantic Rules + RAG
↓
LLM Analytics Planner (JSON only)
↓
Validation & Execution Engine
↓
Dashboard Specification
↓
Dashboard Renderer

Cursor MUST respect this order.
No layer may be skipped.

---

## LLM Usage Rules

Cursor should ensure:

- LLM input includes:

  - schema metadata
  - sample rows
  - explicit chart rules
  - output JSON schema

- LLM output MUST:

  - be valid JSON
  - contain NO computed values
  - contain NO SQL execution
  - contain NO business logic assumptions

Example (Allowed):

```json
{ "type": "line", "x": "date", "y": "sum(revenue)" }

Example (Forbidden):

{ "growth": "18%" }

---

## Validation Rules (Mandatory)

Every AI-generated plan MUST be validated against:

* Column existence
* Data type compatibility
* Chart-type rules
* Aggregation rules
* Numeric recomputation

Invalid plans must:

* be rejected OR
* be auto-corrected using rules

---

## Benchmarking Requirements

Cursor must preserve:

* Golden datasets
* Expected output JSONs
* Automated scoring logic

Every major change should:

* run benchmark tests
* output an accuracy score

---

## Frontend Rules

* Frontend renders only
* No AI logic in UI
* No metric computation in UI
* Dashboard is driven by a JSON spec

---

## Naming Conventions

Use clear, explicit names:

* SchemaExtractor
* ChartRuleEngine
* AnalyticsPlanner
* PlanValidator
* MetricExecutor
* DashboardSpec

Avoid vague names like:

* Analyzer
* SmartEngine
* MagicService

---

## What Success Looks Like

A successful implementation:

* Produces correct dashboards from Excel
* Has measurable accuracy (>80%)
* Rejects hallucinated insights
* Can explain every chart deterministically

---

## Final Instruction to Cursor

> If a design choice makes the system less testable, less deterministic, or less explainable — DO NOT implement it.

Accuracy > Speed
Correctness > Cleverness
Systems > Prompts

---

This document defines the ground truth intent of the ClickDash project.
Cursor should treat it as a system-level contract.
```
