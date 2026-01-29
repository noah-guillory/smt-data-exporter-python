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
    echo "Usage: S3_BUCKET=my-deployment-bucket ./cdk-deploy.sh"
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

print_info "Starting CDK deployment process..."

# Get the project root directory (parent of cdk directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create build directory in project root
BUILD_DIR="$PROJECT_ROOT/build"
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
cp "$PROJECT_ROOT/lambda_function.py" "$PACKAGE_DIR/"
cp "$PROJECT_ROOT/models.py" "$PACKAGE_DIR/"
cp "$PROJECT_ROOT/settings.py" "$PACKAGE_DIR/"

# Create deployment package
print_info "Creating deployment package..."
cd "$PACKAGE_DIR"
zip -r ../lambda-deployment.zip . -q
cd "$PROJECT_ROOT"

print_info "Deployment package created: $BUILD_DIR/lambda-deployment.zip"
PACKAGE_SIZE=$(du -h "$BUILD_DIR/lambda-deployment.zip" | cut -f1)
print_info "Package size: $PACKAGE_SIZE"

# Upload to S3
print_info "Uploading deployment package to S3..."
aws s3 cp "$BUILD_DIR/lambda-deployment.zip" "s3://$S3_BUCKET/lambda-deployment.zip"

# Install CDK dependencies if not already installed
if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    print_info "Installing CDK dependencies..."
    cd "$SCRIPT_DIR"
    npm install
    cd "$PROJECT_ROOT"
fi

# Build CDK TypeScript code
print_info "Building CDK application..."
cd "$SCRIPT_DIR"
npm run build

# Bootstrap CDK if needed (first time only)
print_info "Ensuring CDK is bootstrapped..."
cdk bootstrap aws://unknown-account/$AWS_REGION || true

# Deploy CDK stack
print_info "Deploying CDK stack..."
cdk deploy \
    --require-approval never \
    --context stackName="$STACK_NAME" \
    --context awsRegion="$AWS_REGION" \
    --context s3Bucket="$S3_BUCKET" \
    --context s3Key="lambda-deployment.zip" \
    --context smtUsername="$SMT_USERNAME" \
    --context smtPassword="$SMT_PASSWORD" \
    --context ynabAccessToken="$YNAB_ACCESS_TOKEN" \
    --context ynabBudgetId="$YNAB_BUDGET_ID" \
    --context ynabCategoryId="$YNAB_CATEGORY_ID" \
    --context kwhRate="$KWH_RATE" \
    --context healthcheckUrl="${HEALTHCHECK_URL:-}" \
    --context scheduleExpression="${SCHEDULE_EXPRESSION:-cron(0 2 1 * ? *)}" \
    --context lambdaTimeout="${LAMBDA_TIMEOUT:-300}" \
    --context lambdaMemorySize="${LAMBDA_MEMORY_SIZE:-256}"

cd "$PROJECT_ROOT"

print_info "Deployment complete!"
print_info "Lambda function deployed successfully!"
print_info "The function will run on the configured schedule (default: monthly on the 1st at 2 AM UTC)"
