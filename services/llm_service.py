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

        # Enhanced statistical summaries for numeric columns
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
                        "unique_count": col_data.nunique(),
                        "q25": col_data.quantile(0.25),
                        "q75": col_data.quantile(0.75),
                        "skewness": col_data.skew() if len(col_data) > 1 else 0,
                        "total": col_data.sum()
                    })

        # Enhanced categorical summaries
        for col in analysis['categorical_columns'][:5]:  # Increased to 5 categorical columns
            if col in df.columns:
                value_counts = df[col].value_counts()
                data_summary["basic_stats"][col] = make_json_serializable({
                    "top_values": value_counts.head(15).to_dict(),  # More values
                    "unique_count": df[col].nunique(),
                    "most_common": value_counts.index[0] if len(value_counts) > 0 else None,
                    "most_common_percentage": (value_counts.iloc[0] / len(df) * 100) if len(value_counts) > 0 else 0,
                    "distribution": value_counts.head(10).to_dict()
                })

        # Add correlation analysis for numeric columns
        if len(analysis['numeric_columns']) > 1:
            numeric_df = df[analysis['numeric_columns']].select_dtypes(include=['number'])
            if len(numeric_df.columns) > 1:
                corr_matrix = numeric_df.corr()
                # Find strong correlations
                strong_correlations = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i+1, len(corr_matrix.columns)):
                        corr_val = corr_matrix.iloc[i, j]
                        if abs(corr_val) > 0.5:  # Strong correlation threshold
                            strong_correlations.append({
                                "col1": corr_matrix.columns[i],
                                "col2": corr_matrix.columns[j],
                                "correlation": corr_val
                            })
                data_summary["correlations"] = make_json_serializable(strong_correlations)

        # Add time-based analysis if date columns exist
        date_columns = df.select_dtypes(include=['datetime64', 'object']).columns
        for col in date_columns:
            try:
                df_temp = pd.to_datetime(df[col], errors='coerce')
                if not df_temp.isna().all():
                    data_summary["trends"][col] = {
                        "is_date": True,
                        "date_range": {
                            "start": df_temp.min().isoformat() if pd.notna(df_temp.min()) else None,
                            "end": df_temp.max().isoformat() if pd.notna(df_temp.max()) else None
                        }
                    }
            except:
                pass

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
        """Create an enhanced analysis prompt for the LLM"""
        return f"""
        You are an expert data analyst and visualization specialist with deep business intelligence experience.
        Analyze this Excel dataset with creativity and precision to create a comprehensive, insightful dashboard.

        Dataset Summary:
        {json.dumps(data_summary, indent=2, cls=CustomJSONEncoder)}

        ANALYSIS REQUIREMENTS:
        1. **Be Creative & Comprehensive**: Generate 5-8 diverse, meaningful charts that tell a complete story
        2. **Chart Variety**: Use different chart types (bar, line, pie, scatter, area, doughnut, radar, heatmap)
        3. **Business Intelligence**: Focus on actionable insights, trends, patterns, and anomalies
        4. **Precision**: Use exact column names, proper aggregations, and meaningful metrics
        5. **Visual Appeal**: Choose appropriate color schemes and ensure charts are visually distinct
        6. **Data-Driven**: Base recommendations on actual data patterns, correlations, and distributions

        CHART TYPE GUIDELINES:
        - **Pie/Doughnut**: For categorical distributions with percentages (ensure percentages add to 100%)
        - **Bar**: For comparisons, rankings, and categorical data
        - **Line**: For trends over time or sequential data
        - **Scatter**: For correlations between numeric variables
        - **Area**: For cumulative data or trends with magnitude
        - **Heatmap**: For correlation matrices or intensity data

        Return your response as a JSON object with this EXACT structure:
        {{
            "dashboard_title": "Creative, business-focused title that captures the essence of the data",
            "summary": "Comprehensive 3-4 sentence summary highlighting key findings and business implications",
            "key_metrics": [
                {{"metric": "Total/Average/Key Metric Name", "value": "Calculated Value with Units", "description": "Business significance and context"}},
                {{"metric": "Growth/Trend Metric", "value": "Percentage or Rate", "description": "What this trend means for business"}},
                {{"metric": "Efficiency/Performance Metric", "value": "Ratio or Score", "description": "Operational insights"}}
            ],
            "charts": [
                {{
                    "chart_type": "pie|bar|line|scatter|area|doughnut",
                    "title": "Specific, actionable chart title",
                    "x_axis": "exact_column_name",
                    "y_axis": "exact_column_name_or_calculated_metric",
                    "insights": "Detailed analysis of what this chart reveals, including specific numbers and business implications",
                    "color_scheme": "primary|secondary|success|warning|info|custom",
                    "data_config": {{
                        "source_columns": ["exact_column_name1", "exact_column_name2"],
                        "aggregation": "sum|count|avg|max|min|percentage|none",
                        "limit": 15,
                        "sort": "desc|asc",
                        "filter_conditions": {{}},
                        "show_percentages": true,
                        "group_by": "optional_grouping_column"
                    }}
                }},
                // Generate 5-8 diverse charts
            ],
            "insights": "Comprehensive business intelligence summary (4-6 sentences) covering key patterns, trends, correlations, outliers, and strategic recommendations based on the data analysis"
        }}

        CRITICAL REQUIREMENTS:
        - Only use column names that exist in the dataset
        - For pie charts, ensure data adds up to meaningful percentages
        - Include specific numbers and percentages in insights
        - Make titles business-friendly and actionable
        - Ensure each chart provides unique value and perspective
        - Focus on the most impactful and interesting patterns in the data
        - Consider seasonal trends, outliers, and correlations
        - Provide strategic recommendations based on findings
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
