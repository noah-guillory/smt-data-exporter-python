# SMT Data Exporter - AWS CDK (TypeScript)

## Overview
This AWS CDK application provides a TypeScript-based infrastructure-as-code solution for deploying the SMT Data Exporter Lambda function. It reproduces the functionality of the original `cloudformation.yaml` template using AWS CDK constructs.

## Features
- **TypeScript-based CDK Application**: Type-safe infrastructure definition
- **Reproduces CloudFormation Template**: Maintains feature parity with the original template
- **AWS Lambda Function**: Serverless execution with EventBridge scheduled triggers
- **CloudFormation Infrastructure**: Complete infrastructure-as-code deployment
- **Smart Meter Texas API**: Secure, reliable data access
- **YNAB Integration**: Automatically updates your electric bill category target
- **Monitoring**: CloudWatch logs and alarms for error tracking

## Architecture

The CDK stack creates:
- **Lambda Function**: Python 3.11 runtime processing Smart Meter Texas data
- **EventBridge Rule**: Scheduled trigger (default: monthly on the 1st at 2 AM UTC)
- **IAM Role**: Least-privilege execution role for Lambda
- **CloudWatch Logs**: Centralized logging with 30-day retention
- **CloudWatch Alarm**: Alert on Lambda execution errors

## Prerequisites

1. **Node.js and npm**: Required for CDK
   ```bash
   node --version  # Should be v18+ or higher
   npm --version
   ```

2. **AWS CDK CLI**: Install globally
   ```bash
   npm install -g aws-cdk
   ```

3. **AWS Account** with appropriate permissions to create:
   - Lambda functions
   - IAM roles
   - EventBridge rules
   - CloudWatch resources
   - S3 buckets

4. **AWS CLI** configured with credentials:
   ```bash
   aws configure
   ```

5. **S3 Bucket** for Lambda deployment package:
   ```bash
   aws s3 mb s3://your-deployment-bucket
   ```

6. **Smart Meter Texas Account** credentials

7. **YNAB Account** with:
   - Personal Access Token
   - Budget ID
   - Category ID for electric bill

## Quick Start

### 1. Install CDK Dependencies

```bash
cd cdk
npm install
```

### 2. Set Environment Variables

Create a `.env` file in the project root or export variables:

```bash
export S3_BUCKET="your-deployment-bucket"
export AWS_REGION="us-east-1"
export STACK_NAME="smt-data-exporter"
export SMT_USERNAME="your_smt_username"
export SMT_PASSWORD="your_smt_password"
export YNAB_ACCESS_TOKEN="your_ynab_token"
export YNAB_BUDGET_ID="your_budget_id"
export YNAB_CATEGORY_ID="your_category_id"
export KWH_RATE="0.17754"
export HEALTHCHECK_URL="https://hc-ping.com/your-uuid"  # Optional
```

### 3. Deploy Using CDK

```bash
cd cdk
./cdk-deploy.sh
```

The deployment script will:
1. Install Python dependencies
2. Create Lambda deployment package
3. Upload to S3
4. Build TypeScript CDK code
5. Bootstrap CDK (if needed)
6. Deploy the CDK stack

### 4. Alternative: Manual CDK Deployment

If you prefer to run CDK commands manually:

```bash
# Build the TypeScript code
cd cdk
npm run build

# Synthesize CloudFormation template (optional - to preview)
npm run synth

# Deploy the stack
npm run deploy
```

## CDK Commands

From the `cdk` directory:

```bash
# Install dependencies
npm install

# Build TypeScript code
npm run build

# Watch for changes and rebuild
npm run watch

# Synthesize CloudFormation template
npm run synth

# Show diff between deployed stack and current state
npm run diff

# Deploy the stack
npm run deploy

# Destroy the stack
npm run destroy
```

## Configuration

### Stack Parameters

All parameters can be set via environment variables or CDK context:

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| Stack Name | `STACK_NAME` | `smt-data-exporter` | CloudFormation stack name |
| AWS Region | `AWS_REGION` | `us-east-1` | AWS region for deployment |
| S3 Bucket | `S3_BUCKET` | (required) | S3 bucket for Lambda package |
| S3 Key | `S3_KEY` | `lambda-deployment.zip` | S3 key for Lambda package |
| SMT Username | `SMT_USERNAME` | (required) | Smart Meter Texas username |
| SMT Password | `SMT_PASSWORD` | (required) | Smart Meter Texas password |
| YNAB Token | `YNAB_ACCESS_TOKEN` | (required) | YNAB API access token |
| YNAB Budget ID | `YNAB_BUDGET_ID` | (required) | YNAB budget ID |
| YNAB Category ID | `YNAB_CATEGORY_ID` | (required) | YNAB category ID |
| kWh Rate | `KWH_RATE` | `0.17754` | Cost per kWh |
| Healthcheck URL | `HEALTHCHECK_URL` | (optional) | Healthcheck ping URL |
| Schedule | `SCHEDULE_EXPRESSION` | `cron(0 2 1 * ? *)` | EventBridge schedule |
| Lambda Timeout | `LAMBDA_TIMEOUT` | `300` | Function timeout (seconds) |
| Lambda Memory | `LAMBDA_MEMORY_SIZE` | `256` | Function memory (MB) |

