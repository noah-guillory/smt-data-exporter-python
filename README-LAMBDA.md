# SMT Data Exporter - AWS Lambda

> **💡 Deployment Options:**
> - This guide covers CloudFormation deployment using `deploy.sh`
> - For AWS CDK (TypeScript) deployment, see [cdk/README.md](cdk/README.md)

## Overview
This AWS Lambda function automates the retrieval of monthly electricity usage data from Smart Meter Texas using the official API, calculates the trailing 12-month average kWh usage, and updates a YNAB (You Need A Budget) category target based on your usage and kWh rate.

## Features
- **AWS Lambda Function**: Serverless execution with EventBridge scheduled triggers
- **No pandas dependency**: Lightweight deployment package using pure Python
- **CloudFormation Infrastructure**: Complete infrastructure-as-code deployment
- **Smart Meter Texas API**: Secure, reliable data access (no browser automation or web scraping)
- **Trailing 12-month average**: Calculates electricity usage directly from API data
- **YNAB Integration**: Automatically updates your electric bill category target
- **Secure Configuration**: All credentials stored as Lambda environment variables
- **Monitoring**: CloudWatch logs and alarms for error tracking

## Architecture

The solution includes:
- **Lambda Function**: Python 3.11 runtime processing Smart Meter Texas data
- **EventBridge Rule**: Scheduled trigger (default: monthly on the 1st at 2 AM UTC)
- **IAM Role**: Least-privilege execution role for Lambda
- **CloudWatch Logs**: Centralized logging with 30-day retention
- **CloudWatch Alarm**: Alert on Lambda execution errors

## Prerequisites

1. **AWS Account** with appropriate permissions to create:
   - Lambda functions
   - IAM roles
   - EventBridge rules
   - CloudWatch resources
   - S3 buckets

2. **AWS CLI** configured with credentials:
   ```bash
   aws configure
   ```

3. **S3 Bucket** for Lambda deployment package:
   ```bash
   aws s3 mb s3://your-deployment-bucket
   ```

4. **Smart Meter Texas Account** credentials

5. **YNAB Account** with:
   - Personal Access Token
   - Budget ID
   - Category ID for electric bill

## Quick Start

### 1. Set Environment Variables

Create a `.env` file or export variables:

```bash
export S3_BUCKET="your-deployment-bucket"
export AWS_REGION="us-east-1"
export SMT_USERNAME="your_smt_username"
export SMT_PASSWORD="your_smt_password"
export YNAB_ACCESS_TOKEN="your_ynab_token"
export YNAB_BUDGET_ID="your_budget_id"
export YNAB_CATEGORY_ID="your_category_id"
export KWH_RATE="0.17754"
export HEALTHCHECK_URL="https://hc-ping.com/your-uuid"  # Optional
```

### 2. Deploy

```bash
./deploy.sh
```

The deployment script will:
1. Install Python dependencies
2. Create deployment package
3. Upload to S3
4. Deploy CloudFormation stack
5. Configure Lambda function with your environment variables

### 3. Verify Deployment

Check the Lambda function in AWS Console:
```bash
aws lambda get-function --function-name smt-data-exporter
```

View CloudFormation stack outputs:
```bash
aws cloudformation describe-stacks --stack-name smt-data-exporter
```

### 4. Test Manually

Invoke the Lambda function manually:
```bash
aws lambda invoke \
    --function-name smt-data-exporter \
    --payload '{}' \
    response.json

cat response.json
```

## Configuration

### Schedule Expression

The default schedule runs monthly on the 1st at 2 AM UTC. To customize:

```bash
# Run daily at 3 AM UTC
aws cloudformation deploy \
    --template-file cloudformation.yaml \
    --stack-name smt-data-exporter \
    --parameter-overrides ScheduleExpression="cron(0 3 * * ? *)" \
    ...
```

Schedule expression formats:
- `cron(0 2 1 * ? *)` - Monthly on 1st at 2 AM UTC
- `cron(0 3 * * ? *)` - Daily at 3 AM UTC
- `rate(7 days)` - Every 7 days

### Lambda Configuration

Adjust Lambda settings via CloudFormation parameters:
- `LambdaTimeout`: Execution timeout (default: 300 seconds)
- `LambdaMemorySize`: Memory allocation (default: 256 MB)

## Monitoring

### CloudWatch Logs

View logs:
```bash
aws logs tail /aws/lambda/smt-data-exporter --follow
```

### CloudWatch Alarms

An alarm is automatically created to alert on Lambda errors. Configure SNS notifications:

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name smt-data-exporter-errors \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:my-topic
```

## Local Development

### Testing Locally

Use the provided test script:

```bash
# Set environment variables
source .env

# Run the Lambda function locally
python test_lambda_local.py
```

### Development Dependencies

```bash
pip install -r requirements-dev.txt  # If you create one
```

## Deployment Package Structure

The deployment package includes:
- `lambda_function.py` - Main Lambda handler
- `models.py` - Pydantic models for API responses
- `settings.py` - Configuration management
- Python dependencies (no pandas!)

## Troubleshooting

### Lambda Execution Errors

1. Check CloudWatch Logs:
   ```bash
   aws logs tail /aws/lambda/smt-data-exporter --follow
   ```

2. Verify environment variables:
   ```bash
   aws lambda get-function-configuration --function-name smt-data-exporter
   ```

3. Test credentials manually:
   ```bash
   python test_lambda_local.py
   ```

### Deployment Issues

1. Verify S3 bucket exists:
   ```bash
   aws s3 ls s3://your-deployment-bucket
   ```

2. Check IAM permissions for CloudFormation

3. Review CloudFormation stack events:
   ```bash
   aws cloudformation describe-stack-events --stack-name smt-data-exporter
   ```

## Updating the Function

To update the Lambda function code:

```bash
# Make your changes
# Then redeploy
./deploy.sh
```

CloudFormation will update the Lambda function with the new code.

## Cleanup

To remove all resources:

```bash
aws cloudformation delete-stack --stack-name smt-data-exporter
```

This will delete:
- Lambda function
- EventBridge rule
- IAM role
- CloudWatch log group
- CloudWatch alarm

Note: The S3 bucket and deployment package are not automatically deleted.

## Cost Estimation

Approximate AWS costs (as of 2025):
- **Lambda**: ~$0.00 per month (free tier: 1M requests, 400K GB-seconds)
- **CloudWatch Logs**: ~$0.50-$1.00 per month (depends on log volume)
- **EventBridge**: $0.00 (free for scheduled rules)
- **S3**: Negligible (< $0.01 for deployment package)

**Total estimated cost: < $1.00/month**

## Security

- **Credentials**: Stored as encrypted Lambda environment variables
- **IAM**: Least-privilege execution role
- **No hardcoded secrets**: All sensitive data from environment
- **HTTPS**: All API calls use TLS/SSL

## Migration from Docker

If migrating from the Docker version:

1. The Lambda function does **not** use file-based export markers
2. EventBridge scheduler replaces cron jobs
3. No local data directory - state is managed via execution frequency
4. Environment variables work the same way

## Contributing

Feel free to submit issues or pull requests!

## License

MIT

## Author

Noah Guillory
