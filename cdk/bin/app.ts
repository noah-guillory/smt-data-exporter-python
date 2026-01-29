#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

/**
 * Properties for the SmtDataExporterStack
 */
export interface SmtDataExporterStackProps extends cdk.StackProps {
  /**
   * S3 bucket containing the Lambda deployment package
   */
  s3Bucket: string;

  /**
   * S3 key for the Lambda deployment package
   * @default 'lambda-deployment.zip'
   */
  s3Key?: string;

  /**
   * Smart Meter Texas username
   */
  smtUsername: string;

  /**
   * Smart Meter Texas password
   */
  smtPassword: string;

  /**
   * YNAB API access token
   */
  ynabAccessToken: string;

  /**
   * YNAB budget ID
   */
  ynabBudgetId: string;

  /**
   * YNAB category ID for electric bill
   */
  ynabCategoryId: string;

  /**
   * Cost per kWh (e.g., 0.17754)
   * @default '0.17754'
   */
  kwhRate?: string;

  /**
   * Optional healthcheck URL (e.g., https://hc-ping.com/uuid)
   * @default undefined
   */
  healthcheckUrl?: string;

  /**
   * EventBridge schedule expression
   * @default 'cron(0 2 1 * ? *)' - Monthly on the 1st at 2 AM UTC
   */
  scheduleExpression?: string;

  /**
   * Lambda function timeout in seconds
   * @default 300
   */
  lambdaTimeout?: number;

  /**
   * Lambda function memory in MB
   * @default 256
   */
  lambdaMemorySize?: number;
}

/**
 * CDK Stack for SMT Data Exporter Lambda Function
 * 
 * This stack reproduces the CloudFormation template for deploying a Lambda function
 * that exports Smart Meter Texas data and updates YNAB electric bill targets.
 */
export class SmtDataExporterStack extends cdk.Stack {
  public readonly lambdaFunction: lambda.Function;
  public readonly scheduledRule: events.Rule;
  public readonly logGroup: logs.LogGroup;

