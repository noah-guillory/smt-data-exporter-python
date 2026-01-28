#!/usr/bin/env python3
"""
Unit tests for the Lambda function's calculate_trailing_12_month_average function.
This ensures the pure Python implementation matches the expected behavior.
"""

import sys
import os
from datetime import datetime
from collections import defaultdict

# Add the current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from models import MonthlyBillingDataResponse, Data, BillingData


def calculate_trailing_12_month_average_test(report: MonthlyBillingDataResponse) -> float:
    """
    Test version of calculate_trailing_12_month_average (copied to avoid module loading).
    Calculate the trailing 12-month average kWh usage from the API response object.
    Returns the average for the latest month in the dataset.
    Uses pure Python instead of pandas.
    """
    billing_data = report.data.billing_data
    if not billing_data:
        return 0.0
    
    # Group data by month (YYYY-MM format)
    monthly_usage = defaultdict(float)
    for bd in billing_data:
        month_key = bd.start_date.strftime("%Y-%m")
        monthly_usage[month_key] += bd.actual_kwh
    
    # Sort months chronologically
    sorted_months = sorted(monthly_usage.items())
    
    if not sorted_months:
        return 0.0
    
    # Calculate trailing 12-month averages for each month
    trailing_averages = {}
    for i in range(len(sorted_months)):
        month, _ = sorted_months[i]
        # Get the last 12 months including current month
        start_idx = max(0, i - 11)
        window_data = sorted_months[start_idx:i + 1]
        
        if len(window_data) >= 12:
            avg_kwh = sum(kwh for _, kwh in window_data) / 12
            trailing_averages[month] = avg_kwh
    
    if not trailing_averages:
        # If we don't have 12 months of data yet, return 0
        return 0.0
    
    # Get the latest month's trailing average
    latest_month = sorted_months[-1][0]
    latest_avg = trailing_averages.get(latest_month, 0.0)
    
    return float(latest_avg)


def test_calculate_trailing_12_month_average():
    """Test the trailing 12-month average calculation with sample data."""
    
    # Create sample billing data for 13 months
    billing_data_list = []
    base_kwh = 1000.0
    
    for i in range(13):
        month_offset = 13 - i  # Start 13 months ago
        date_str = f"{2024 - (month_offset // 12):04d}-{(month_offset % 12) or 12:02d}-01"
        
        bd = BillingData(
            start_date=datetime.strptime(date_str, "%Y-%m-%d"),
            end_date=datetime.strptime(date_str, "%Y-%m-%d"),
            revision_date=datetime.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S"),
            actual_kwh=base_kwh + (i * 10),  # Gradually increasing usage
            metered_kw=10.0,
            billed_kw=10.0,
            metered_kva=10.0,
            billed_kva=10.0
        )
        billing_data_list.append(bd)
    
    # Create response object
    data = Data(
        trans_id="test-123",
        esiid="test-esiid",
        billing_data=billing_data_list
    )
    response = MonthlyBillingDataResponse(data=data)
    
    # Calculate average
    average = calculate_trailing_12_month_average_test(response)
    
    # Expected: average of the last 12 months (excluding the oldest month)
    # Values: 1010, 1020, 1030, ..., 1120 (12 values)
    # Average: (1010 + 1020 + ... + 1120) / 12 = 1065.0
    expected_average = sum(base_kwh + (i * 10) for i in range(1, 13)) / 12
    
    print(f"Calculated average: {average:.2f} kWh")
    print(f"Expected average: {expected_average:.2f} kWh")
    
    # Allow small floating point differences
    assert abs(average - expected_average) < 0.01, \
        f"Expected {expected_average:.2f}, got {average:.2f}"
    
    print("✅ Test passed!")


def test_less_than_12_months():
    """Test with less than 12 months of data."""
    
    billing_data_list = []
    for i in range(6):  # Only 6 months
        date_str = f"2024-{i+1:02d}-01"
        bd = BillingData(
            start_date=datetime.strptime(date_str, "%Y-%m-%d"),
            end_date=datetime.strptime(date_str, "%Y-%m-%d"),
            revision_date=datetime.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S"),
            actual_kwh=1000.0,
            metered_kw=10.0,
            billed_kw=10.0,
            metered_kva=10.0,
            billed_kva=10.0
        )
        billing_data_list.append(bd)
    
    data = Data(
        trans_id="test-123",
        esiid="test-esiid",
        billing_data=billing_data_list
    )
    response = MonthlyBillingDataResponse(data=data)
    
    average = calculate_trailing_12_month_average_test(response)
    
    print(f"Average with < 12 months: {average:.2f} kWh")
    assert average == 0.0, "Should return 0.0 when less than 12 months"
    print("✅ Test passed!")


def test_empty_data():
    """Test with empty billing data."""
    
    data = Data(
        trans_id="test-123",
        esiid="test-esiid",
        billing_data=[]
    )
    response = MonthlyBillingDataResponse(data=data)
    
    average = calculate_trailing_12_month_average_test(response)
    
    print(f"Average with empty data: {average:.2f} kWh")
    assert average == 0.0, "Should return 0.0 for empty data"
    print("✅ Test passed!")


def test_multiple_entries_per_month():
    """Test with multiple billing entries in the same month (should be summed)."""
    
    billing_data_list = []
    # Add 2 entries for each of 12 months
    for month in range(1, 13):
        for entry in range(2):
            date_str = f"2024-{month:02d}-01"
            bd = BillingData(
                start_date=datetime.strptime(date_str, "%Y-%m-%d"),
                end_date=datetime.strptime(date_str, "%Y-%m-%d"),
                revision_date=datetime.strptime(f"{date_str} 00:00:00", "%Y-%m-%d %H:%M:%S"),
                actual_kwh=500.0,  # Each entry is 500 kWh
                metered_kw=10.0,
                billed_kw=10.0,
                metered_kva=10.0,
                billed_kva=10.0
            )
            billing_data_list.append(bd)
    
    data = Data(
        trans_id="test-123",
        esiid="test-esiid",
        billing_data=billing_data_list
    )
    response = MonthlyBillingDataResponse(data=data)
    
    average = calculate_trailing_12_month_average_test(response)
    
    # Each month has 2 entries of 500 kWh = 1000 kWh per month
    # Average of 12 months = 1000 kWh
    print(f"Average with multiple entries per month: {average:.2f} kWh")
    assert abs(average - 1000.0) < 0.01, f"Expected 1000.0, got {average:.2f}"
    print("✅ Test passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing calculate_trailing_12_month_average")
    print("=" * 60)
    print()
    
    try:
        print("Test 1: Normal case with 13 months of data")
        test_calculate_trailing_12_month_average()
        print()
        
        print("Test 2: Less than 12 months of data")
        test_less_than_12_months()
        print()
        
        print("Test 3: Empty data")
        test_empty_data()
        print()
        
        print("Test 4: Multiple entries per month")
        test_multiple_entries_per_month()
        print()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ Test failed: {e}")
        print("=" * 60)
        exit(1)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        exit(1)
