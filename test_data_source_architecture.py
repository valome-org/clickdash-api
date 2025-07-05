#!/usr/bin/env python3
"""
Test script for the new data source architecture
"""

import asyncio
import tempfile
import pandas as pd
from pathlib import Path
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from services.data_source_service import data_source_service
from core.data_sources.base import DataSourceConfig
from adapters.excel.adapter import ExcelAdapter
from adapters.csv.adapter import CSVAdapter


async def test_excel_adapter():
    """Test Excel adapter functionality"""
    print("🔍 Testing Excel Adapter...")

    # Create test Excel file
    test_data = pd.DataFrame({
        'Name': ['Alice', 'Bob', 'Charlie', 'Diana'],
        'Age': [25, 30, 35, 28],
        'City': ['New York', 'London', 'Paris', 'Tokyo'],
        'Salary': [50000, 60000, 70000, 55000]
    })

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        test_data.to_excel(tmp_file.name, index=False)
        tmp_file_path = tmp_file.name

    try:
        # Test data source creation
        data_source = await data_source_service.create_data_source_from_file(tmp_file_path)

        if data_source:
            print("✅ Excel data source created successfully")

            # Test metadata extraction
            metadata = await data_source.get_metadata()
            print(f"✅ Metadata extracted: {metadata.row_count} rows, {metadata.column_count} columns")

            # Test data validation
            validation_results = await data_source.validate_data()
            print(f"✅ Data validation: {validation_results['status']}")

            # Test data retrieval
            data = await data_source.get_data(limit=2)
            print(f"✅ Data retrieved: {len(data)} rows")

            # Test capabilities
            capabilities = await data_source.get_capabilities()
            print(f"✅ Capabilities: {capabilities.supported_formats}")

            # Cleanup
            await data_source.disconnect()

        else:
            print("❌ Failed to create Excel data source")

    finally:
        # Clean up temp file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


async def test_csv_adapter():
    """Test CSV adapter functionality"""
    print("\n🔍 Testing CSV Adapter...")

    # Create test CSV file
    test_data = pd.DataFrame({
        'Product': ['Widget A', 'Widget B', 'Widget C', 'Widget D'],
        'Price': [10.99, 15.99, 20.99, 25.99],
        'Category': ['Electronics', 'Books', 'Clothing', 'Electronics'],
        'In Stock': [True, False, True, True]
    })

    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as tmp_file:
        test_data.to_csv(tmp_file.name, index=False)
        tmp_file_path = tmp_file.name

    try:
        # Test data source creation
        data_source = await data_source_service.create_data_source_from_file(tmp_file_path)

        if data_source:
            print("✅ CSV data source created successfully")

            # Test metadata extraction
            metadata = await data_source.get_metadata()
            print(f"✅ Metadata extracted: {metadata.row_count} rows, {metadata.column_count} columns")

            # Test data validation
            validation_results = await data_source.validate_data()
            print(f"✅ Data validation: {validation_results['status']}")

            # Test data retrieval with filters
            data = await data_source.get_data(
                filters={'Category': 'Electronics'},
                limit=10
            )
            print(f"✅ Filtered data retrieved: {len(data)} rows")

            # Test streaming
            chunk_count = 0
            async for chunk in data_source.get_data_stream(chunk_size=2):
                chunk_count += 1
                print(f"✅ Stream chunk {chunk_count}: {len(chunk)} rows")

            # Cleanup
            await data_source.disconnect()

        else:
            print("❌ Failed to create CSV data source")

    finally:
        # Clean up temp file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


async def test_data_source_service():
    """Test the data source service"""
    print("\n🔍 Testing Data Source Service...")

    # Test supported formats
    formats = data_source_service.get_supported_formats()
    print(f"✅ Supported formats: {formats}")

    # Test registry info
    registry_info = data_source_service.get_registry_info()
    print(f"✅ Registered sources: {registry_info['registered_sources']}")

    # Test health check
    health_info = await data_source_service.health_check()
    print(f"✅ Health check: {health_info['status']}")


async def test_comprehensive_workflow():
    """Test a comprehensive workflow"""
    print("\n🔍 Testing Comprehensive Workflow...")

    # Create test data with various data quality issues
    test_data = pd.DataFrame({
        'ID': [1, 2, 3, 4, 5, 5],  # Duplicate ID
        'Name': ['Alice', 'Bob', None, 'Diana', 'Eve', 'Alice'],  # Missing value, duplicate name
        'Age': [25, 30, 35, 28, 22, 25],
        'Email': ['alice@test.com', 'bob@test.com', 'charlie@test.com', None, 'eve@test.com', 'alice@test.com'],
        'Score': [85.5, 92.0, 78.5, 88.0, 91.5, 85.5]
    })

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
        test_data.to_excel(tmp_file.name, index=False)
        tmp_file_path = tmp_file.name

    try:
        # Test comprehensive analysis
        analysis_results = await data_source_service.analyze_file(tmp_file_path)

        if analysis_results:
            print("✅ Comprehensive analysis completed")
            print(f"   📊 Quality Score: {analysis_results['metadata']['quality_score']}")
            print(f"   🔍 Validation Status: {analysis_results['validation']['status']}")
            print(f"   📋 Capabilities: {len(analysis_results['capabilities'])} features")

            # Print validation details
            if analysis_results['validation']['warnings']:
                print("   ⚠️  Data Quality Warnings:")
                for warning in analysis_results['validation']['warnings']:
                    print(f"     - {warning}")

            # Print recommendations
            if analysis_results['validation']['recommendations']:
                print("   💡 Recommendations:")
                for rec in analysis_results['validation']['recommendations']:
                    print(f"     - {rec}")

        else:
            print("❌ Comprehensive analysis failed")

    finally:
        # Clean up temp file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


async def main():
    """Main test function"""
    print("🚀 Testing AI Dashboard Platform - Data Source Architecture")
    print("=" * 60)

    try:
        await test_excel_adapter()
        await test_csv_adapter()
        await test_data_source_service()
        await test_comprehensive_workflow()

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("🎉 New data source architecture is working properly!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
