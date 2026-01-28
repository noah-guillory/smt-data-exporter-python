#!/bin/bash
set -e

# Configuration
STACK_NAME="${STACK_NAME:-smt-data-exporter}"
AWS_REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET="${S3_BUCKET}"  # S3 bucket for Lambda deployment package
PYTHON_VERSION="python3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if S3 bucket is provided
if [ -z "$S3_BUCKET" ]; then
    print_error "S3_BUCKET environment variable is required for deployment"
    echo "Usage: S3_BUCKET=my-deployment-bucket ./deploy.sh"
    exit 1
fi

# Check required environment variables for Lambda configuration
REQUIRED_VARS=("SMT_USERNAME" "SMT_PASSWORD" "YNAB_ACCESS_TOKEN" "YNAB_BUDGET_ID" "YNAB_CATEGORY_ID" "KWH_RATE")
missing_vars=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "The following required environment variables are not set:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please set these variables before deploying:"
    echo "export SMT_USERNAME='your_username'"
    echo "export SMT_PASSWORD='your_password'"
    echo "export YNAB_ACCESS_TOKEN='your_token'"
    echo "export YNAB_BUDGET_ID='your_budget_id'"
    echo "export YNAB_CATEGORY_ID='your_category_id'"
    echo "export KWH_RATE='0.17754'"
    echo "export HEALTHCHECK_URL='https://hc-ping.com/your-uuid' # Optional"
    exit 1
fi

print_info "Starting deployment process..."

# Create build directory
BUILD_DIR="build"
PACKAGE_DIR="$BUILD_DIR/package"
rm -rf "$BUILD_DIR"
mkdir -p "$PACKAGE_DIR"

print_info "Installing Python dependencies..."
pip install --target "$PACKAGE_DIR" --upgrade \
    certifi \
    pydantic \
    pydantic-settings \
    pyopenssl \
    smart-meter-texas \
    ynab

# Copy Lambda function and supporting files
print_info "Copying Lambda function code..."
cp lambda_function.py "$PACKAGE_DIR/"
cp models.py "$PACKAGE_DIR/"
cp settings.py "$PACKAGE_DIR/"

# Create deployment package
print_info "Creating deployment package..."
cd "$PACKAGE_DIR"
zip -r ../lambda-deployment.zip . -q
cd ../../

print_info "Deployment package created: $BUILD_DIR/lambda-deployment.zip"
PACKAGE_SIZE=$(du -h "$BUILD_DIR/lambda-deployment.zip" | cut -f1)
print_info "Package size: $PACKAGE_SIZE"

# Upload to S3
print_info "Uploading deployment package to S3..."
aws s3 cp "$BUILD_DIR/lambda-deployment.zip" "s3://$S3_BUCKET/lambda-deployment.zip"

# Deploy CloudFormation stack
print_info "Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file cloudformation.yaml \
    --stack-name "$STACK_NAME" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        S3Bucket="$S3_BUCKET" \
        S3Key="lambda-deployment.zip" \
        SmtUsername="$SMT_USERNAME" \
        SmtPassword="$SMT_PASSWORD" \
        YnabAccessToken="$YNAB_ACCESS_TOKEN" \
        YnabBudgetId="$YNAB_BUDGET_ID" \
        YnabCategoryId="$YNAB_CATEGORY_ID" \
        KwhRate="$KWH_RATE" \
        HealthcheckUrl="${HEALTHCHECK_URL:-}" \
    --region "$AWS_REGION"

# Get stack outputs
print_info "Deployment complete! Getting stack outputs..."
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs' \
    --output table

print_info "Lambda function deployed successfully!"
print_info "The function will run on the configured schedule (default: monthly on the 1st at 2 AM UTC)"
