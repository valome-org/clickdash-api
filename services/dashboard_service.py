import pandas as pd
from models.dashboard import ChartConfig, DashboardConfig
from utils.serialization import make_json_serializable

from .llm_service import LLMService


class DashboardService:
    """Service for handling dashboard generation and chart data"""

    def __init__(self):
        self.llm_service = LLMService()

    def generate_chart_data(self, df: pd.DataFrame, chart_config: dict) -> dict:
        """Generate actual chart data based on LLM recommendations"""
        try:
            chart_type = chart_config.get("chart_type", "bar")
            data_config = chart_config.get("data_config", {})
            source_columns = data_config.get("source_columns", [])
            aggregation = data_config.get("aggregation", "count")
            limit = data_config.get("limit", 10)
            sort_order = data_config.get("sort", "desc")

            if not source_columns or not all(col in df.columns for col in source_columns):
                # Fallback to first available columns
                if chart_type in ["bar", "pie"] and len(df.select_dtypes(include=['object']).columns) > 0:
                    source_columns = [df.select_dtypes(include=['object']).columns[0]]
                    aggregation = "count"
                elif len(df.select_dtypes(include=['number']).columns) > 0:
                    source_columns = [df.select_dtypes(include=['number']).columns[0]]
                    aggregation = "sum"
                else:
                    return {"labels": ["No Data"], "datasets": [{"data": [0]}]}

            if chart_type in ["bar", "pie"]:
                return self._generate_bar_pie_chart_data(df, source_columns, aggregation, limit, sort_order, chart_config)
            elif chart_type == "line":
                return self._generate_line_chart_data(df, source_columns, limit)
            elif chart_type == "scatter":
                return self._generate_scatter_chart_data(df, source_columns)

            # Default fallback
            return {"labels": ["No Data"], "datasets": [{"data": [0]}]}

        except Exception as e:
            print(f"Chart data generation error: {str(e)}")
            return {"labels": ["Error"], "datasets": [{"data": [0]}]}

    def _generate_bar_pie_chart_data(self, df: pd.DataFrame, source_columns: list, aggregation: str,
                                   limit: int, sort_order: str, chart_config: dict) -> dict:
        """Generate data for bar and pie charts"""
        # Categorical data aggregation
        if aggregation == "count":
            result = df[source_columns[0]].value_counts().head(limit)
        else:
            result = df.groupby(source_columns[0])[source_columns[1]].agg(aggregation).head(limit) if len(source_columns) > 1 else df[source_columns[0]].value_counts().head(limit)

        if sort_order == "asc":
            result = result.sort_values()

        # Convert to JSON serializable format
        labels = make_json_serializable(result.index.tolist())
        values = make_json_serializable(result.values.tolist())

        # Color schemes
        color_schemes = {
            "primary": ["rgba(59, 130, 246, 0.8)", "rgba(99, 102, 241, 0.8)", "rgba(139, 92, 246, 0.8)"],
            "secondary": ["rgba(107, 114, 128, 0.8)", "rgba(156, 163, 175, 0.8)", "rgba(209, 213, 219, 0.8)"],
            "success": ["rgba(34, 197, 94, 0.8)", "rgba(22, 163, 74, 0.8)", "rgba(21, 128, 61, 0.8)"],
            "warning": ["rgba(245, 158, 11, 0.8)", "rgba(217, 119, 6, 0.8)", "rgba(180, 83, 9, 0.8)"],
            "info": ["rgba(6, 182, 212, 0.8)", "rgba(14, 165, 233, 0.8)", "rgba(37, 99, 235, 0.8)"]
        }

        scheme = chart_config.get("color_scheme", "primary")
        colors = color_schemes.get(scheme, color_schemes["primary"])

        return make_json_serializable({
            "labels": labels,
            "datasets": [{
                "label": chart_config.get("title", "Data"),
                "data": values,
                "backgroundColor": colors * (len(values) // len(colors) + 1),
                "borderColor": [c.replace("0.8", "1") for c in colors] * (len(values) // len(colors) + 1),
                "borderWidth": 1
            }]
        })

    def _generate_line_chart_data(self, df: pd.DataFrame, source_columns: list, limit: int) -> dict:
        """Generate data for line charts"""
        column = source_columns[0]
        data = df[column].dropna().head(limit)

        return make_json_serializable({
            "labels": [str(i) for i in range(len(data))],
            "datasets": [{
                "label": column,
                "data": data.tolist(),
                "borderColor": "rgba(34, 197, 94, 1)",
                "backgroundColor": "rgba(34, 197, 94, 0.1)",
                "tension": 0.4
            }]
        })

    def _generate_scatter_chart_data(self, df: pd.DataFrame, source_columns: list) -> dict:
        """Generate data for scatter charts"""
        if len(source_columns) >= 2:
            x_data = df[source_columns[0]].dropna()
            y_data = df[source_columns[1]].dropna()
            min_len = min(len(x_data), len(y_data))

            scatter_data = []
            for i in range(min_len):
                scatter_data.append({
                    "x": make_json_serializable(x_data.iloc[i]),
                    "y": make_json_serializable(y_data.iloc[i])
                })

            return {
                "datasets": [{
                    "label": f"{source_columns[0]} vs {source_columns[1]}",
                    "data": scatter_data,
                    "backgroundColor": "rgba(59, 130, 246, 0.6)"
                }]
            }
        return {"labels": ["No Data"], "datasets": [{"data": [0]}]}

    async def generate_llm_dashboard(self, df: pd.DataFrame, analysis: dict, filename: str) -> DashboardConfig:
        """Generate complete dashboard using LLM analysis"""
        try:
            # Get LLM analysis
            llm_analysis = await self.llm_service.analyze_data_with_llm(df, analysis, filename)

            # Generate charts based on LLM recommendations
            charts = []
            for chart_spec in llm_analysis.get("charts", []):
                chart_data = self.generate_chart_data(df, chart_spec)

                chart = ChartConfig(
                    chart_type=chart_spec.get("chart_type", "bar"),
                    title=chart_spec.get("title", "Chart"),
                    x_axis=chart_spec.get("x_axis", "X"),
                    y_axis=chart_spec.get("y_axis", "Y"),
                    data=chart_data,
                    insights=chart_spec.get("insights", ""),
                    color_scheme=chart_spec.get("color_scheme", "primary")
                )
                charts.append(chart)

            dashboard_config = DashboardConfig(
                title=llm_analysis.get("dashboard_title", f"Dashboard - {filename}"),
                charts=charts,
                insights=llm_analysis.get("insights", ""),
                summary=llm_analysis.get("summary", ""),
                key_metrics=make_json_serializable(llm_analysis.get("key_metrics", []))
            )

            return dashboard_config

        except Exception as e:
            print(f"LLM Dashboard generation error: {str(e)}")
            # Fallback to basic dashboard
            return self.generate_basic_dashboard(df, analysis, filename)

    def generate_basic_dashboard(self, df: pd.DataFrame, analysis: dict, filename: str) -> DashboardConfig:
        """Fallback dashboard generation"""
        charts = []

        # Basic bar chart for categorical data
        if analysis['categorical_columns']:
            cat_col = analysis['categorical_columns'][0]
            value_counts = df[cat_col].value_counts().head(10)

            chart_data = make_json_serializable({
                "labels": value_counts.index.tolist(),
                "datasets": [{
                    "label": "Count",
                    "data": value_counts.values.tolist(),
                    "backgroundColor": "rgba(59, 130, 246, 0.5)"
                }]
            })

            charts.append(ChartConfig(
                chart_type="bar",
                title=f"Distribution of {cat_col}",
                x_axis=cat_col,
                y_axis="Count",
                data=chart_data,
                insights=f"Shows the distribution of {cat_col} values in the dataset"
            ))

        return DashboardConfig(
            title=f"Basic Dashboard - {filename}",
            charts=charts,
            insights="Basic dashboard with fundamental data visualizations",
            summary=f"Analysis of {filename} containing {len(df)} rows and {len(df.columns)} columns",
            key_metrics=make_json_serializable([
                {"metric": "Total Records", "value": str(len(df)), "description": "Number of data rows"},
                {"metric": "Data Fields", "value": str(len(df.columns)), "description": "Number of columns"}
            ])
        )
