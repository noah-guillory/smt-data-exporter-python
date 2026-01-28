#!/usr/bin/env python3
"""
Local test script for the Lambda function.
This allows you to test the Lambda function locally before deploying to AWS.

Usage:
    python test_lambda_local.py

Make sure to set the required environment variables before running:
    export SMT_USERNAME="your_username"
    export SMT_PASSWORD="your_password"
    export YNAB_ACCESS_TOKEN="your_token"
    export YNAB_BUDGET_ID="your_budget_id"
    export YNAB_CATEGORY_ID="your_category_id"
    export KWH_RATE="0.17754"
    export HEALTHCHECK_URL="https://hc-ping.com/your-uuid"  # Optional
"""

import json
import sys
from lambda_function import lambda_handler

def test_lambda_locally():
    """Test the Lambda function locally."""
    
    # Mock EventBridge event
    event = {
        "version": "0",
        "id": "test-event-id",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": "2025-01-01T02:00:00Z",
        "region": "us-east-1",
        "resources": ["arn:aws:events:us-east-1:123456789012:rule/test-rule"],
        "detail": {}
    }
    
    # Mock Lambda context
    class MockContext:
        function_name = "smt-data-exporter"
        function_version = "$LATEST"
        invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:smt-data-exporter"
        memory_limit_in_mb = 256
        aws_request_id = "test-request-id"
        log_group_name = "/aws/lambda/smt-data-exporter"
        log_stream_name = "test-stream"
        
        def get_remaining_time_in_millis(self):
            return 300000  # 5 minutes
    
    context = MockContext()
    
    print("=" * 60)
    print("Testing Lambda Function Locally")
    print("=" * 60)
    print(f"Event: {json.dumps(event, indent=2)}")
    print(f"Context: function_name={context.function_name}, memory={context.memory_limit_in_mb}MB")
    print("=" * 60)
    print()
    
    try:
        # Invoke the Lambda handler
        response = lambda_handler(event, context)
        
        print()
        print("=" * 60)
        print("Lambda Response:")
        print("=" * 60)
        print(json.dumps(response, indent=2))
        print("=" * 60)
        
        if response.get('statusCode') == 200:
            print("\n✅ Lambda function executed successfully!")
            return 0
        else:
            print("\n❌ Lambda function returned an error")
            return 1
            
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ Error executing Lambda function:")
        print("=" * 60)
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(test_lambda_locally())
