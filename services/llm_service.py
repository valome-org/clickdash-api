import json
import os
from typing import Any, Dict, Optional

import google.generativeai as genai
import pandas as pd
from config.settings import GEMINI_MODEL, LLM_MODEL, OPENAI_MODEL
from openai import OpenAI
from utils.serialization import CustomJSONEncoder, make_json_serializable


class LLMService:
    """Service for handling LLM interactions"""

    def __init__(self):
        # Initialize LLM clients
        self.openai_client = None
        if os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        if os.getenv("GOOGLE_API_KEY"):
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

    async def analyze_data_with_llm(self, df: pd.DataFrame, analysis: dict, filename: str, options=None) -> Dict[str, Any]:
        """Use OpenAI or Gemini to analyze data and generate intelligent insights and chart recommendations"""

        # Prepare data summary for LLM with proper serialization
        sample_data = df.head(10).to_dict() if len(df) > 0 else {}  # Increased sample size

        # Enhanced data analysis
        data_summary = {
            "filename": filename,
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": {
                "numeric": analysis['numeric_columns'],
                "categorical": analysis['categorical_columns'],
                "all_columns": analysis['columns']
            },
            "sample_data": make_json_serializable(sample_data),
            "data_types": analysis['data_types'],
            "missing_values": analysis['missing_values'],
            "basic_stats": {},
            "correlations": {},
            "trends": {},
            "outliers": {}
        }

        # Add more advanced statistics for numeric columns
        if len(analysis['numeric_columns']) > 0:
            numeric_stats = df[analysis['numeric_columns']].describe().to_dict()
            data_summary["basic_stats"] = make_json_serializable(numeric_stats)

            # Add correlation matrix for numeric columns if there are at least 2
            if len(analysis['numeric_columns']) >= 2:
                corr_matrix = df[analysis['numeric_columns']].corr().to_dict()
                data_summary["correlations"] = make_json_serializable(corr_matrix)

        # Try to add time series information if available
        time_columns = [col for col in df.columns if analysis['data_types'].get(col) in ['datetime64', 'date', 'time']]
        if time_columns:
            data_summary["time_columns"] = time_columns
            # Sample of time series data
            time_sample = {}
            for col in time_columns[:2]:  # Limit to first 2 time columns
                try:
                    time_sample[col] = sorted(df[col].dropna().unique())[:10]
                    time_sample[col] = [str(ts) for ts in time_sample[col]]
                except:
                    time_sample[col] = "Error parsing time data"
            data_summary["time_sample"] = time_sample

        # Create the prompt using the appropriate method
        prompt = self._create_enhanced_analysis_prompt(data_summary, options)

        # Choose the LLM to use based on configuration
        if LLM_MODEL == "openai" and self.openai_client:
            return await self._analyze_with_openai(prompt)
        else:
            return await self._analyze_with_gemini(prompt)

    async def _analyze_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Analyze data using OpenAI's API"""
        try:
            response = await self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a data visualization expert that creates insightful dashboards."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=3000
            )

            result_text = response.choices[0].message.content

            # Extract JSON from the response
            result_json = self._extract_json_from_text(result_text)
            return result_json

        except Exception as e:
            print(f"OpenAI Analysis Error: {str(e)}")
            # Return empty result
            return {"dashboard_title": "Error", "charts": [], "insights": f"Error: {str(e)}"}

    async def _analyze_with_gemini(self, prompt: str) -> Dict[str, Any]:
        """Analyze data using Google's Gemini API"""
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            response = model.generate_content(prompt)
            result_text = response.text

            # Extract JSON from the response
            result_json = self._extract_json_from_text(result_text)
            return result_json

        except Exception as e:
            print(f"Gemini Analysis Error: {str(e)}")
            # Return empty result
            return {"dashboard_title": "Error", "charts": [], "insights": f"Error: {str(e)}"}

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Extract JSON from the text response"""
        try:
            # Find the start and end of the JSON object
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1

            if start_idx >= 0 and end_idx > 0:
                json_str = text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")

        except Exception as e:
            print(f"JSON extraction error: {str(e)}")
            print(f"Response text: {text}")
            # Return empty JSON if extraction fails
            return {"dashboard_title": "Error", "charts": [], "insights": "Error extracting insights"}

    def _create_enhanced_analysis_prompt(self, data_summary: dict, options: Optional[Dict[str, Any]] = None) -> str:
        """Create an enhanced analysis prompt for the LLM that incorporates user preferences"""

        # Process user options
        category = options.get("category") if options else None
        chart_types = options.get("chart_types", []) if options else []
        number_of_charts = options.get("number_of_charts", 3) if options else 3
        description = options.get("description") if options else None

        # Capture data availability to help the LLM adapt to sparse datasets
        availability = {
            "rows": data_summary["shape"]["rows"],
            "columns": data_summary["shape"]["columns"],
            "numeric_columns_count": len(data_summary["columns"]["numeric"]),
            "categorical_columns_count": len(data_summary["columns"]["categorical"]),
            "has_data": data_summary["shape"]["rows"] > 0 and data_summary["shape"]["columns"] > 0,
        }

        # Build the prompt with user preferences
        category_guidance = ""
        if category:
            category_guidance = f"""
            Optional domain context: {category}. Use it only when it aligns with the observed columns; do not invent fields or assumptions not supported by the data.
            """

        chart_type_guidance = ""
        if chart_types:
            chart_types_str = ", ".join(chart_types)
            chart_type_guidance = f"""
            Prefer the following chart types when they fit the data: {chart_types_str}. Fall back to better-suited chart types if these do not make sense for the available fields.
            """

        description_guidance = ""
        if description:
            description_guidance = f"""
            ADDITIONAL CONTEXT FROM USER:
            {description}

            Use this information to guide your analysis when compatible with the observed data.
            """

        # Build complete prompt
        prompt = f"""
        You are an expert data analyst and visualization specialist with deep business intelligence experience.
        Analyze this dataset based strictly on the provided summary. Prioritize evidence from the data; do not assume domain-specific fields or trends that are not present.

        Dataset Summary:
        {json.dumps(data_summary, indent=2, cls=CustomJSONEncoder)}
        Data Availability:
        {json.dumps(availability, indent=2, cls=CustomJSONEncoder)}

        {category_guidance}
        {chart_type_guidance}
        {description_guidance}

        ANALYSIS REQUIREMENTS:
        1. **Be Data-Driven & Adaptive**: Generate up to {number_of_charts} charts that make sense for the available fields; if data is sparse or empty, produce fewer charts and clearly explain the limitation.
        2. **Chart Suitability**: Choose chart types that match the data types and available columns; avoid any chart that would require missing fields.
        3. **Business Intelligence**: Focus on actionable insights, trends, patterns, and anomalies grounded in the observed data.
        4. **Precision**: Use exact column names, proper aggregations, and meaningful metrics; do not fabricate columns or values.
        5. **Visual Distinction**: Ensure charts are visually distinct with thoughtful color schemes.
        6. **Interactive Features**: Add suggestions for interactive features that would enhance each chart.
        7. **Rich Metadata**: Include detailed metadata for each visualization.

        Return your response as a JSON object with this EXACT structure:
        {{
            "dashboard_title": "Meaningful title for the dashboard",
            "summary": "Brief 2-3 sentence summary of what the data represents",
            "key_metrics": [
                {{"metric": "Metric Name", "value": "Value", "description": "What this means"}},
                {{"metric": "Another Metric", "value": "Value", "description": "What this means"}}
            ],
            "charts": [
                {{
                    "chart_type": "bar|line|pie|scatter|area|doughnut|radar|heatmap",
                    "title": "Descriptive chart title",
                    "x_axis": "column_name",
                    "y_axis": "column_name_or_aggregation",
                    "insights": "What this chart reveals about the data",
                    "color_scheme": "primary|secondary|success|warning|info",
                    "data_config": {{
                        "source_columns": ["col1", "col2"],
                        "aggregation": "sum|count|avg|none",
                        "limit": 10,
                        "sort": "asc|desc"
                    }},
                    "metadata": {{
                        "importance": "high|medium|low",
                        "relevant_business_kpis": ["kpi1", "kpi2"],
                        "recommended_actions": ["action1", "action2"]
                    }},
                    "interactive_features": ["filter", "drill_down", "tooltip", "animation"]
                }}
            ],
            "insights": "Detailed insights about the data patterns, trends, and business implications (3-4 sentences)",
            "metadata": {{
                "data_quality_score": "high|medium|low",
                "analysis_confidence": "high|medium|low",
                "recommended_refresh_frequency": "daily|weekly|monthly",
                "key_factors": ["factor1", "factor2"],
                "potential_use_cases": ["use_case1", "use_case2"]
            }}
        }}

        Your response MUST be valid JSON. Do not include any text before or after the JSON object.
        """

        return prompt