### Schedule Expression

Customize the EventBridge schedule:

```bash
# Run daily at 3 AM UTC
export SCHEDULE_EXPRESSION="cron(0 3 * * ? *)"

# Run every 7 days
export SCHEDULE_EXPRESSION="rate(7 days)"

# Monthly on 1st at 2 AM UTC (default)
export SCHEDULE_EXPRESSION="cron(0 2 1 * ? *)"
```

## Synthesizing CloudFormation Template

To generate the CloudFormation template without deploying:

```bash
cd cdk
npm run synth
```

This will output the CloudFormation template to `cdk.out/` and display it in the terminal.

## Comparing with Original Template

To compare the CDK-generated template with the original:

```bash
cd cdk
npm run synth > generated-template.yaml
diff generated-template.yaml ../cloudformation.yaml
```

## Monitoring

### CloudWatch Logs

View logs:
```bash
aws logs tail /aws/lambda/smt-data-exporter --follow
```

### Stack Outputs

View stack outputs:
```bash
cdk deploy --outputs-file outputs.json
cat outputs.json
```

Or using AWS CLI:
```bash
aws cloudformation describe-stacks --stack-name smt-data-exporter --query 'Stacks[0].Outputs'
```

## Updating the Function

To update the Lambda function code:

1. Make your changes to the Python files
2. Run the deployment script again:
   ```bash
   cd cdk
   ./cdk-deploy.sh
   ```

CDK will detect changes and update only what's necessary.

## Cleanup

To remove all resources:

```bash
cd cdk
npm run destroy
```

Or using AWS CLI:
```bash
aws cloudformation delete-stack --stack-name smt-data-exporter
```

Note: The S3 bucket and deployment package are not automatically deleted.

## Differences from CloudFormation Template

This CDK application provides the same functionality as the CloudFormation template with these benefits:

1. **Type Safety**: TypeScript provides compile-time type checking
2. **Better Abstractions**: CDK constructs provide higher-level abstractions
3. **Reusability**: Stack can be easily imported and reused in other projects
4. **Testing**: Can write unit tests for infrastructure code
5. **IDE Support**: Better autocomplete and inline documentation

## Project Structure

```
cdk/
├── bin/
│   └── app.ts              # Main CDK application and stack definition
├── lib/                    # (Generated) Compiled JavaScript
├── node_modules/           # (Generated) Dependencies
├── cdk.out/               # (Generated) Synthesized CloudFormation
├── cdk.json               # CDK configuration
├── package.json           # Node.js dependencies
├── tsconfig.json          # TypeScript configuration
├── cdk-deploy.sh          # Deployment script
└── README.md              # This file
```

## Troubleshooting

### CDK Bootstrap Issues

If you encounter bootstrap issues:
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### TypeScript Compilation Errors

Ensure you have the latest dependencies:
```bash
cd cdk
npm install
npm run build
```

### Lambda Deployment Package Issues

If the Lambda function fails to deploy:
1. Check that the S3 bucket exists
2. Verify the deployment package was uploaded
3. Check CloudWatch logs for errors

## Cost Estimation

Approximate AWS costs (as of 2025):
- **Lambda**: ~$0.00 per month (free tier: 1M requests, 400K GB-seconds)
- **CloudWatch Logs**: ~$0.50-$1.00 per month (depends on log volume)
- **EventBridge**: $0.00 (free for scheduled rules)
- **S3**: Negligible (< $0.01 for deployment package)

**Total estimated cost: < $1.00/month**

## Migration from CloudFormation

To migrate from the original CloudFormation template to CDK:

1. Deploy the CDK stack with a different stack name first
2. Test thoroughly
3. Delete the old CloudFormation stack
4. Or: Update the existing stack by using the same stack name

## Contributing

Feel free to submit issues or pull requests!

## License

MIT

## Author

Noah Guillory
