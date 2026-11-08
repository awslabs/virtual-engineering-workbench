import { Construct } from 'constructs';
import {
  aws_lambda_nodejs as lambda_node,
  aws_iam as iam,
  aws_lambda as lambda,
  Aws,
  Duration,
  custom_resources
} from 'aws-cdk-lib';
import { NagSuppressions } from 'cdk-nag';

export class LambdaEdgeMonitoring extends Construct {

  public readonly serviceToken: string;

  constructor(scope: Construct, id: string, props: {
    formatResourceName: (resourceName: string) => string,
  }) {
    super(scope, id);

    const lambdaManagedPolicy = new iam.ManagedPolicy(this, 'cw-group-upsert-policy', {
      managedPolicyName: 'LambdaEdgeMonitoringPolicy',
      description: 'Grants permissions to configure cross regional monitoring for Lambda@Edge',
      path: '/VirtualWorkbench/',
      statements: [
        // ec2:DescribeRegions is a list-style action with no resource-level support.
        new iam.PolicyStatement({
          actions: ['ec2:DescribeRegions'],
          resources: ['*'],
        }),
        // Lambda actions target the destination Lambda passed as a custom-resource
        // property. That Lambda is deployed by this stack and always carries the
        // VEW resource-name prefix. Scope to any Lambda function with the VEW prefix
        // in this account, across all regions (Lambda@Edge log processing is
        // multi-region).
        new iam.PolicyStatement({
          actions: [
            'lambda:AddPermission',
            'lambda:GetPolicy',
          ],
          resources: [
            `arn:${Aws.PARTITION}:lambda:*:${Aws.ACCOUNT_ID}:function:${props.formatResourceName('*')}`,
          ],
        }),
        // CloudWatch Logs actions target the log group carried in the custom
        // resource properties. Log group names follow the /aws/lambda/{region}.{fn}
        // pattern; scope to any VEW-prefixed CW log group in this account.
        new iam.PolicyStatement({
          actions: [
            'logs:CreateLogGroup',
            'logs:DeleteSubscriptionFilter',
            'logs:DescribeLogGroups',
            'logs:DescribeSubscriptionFilters',
            'logs:PutSubscriptionFilter',
          ],
          resources: [
            `arn:${Aws.PARTITION}:logs:*:${Aws.ACCOUNT_ID}:log-group:/aws/lambda/*.${props.formatResourceName('*')}:*`,
            `arn:${Aws.PARTITION}:logs:*:${Aws.ACCOUNT_ID}:log-group:/aws/lambda/*.${props.formatResourceName('*')}`,
          ],
        }),
        // iam:PassRole is deliberately absent: the handler in
        // lambda-edge-monitoring.handler.ts invokes no AWS API that requires it.
        // CloudWatch Logs invokes the destination Lambda under its own principal,
        // through the resource policy set with lambda:AddPermission.
      ]
    });

    const role = new iam.Role(this, 'cw-group-role', {
      roleName: 'LambdaEdgeMonitoringCustomResource',
      path: '/VirtualWorkbench/',
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        lambdaManagedPolicy,
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
      ]
    });

    const func = new lambda_node.NodejsFunction(this, 'handler', {
      runtime: lambda.Runtime.NODEJS_24_X,
      timeout: Duration.seconds(30),
      memorySize: 256,
      reservedConcurrentExecutions: 1,
      functionName: props.formatResourceName('lambda-edge-monitor-cfg'),
      description: 'Custom resource to configure Lambda@Edge monitoring in all regions.',
      role,
      environment: {
        // eslint-disable-next-line @typescript-eslint/naming-convention
        LOG_LEVEL: 'DEBUG',
      }
    });


    const serviceProviderRole = new iam.Role(this, 'service-provider-role', {
      roleName: 'LambdaEdgeMonitoringServiceProvider',
      path: '/VirtualWorkbench/',
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
      ]
    });

    const cwLogGroupUpsertProvider = new custom_resources.Provider(this, 'cw-logs-upsert-provider', {
      onEventHandler: func,
      role: serviceProviderRole,
    });

    this.serviceToken = cwLogGroupUpsertProvider.serviceToken;

    NagSuppressions.addResourceSuppressions(lambdaManagedPolicy, [{
      id: 'AwsSolutions-IAM5',
      reason: 'Function needs to create or read arbitrary CW log groups.'
    }], true);

    NagSuppressions.addResourceSuppressions(func, [{
      id: 'AwsSolutions-IAM4',
      reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.'
    }, {
      id: 'NIST.800.53.R4-LambdaInsideVPC',
      reason: 'Lambdas are not deployed to VPC.'
    }, {
      id: 'NIST.800.53.R5-LambdaDLQ',
      reason: 'Lambda ys synchronous and does not require DLQ.'
    }, {
      id: 'NIST.800.53.R5-LambdaInsideVPC',
      reason: 'Lambdas are not deployed to VPC.'
    }], true);

    NagSuppressions.addResourceSuppressions(role, [{
      id: 'AwsSolutions-IAM4',
      reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.'
    }, {
      id: 'AwsSolutions-IAM5',
      reason: 'Function needs to create or read arbitrary CW log groups.'
    }, {
      id: 'NIST.800.53.R4-IAMNoInlinePolicy',
      reason: 'Role has no inline policies defined.'
    }, {
      id: 'NIST.800.53.R5-IAMNoInlinePolicy',
      reason: 'Role has no inline policies defined.'
    }], true);

    NagSuppressions.addResourceSuppressions(serviceProviderRole, [{
      id: 'AwsSolutions-IAM4',
      reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.'
    }, {
      id: 'AwsSolutions-IAM5',
      reason: 'Function needs to create or read arbitrary CW log groups.'
    }, {
      id: 'NIST.800.53.R4-IAMNoInlinePolicy',
      reason: 'Role has no inline policies defined.'
    }, {
      id: 'NIST.800.53.R5-IAMNoInlinePolicy',
      reason: 'Role has no inline policies defined.'
    }], true);

    NagSuppressions.addResourceSuppressions(cwLogGroupUpsertProvider, [{
      id: 'AwsSolutions-IAM4',
      reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.'
    }, {
      id: 'NIST.800.53.R4-LambdaInsideVPC',
      reason: 'Lambdas are not deployed to VPC.'
    }, {
      id: 'NIST.800.53.R5-LambdaDLQ',
      reason: 'Lambda is triggeted by a schedule and does not need a DLQ.'
    }, {
      id: 'NIST.800.53.R5-LambdaInsideVPC',
      reason: 'Lambdas are not deployed to VPC.'
    }, {
      id: 'AwsSolutions-IAM5',
      reason: 'Function needs to create or read arbitrary CW log groups.'
    }, {
      id: 'AwsSolutions-L1',
      reason: 'Code is autogenerated by CDK and does not support latest Node.js runtime.'
    }, {
      id: 'NIST.800.53.R5-LambdaConcurrency',
      reason: 'Code is autogenerated by CDK and does not configure reserved concurrency.'
    }], true);

  }
}