  constructor(scope: Construct, id: string, props: SmtDataExporterStackProps) {
    super(scope, id, props);

    // Get S3 bucket reference
    const bucket = s3.Bucket.fromBucketName(this, 'DeploymentBucket', props.s3Bucket);

    // Lambda Execution Role
    const lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    cdk.Tags.of(lambdaExecutionRole).add('Application', 'SMT-Data-Exporter');

    // CloudWatch Log Group
    this.logGroup = new logs.LogGroup(this, 'LambdaLogGroup', {
      logGroupName: '/aws/lambda/smt-data-exporter',
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Build environment variables
    const environment: { [key: string]: string } = {
      SMT_USERNAME: props.smtUsername,
      SMT_PASSWORD: props.smtPassword,
      YNAB_ACCESS_TOKEN: props.ynabAccessToken,
      YNAB_BUDGET_ID: props.ynabBudgetId,
      YNAB_CATEGORY_ID: props.ynabCategoryId,
      KWH_RATE: props.kwhRate ?? '0.17754',
    };

    if (props.healthcheckUrl) {
      environment.HEALTHCHECK_URL = props.healthcheckUrl;
    }

    // Lambda Function
    this.lambdaFunction = new lambda.Function(this, 'LambdaFunction', {
      functionName: 'smt-data-exporter',
      description: 'Exports Smart Meter Texas data and updates YNAB electric bill target',
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_function.lambda_handler',
      role: lambdaExecutionRole,
      code: lambda.Code.fromBucket(bucket, props.s3Key ?? 'lambda-deployment.zip'),
      timeout: cdk.Duration.seconds(props.lambdaTimeout ?? 300),
      memorySize: props.lambdaMemorySize ?? 256,
      environment,
      logGroup: this.logGroup,
    });

    cdk.Tags.of(this.lambdaFunction).add('Application', 'SMT-Data-Exporter');

    // EventBridge Rule
    this.scheduledRule = new events.Rule(this, 'ScheduledRule', {
      ruleName: 'smt-data-exporter-schedule',
      description: 'Trigger SMT data export on a schedule',
      schedule: events.Schedule.expression(props.scheduleExpression ?? 'cron(0 2 1 * ? *)'),
      enabled: true,
    });

    this.scheduledRule.addTarget(new targets.LambdaFunction(this.lambdaFunction));

    // CloudWatch Alarm for Lambda Errors
    new cloudwatch.Alarm(this, 'LambdaErrorAlarm', {
      alarmName: 'smt-data-exporter-errors',
      alarmDescription: 'Alert when Lambda function has errors',
      metric: this.lambdaFunction.metricErrors({
        period: cdk.Duration.seconds(300),
        statistic: 'Sum',
      }),
      evaluationPeriods: 1,
      threshold: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    // Outputs
    new cdk.CfnOutput(this, 'LambdaFunctionArn', {
      description: 'ARN of the Lambda function',
      value: this.lambdaFunction.functionArn,
      exportName: `${this.stackName}-LambdaFunctionArn`,
    });

    new cdk.CfnOutput(this, 'LambdaFunctionName', {
      description: 'Name of the Lambda function',
      value: this.lambdaFunction.functionName,
      exportName: `${this.stackName}-LambdaFunctionName`,
    });

    new cdk.CfnOutput(this, 'ScheduledRuleArn', {
      description: 'ARN of the EventBridge scheduled rule',
      value: this.scheduledRule.ruleArn,
      exportName: `${this.stackName}-ScheduledRuleArn`,
    });

    new cdk.CfnOutput(this, 'LogGroupName', {
      description: 'Name of the CloudWatch Log Group',
      value: this.logGroup.logGroupName,
      exportName: `${this.stackName}-LogGroupName`,
    });

    new cdk.CfnOutput(this, 'ScheduleExpression', {
      description: 'Schedule expression for the EventBridge rule',
      value: props.scheduleExpression ?? 'cron(0 2 1 * ? *)',
    });
  }
}

/**
 * Main CDK App
 */
const app = new cdk.App();

// Get configuration from CDK context or environment variables
const stackName = app.node.tryGetContext('stackName') || process.env.STACK_NAME || 'smt-data-exporter';
const awsRegion = app.node.tryGetContext('awsRegion') || process.env.AWS_REGION || 'us-east-1';
const s3Bucket = app.node.tryGetContext('s3Bucket') || process.env.S3_BUCKET;
const s3Key = app.node.tryGetContext('s3Key') || process.env.S3_KEY || 'lambda-deployment.zip';
const smtUsername = app.node.tryGetContext('smtUsername') || process.env.SMT_USERNAME;
const smtPassword = app.node.tryGetContext('smtPassword') || process.env.SMT_PASSWORD;
const ynabAccessToken = app.node.tryGetContext('ynabAccessToken') || process.env.YNAB_ACCESS_TOKEN;
const ynabBudgetId = app.node.tryGetContext('ynabBudgetId') || process.env.YNAB_BUDGET_ID;
const ynabCategoryId = app.node.tryGetContext('ynabCategoryId') || process.env.YNAB_CATEGORY_ID;
const kwhRate = app.node.tryGetContext('kwhRate') || process.env.KWH_RATE || '0.17754';
const healthcheckUrl = app.node.tryGetContext('healthcheckUrl') || process.env.HEALTHCHECK_URL;
const scheduleExpression = app.node.tryGetContext('scheduleExpression') || process.env.SCHEDULE_EXPRESSION || 'cron(0 2 1 * ? *)';
const lambdaTimeout = parseInt(app.node.tryGetContext('lambdaTimeout') || process.env.LAMBDA_TIMEOUT || '300');
const lambdaMemorySize = parseInt(app.node.tryGetContext('lambdaMemorySize') || process.env.LAMBDA_MEMORY_SIZE || '256');

// Validate numeric parameters
if (isNaN(lambdaTimeout) || lambdaTimeout < 60 || lambdaTimeout > 900) {
  throw new Error('LAMBDA_TIMEOUT must be a valid number between 60 and 900 seconds');
}
if (isNaN(lambdaMemorySize) || lambdaMemorySize < 128 || lambdaMemorySize > 10240) {
  throw new Error('LAMBDA_MEMORY_SIZE must be a valid number between 128 and 10240 MB');
}

// Validate required parameters
if (!s3Bucket) {
  throw new Error('S3_BUCKET environment variable or context parameter is required');
}
if (!smtUsername) {
  throw new Error('SMT_USERNAME environment variable or context parameter is required');
}
if (!smtPassword) {
  throw new Error('SMT_PASSWORD environment variable or context parameter is required');
}
if (!ynabAccessToken) {
  throw new Error('YNAB_ACCESS_TOKEN environment variable or context parameter is required');
}
if (!ynabBudgetId) {
  throw new Error('YNAB_BUDGET_ID environment variable or context parameter is required');
}
if (!ynabCategoryId) {
  throw new Error('YNAB_CATEGORY_ID environment variable or context parameter is required');
}

// Create the stack
new SmtDataExporterStack(app, stackName, {
  env: {
    region: awsRegion,
  },
  description: 'Smart Meter Texas Data Exporter Lambda Function with EventBridge Scheduler',
  s3Bucket,
  s3Key,
  smtUsername,
  smtPassword,
  ynabAccessToken,
  ynabBudgetId,
  ynabCategoryId,
  kwhRate,
  healthcheckUrl,
  scheduleExpression,
  lambdaTimeout,
  lambdaMemorySize,
});

app.synth();
