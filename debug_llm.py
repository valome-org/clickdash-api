import asyncio

import pandas as pd
from dotenv import load_dotenv
from main import analyze_data_with_llm

load_dotenv()

async def test_llm_analysis():
    """Test the LLM analysis function"""

    # Create sample data similar to the travel data
    data = {
        'Employee Name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown'],
        'Department': ['Sales', 'Marketing', 'IT', 'Sales'],
        'Travel Date': ['2021-01-15', '2021-02-10', '2021-03-05', '2021-01-20'],
        'Destination': ['New York', 'London', 'Tokyo', 'Paris'],
        'Cost': [1500, 2200, 3000, 1800]
    }

    df = pd.DataFrame(data)

    analysis = {
        'columns': list(df.columns),
        'rows': len(df),
        'numeric_columns': ['Cost'],
        'categorical_columns': ['Employee Name', 'Department', 'Destination'],
        'summary': df.describe(include='all').fillna('').to_dict(),
        'missing_values': df.isnull().sum().to_dict(),
        'data_types': df.dtypes.astype(str).to_dict()
    }

    print("🧪 Testing LLM analysis...")

    try:
        result = await analyze_data_with_llm(df, analysis, "test_travel.xlsx")
        print("✅ LLM Analysis successful!")
        print(f"Dashboard title: {result.get('dashboard_title', 'N/A')}")
        print(f"Number of charts: {len(result.get('charts', []))}")
        print(f"Summary: {result.get('summary', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ LLM Analysis failed: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_llm_analysis())
