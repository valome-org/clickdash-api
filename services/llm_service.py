import json
import os
from typing import Any, Dict

import google.generativeai as genai
import pandas as pd
from config.settings import LLM_MODEL
from openai import OpenAI
from utils.serialization import CustomJSONEncoder, make_json_serializable


class LLMService:
    """Service for handling LLM interactions"""

    def __init__(self):
        # Initialize LLM clients
        self.openai_client = None
        if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your-openai-api-key-here":
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        if os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here":
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

    async def analyze_data_with_llm(self, df: pd.DataFrame, analysis: dict, filename: str) -> Dict[str, Any]:
        """Use OpenAI or Gemini to analyze data and generate intelligent insights and chart recommendations"""

        # Prepare data summary for LLM with proper serialization
        sample_data = df.head(5).to_dict() if len(df) > 0 else {}

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
            "basic_stats": {}
        }

        # Add statistical summaries for numeric columns
        for col in analysis['numeric_columns']:
            if col in df.columns:
                col_data = df[col].dropna()
                if len(col_data) > 0:
                    data_summary["basic_stats"][col] = make_json_serializable({
                        "mean": col_data.mean(),
                        "median": col_data.median(),
                        "std": col_data.std() if len(col_data) > 1 else 0,
                        "min": col_data.min(),
                        "max": col_data.max(),
                        "unique_count": col_data.nunique()
                    })

        # Add categorical summaries
        for col in analysis['categorical_columns'][:3]:  # Limit to first 3 categorical columns
            if col in df.columns:
                value_counts = df[col].value_counts().head(10)
                data_summary["basic_stats"][col] = make_json_serializable({
                    "top_values": value_counts.to_dict(),
                    "unique_count": df[col].nunique(),
                    "most_common": value_counts.index[0] if len(value_counts) > 0 else None
                })

        prompt = self._create_analysis_prompt(data_summary)

        try:
            # Try primary model first (from environment configuration)
            if LLM_MODEL == "gemini" and os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here":
                return await self._analyze_with_gemini(prompt)
            elif LLM_MODEL == "openai" and self.openai_client:
                return await self._analyze_with_openai(prompt)
            # Fallback to available model
            elif os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_API_KEY") != "your-google-api-key-here":
                return await self._analyze_with_gemini(prompt)
            elif self.openai_client:
                return await self._analyze_with_openai(prompt)
            else:
                print("No LLM API keys configured, using fallback analysis")
                return self._generate_fallback_analysis(df, analysis, filename)

        except Exception as e:
            print(f"LLM Analysis error: {str(e)}")
            # Fallback to basic analysis
            return self._generate_fallback_analysis(df, analysis, filename)

    def _create_analysis_prompt(self, data_summary: dict) -> str:
        """Create the analysis prompt for the LLM"""
        return f"""
        You are a data visualization expert. Analyze this Excel dataset and create an intelligent dashboard configuration.

        Dataset Summary:
        {json.dumps(data_summary, indent=2, cls=CustomJSONEncoder)}

        Requirements:
        1. Generate 3-5 meaningful charts that tell a story about the data
        2. Choose appropriate chart types based on data characteristics
        3. Create insightful titles and descriptions
        4. Provide key business insights
        5. Suggest color schemes that enhance readability
        6. Focus on the most important patterns and relationships

        Return your response as a JSON object with this exact structure:
        {{
            "dashboard_title": "Meaningful title for the dashboard",
            "summary": "Brief 2-3 sentence summary of what the data represents",
            "key_metrics": [
                {{"metric": "Metric Name", "value": "Value", "description": "What this means"}},
                {{"metric": "Another Metric", "value": "Value", "description": "What this means"}}
            ],
            "charts": [
                {{
                    "chart_type": "bar|line|pie|scatter|area",
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
                    }}
                }}
            ],
            "insights": "Detailed insights about the data patterns, trends, and business implications (3-4 sentences)"
        }}

        Important:
        - Only reference columns that actually exist in the dataset
        - Choose chart types that make sense for the data types
        - Ensure x_axis and y_axis reference actual column names
        - Make titles business-friendly, not technical
        - Focus on actionable insights
        """

    async def _analyze_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Analyze data using OpenAI GPT"""
        if not self.openai_client:
            raise Exception("OpenAI client not configured")

        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a data visualization expert who creates insightful, business-focused dashboards. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        response_text = response.choices[0].message.content.strip()

        # Clean up the response to ensure it's valid JSON
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        parsed_response = json.loads(response_text)
        return make_json_serializable(parsed_response)

    async def _analyze_with_gemini(self, prompt: str) -> Dict[str, Any]:
        """Analyze data using Google Gemini"""
        if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "your-google-api-key-here":
            raise Exception("Google API key not configured")

        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Create system prompt for Gemini
        full_prompt = f"""
        You are a data visualization expert who creates insightful, business-focused dashboards.
        You must respond ONLY with valid JSON, no other text or formatting.

        {prompt}
        """

        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2000,
            )
        )

        response_text = response.text.strip()

        # Clean up the response to ensure it's valid JSON
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        parsed_response = json.loads(response_text)
        return make_json_serializable(parsed_response)

    def _generate_fallback_analysis(self, df: pd.DataFrame, analysis: dict, filename: str) -> Dict[str, Any]:
        """Fallback analysis when LLM is not available"""
        return make_json_serializable({
            "dashboard_title": f"Analysis of {filename}",
            "summary": f"Dataset contains {len(df)} rows and {len(df.columns)} columns with various data types.",
            "key_metrics": [
                {"metric": "Total Rows", "value": str(len(df)), "description": "Number of records in the dataset"},
                {"metric": "Columns", "value": str(len(df.columns)), "description": "Number of data fields"}
            ],
            "charts": [
                {
                    "chart_type": "bar",
                    "title": f"Distribution of {analysis['categorical_columns'][0]}" if analysis['categorical_columns'] else "Data Overview",
                    "x_axis": analysis['categorical_columns'][0] if analysis['categorical_columns'] else "Categories",
                    "y_axis": "Count",
                    "insights": "Basic distribution of categorical data",
                    "color_scheme": "primary",
                    "data_config": {
                        "source_columns": [analysis['categorical_columns'][0]] if analysis['categorical_columns'] else [],
                        "aggregation": "count",
                        "limit": 10,
                        "sort": "desc"
                    }
                }
            ],
            "insights": "This dataset provides various data points that can be analyzed for business insights. Further analysis could reveal patterns and trends."
        })
