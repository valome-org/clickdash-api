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
            limit = data_config.get("limit", 15)
            sort_order = data_config.get("sort", "desc")
            show_percentages = data_config.get("show_percentages", False)

            if not source_columns or not all(col in df.columns for col in source_columns):
                # Fallback to first available columns
                if chart_type in ["bar", "pie", "doughnut"] and len(df.select_dtypes(include=['object']).columns) > 0:
                    source_columns = [df.select_dtypes(include=['object']).columns[0]]
                    aggregation = "count"
                elif len(df.select_dtypes(include=['number']).columns) > 0:
                    source_columns = [df.select_dtypes(include=['number']).columns[0]]
                    aggregation = "sum"
                else:
                    return {
                        "labels": ["No Data"],
                        "datasets": [{
                            "label": "No Data",
                            "data": [0],
                            "backgroundColor": ["rgba(156, 163, 175, 0.8)"],
                            "borderColor": ["rgba(156, 163, 175, 1)"],
                            "borderWidth": 1
                        }]
                    }

            if chart_type in ["bar", "pie", "doughnut"]:
                return self._generate_bar_pie_chart_data(df, source_columns, aggregation, limit, sort_order, chart_config, show_percentages)
            elif chart_type == "line":
                return self._generate_line_chart_data(df, source_columns, limit, chart_config)

            # Default to bar chart for any other type
            return self._generate_bar_pie_chart_data(df, source_columns, "count", limit, sort_order, chart_config, show_percentages)

        except Exception as e:
            print(f"Chart data generation error: {str(e)}")
            # Return a safe fallback structure
            return {
                "labels": ["No Data"],
                "datasets": [{
                    "label": "No Data",
                    "data": [0],
                    "backgroundColor": ["rgba(156, 163, 175, 0.8)"],
                    "borderColor": ["rgba(156, 163, 175, 1)"],
                    "borderWidth": 1
                }]
            }

    def _generate_bar_pie_chart_data(self, df: pd.DataFrame, source_columns: list, aggregation: str,
                                   limit: int, sort_order: str, chart_config: dict, show_percentages: bool = False) -> dict:
        """Generate data for bar, pie, and doughnut charts with enhanced percentage support"""
        chart_type = chart_config.get("chart_type", "bar")

        # Categorical data aggregation
        if aggregation == "count":
            result = df[source_columns[0]].value_counts().head(limit)
        elif aggregation == "percentage":
            result = df[source_columns[0]].value_counts(normalize=True) * 100
            result = result.head(limit)
        else:
            if len(source_columns) > 1:
                result = df.groupby(source_columns[0])[source_columns[1]].agg(aggregation).head(limit)
            else:
                result = df[source_columns[0]].value_counts().head(limit)

        if sort_order == "asc":
            result = result.sort_values()

        # Convert to JSON serializable format
        labels = make_json_serializable(result.index.tolist())
        values = make_json_serializable(result.values.tolist())

        # For pie charts, calculate percentages
        if chart_type in ["pie", "doughnut"] or show_percentages:
            total = sum(values)
            if total > 0:
                percentages = [(v/total)*100 for v in values]
                # Add percentage labels
                labels_with_percentages = [f"{label} ({perc:.1f}%)" for label, perc in zip(labels, percentages)]
            else:
                percentages = values
                labels_with_percentages = labels
        else:
            labels_with_percentages = labels
            percentages = values

        # Enhanced color schemes with more variety
        color_schemes = {
            "primary": [
                "rgba(59, 130, 246, 0.8)", "rgba(99, 102, 241, 0.8)", "rgba(139, 92, 246, 0.8)",
                "rgba(168, 85, 247, 0.8)", "rgba(236, 72, 153, 0.8)", "rgba(239, 68, 68, 0.8)",
                "rgba(245, 158, 11, 0.8)", "rgba(34, 197, 94, 0.8)", "rgba(6, 182, 212, 0.8)",
                "rgba(156, 163, 175, 0.8)"
            ],
            "success": [
                "rgba(34, 197, 94, 0.8)", "rgba(22, 163, 74, 0.8)", "rgba(21, 128, 61, 0.8)",
                "rgba(20, 83, 45, 0.8)", "rgba(134, 239, 172, 0.8)", "rgba(74, 222, 128, 0.8)"
            ],
            "warning": [
                "rgba(245, 158, 11, 0.8)", "rgba(217, 119, 6, 0.8)", "rgba(180, 83, 9, 0.8)",
                "rgba(146, 64, 14, 0.8)", "rgba(251, 191, 36, 0.8)", "rgba(252, 211, 77, 0.8)"
            ],
            "info": [
                "rgba(6, 182, 212, 0.8)", "rgba(14, 165, 233, 0.8)", "rgba(37, 99, 235, 0.8)",
                "rgba(67, 56, 202, 0.8)", "rgba(103, 232, 249, 0.8)", "rgba(125, 211, 252, 0.8)"
            ],
            "custom": [
                "rgba(255, 99, 132, 0.8)", "rgba(54, 162, 235, 0.8)", "rgba(255, 205, 86, 0.8)",
                "rgba(75, 192, 192, 0.8)", "rgba(153, 102, 255, 0.8)", "rgba(255, 159, 64, 0.8)",
                "rgba(199, 199, 199, 0.8)", "rgba(83, 102, 255, 0.8)", "rgba(255, 99, 255, 0.8)",
                "rgba(99, 255, 132, 0.8)"
            ]
        }

        scheme = chart_config.get("color_scheme", "primary")
        colors = color_schemes.get(scheme, color_schemes["primary"])

        # Ensure we have enough colors
        extended_colors = colors * (len(values) // len(colors) + 1)

        chart_data = {
            "labels": labels_with_percentages if chart_type in ["pie", "doughnut"] else labels,
            "datasets": [{
                "label": chart_config.get("title", "Data"),
                "data": values,
                "backgroundColor": extended_colors[:len(values)],
                "borderColor": [c.replace("0.8", "1") for c in extended_colors[:len(values)]],
                "borderWidth": 2 if chart_type in ["pie", "doughnut"] else 1
            }]
        }

        # Add percentage data for pie charts
        if chart_type in ["pie", "doughnut"]:
            chart_data["datasets"][0]["percentages"] = percentages

        return make_json_serializable(chart_data)

    def _generate_line_chart_data(self, df: pd.DataFrame, source_columns: list, limit: int) -> dict:
        """Generate data for line charts with enhanced time series support"""
        column = source_columns[0]

        # Check if we have a date column for time series
        if len(source_columns) > 1:
            # Try to create time series data
            try:
                date_col = source_columns[0]
                value_col = source_columns[1]

                # Convert to datetime if possible
                df_temp = df.copy()
                df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors='coerce')
                df_temp = df_temp.dropna(subset=[date_col, value_col])

                if not df_temp.empty:
                    # Group by date and aggregate
                    df_grouped = df_temp.groupby(df_temp[date_col].dt.date)[value_col].sum().head(limit)

                    return make_json_serializable({
                        "labels": [str(date) for date in df_grouped.index],
                        "datasets": [{
                            "label": f"{value_col} over time",
                            "data": df_grouped.values.tolist(),
                            "borderColor": "rgba(34, 197, 94, 1)",
                            "backgroundColor": "rgba(34, 197, 94, 0.1)",
                            "tension": 0.4,
                            "fill": False
                        }]
                    })
            except:
                pass

        # Fallback to simple line chart
        data = df[column].dropna().head(limit)
        return make_json_serializable({
            "labels": [str(i+1) for i in range(len(data))],
            "datasets": [{
                "label": column,
                "data": data.tolist(),
                "borderColor": "rgba(34, 197, 94, 1)",
                "backgroundColor": "rgba(34, 197, 94, 0.1)",
                "tension": 0.4,
                "fill": False
            }]
        })

    async def generate_llm_dashboard(self, df: pd.DataFrame, analysis: dict, filename: str, options=None) -> DashboardConfig:
        """Generate complete dashboard using LLM analysis"""
        try:
            # Get LLM analysis with user options
            llm_analysis = await self.llm_service.analyze_data_with_llm(df, analysis, filename, options)

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
                    color_scheme=chart_spec.get("color_scheme", "primary"),
                    # Add more metadata for interactivity
                    metadata=chart_spec.get("metadata", {}),
                    interactive_features=chart_spec.get("interactive_features", [])
                )
                charts.append(chart)

            dashboard_config = DashboardConfig(
                title=llm_analysis.get("dashboard_title", f"Dashboard - {filename}"),
                charts=charts,
                insights=llm_analysis.get("insights", ""),
                summary=llm_analysis.get("summary", ""),
                key_metrics=make_json_serializable(llm_analysis.get("key_metrics", [])),
                category=options.get("category") if options else None,
                metadata=llm_analysis.get("metadata", {})
            )

            return dashboard_config

        except Exception as e:
            print(f"LLM Dashboard generation error: {str(e)}")
            # Fallback to basic dashboard
            return self.generate_basic_dashboard(df, analysis, filename, options)

    def generate_basic_dashboard(self, df: pd.DataFrame, analysis: dict, filename: str, options=None) -> DashboardConfig:
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

        # Use user-specified options if available
        category = options.get("category") if options else None
        description = options.get("description") if options else None

        summary_text = f"Analysis of {filename} containing {len(df)} rows and {len(df.columns)} columns"
        if description:
            summary_text += f". {description}"

        return DashboardConfig(
            title=f"{category.capitalize() if category else 'Basic'} Dashboard - {filename}",
            charts=charts,
            insights="Basic dashboard with fundamental data visualizations",
            summary=summary_text,
            key_metrics=make_json_serializable([
                {"metric": "Total Records", "value": str(len(df)), "description": "Number of data rows"},
                {"metric": "Data Fields", "value": str(len(df.columns)), "description": "Number of columns"}
            ]),
            category=category
        )
