// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Construct } from 'constructs';
import {
  aws_s3 as s3,
  aws_iam as iam,
  aws_ssm as ssm,
  Stack, RemovalPolicy,
  aws_certificatemanager as acm,
  aws_ec2 as ec2,
  aws_elasticloadbalancingv2 as albv2,
  aws_elasticloadbalancingv2_targets as albv2_targets,
  aws_elasticloadbalancingv2_actions as albv2_actions,
  custom_resources,
  aws_lambda_nodejs as lambda_nodejs,
  aws_lambda as lambda,
  aws_apigateway as apigateway,
  aws_logs as logs,
} from 'aws-cdk-lib';
import { WebUserPool } from './app-user-pool';
import { NagSuppressions } from 'cdk-nag';
import { AppConfig } from '../app-config';

/* eslint @typescript-eslint/naming-convention: "off" */

enum PrivateIPAddressRange {
  ClassA = '10.0.0.0/8',
  ClassB = '172.16.0.0/12',
  ClassC = '192.168.0.0/16',
}

export interface AppElbCustomDomainOption {
  customDomains?: string[],
  cert?: acm.ICertificate,
}

const TEST_ENVIRONMENTS = new Set<string>(['dev', 'qa']);

export type IPPrefixList = { [key: string]: string };

declare global {
  interface Array<T> {
    pushIf(p: () => boolean, o: T): Array<T>,
  }
}

/* eslint no-extend-native: "off" */

Array.prototype.pushIf = function<T>(p: () => boolean, o: T) {
  if (p()) {
    this.push(o);
  }
  return this;
};

export class AppElb extends Construct {
  private readonly _appName: string;
  private readonly _appEnvironment: string;
  private readonly _domainName: string;
  private readonly _certificate: acm.ICertificate;
  private readonly _frontendS3Bucket: s3.Bucket;
  private readonly _accessLogBucket: s3.Bucket;
  private _customLogoutUrl: string;
  private _albTargetGroup: albv2.ApplicationTargetGroup;
  private _alb: albv2.ApplicationLoadBalancer;
  private _albListener: albv2.ApplicationListener;
  private _albLambdaTarget: lambda.Function;
  private _resourceName: (resourceName: string) => string;

  constructor(scope: Construct, id: string, props: {
    appName: string,
    appEnvironment: string,
    domainName: string,
    certificateArn: string,
    formatResourceName: (resourceName: string) => string,
  }) {
    super(scope, id);

    this._resourceName = props.formatResourceName;
    this._appName = props.appName;
    this._appEnvironment = props.appEnvironment;
    this._domainName = props.domainName;
    this._certificate = acm.Certificate.fromCertificateArn(this, 'Certificate', props.certificateArn);

    const stack = Stack.of(this);

    this._accessLogBucket = new s3.Bucket(this, 'access-log-bucket', {
      accessControl: s3.BucketAccessControl.LOG_DELIVERY_WRITE,
      bucketName: `${stack.stackName}-${stack.region}-${stack.account}-logs`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
    });

    NagSuppressions.addResourceSuppressions(this._accessLogBucket, [{
      id: 'NIST.800.53.R4-S3BucketDefaultLockEnabled',
      reason: 'No need to have object lock for CDN access logs.'
    }, {
      id: 'NIST.800.53.R4-S3BucketReplicationEnabled',
      reason: 'No need to have replication for CDN access logs.'
    }, {
      id: 'NIST.800.53.R4-S3BucketVersioningEnabled',
      reason: 'No need to have versioning for CDN access logs.'
    }, {
      id: 'NIST.800.53.R5-S3BucketReplicationEnabled',
      reason: 'No need to have replication for CDN access logs.'
    }, {
      id: 'NIST.800.53.R5-S3BucketVersioningEnabled',
      reason: 'No need to have versioning for CDN access logs.'
    }, {
      id: 'NIST.800.53.R5-S3DefaultEncryptionKMS',
      reason: 'Currently there is no requirement to use KMS customer managed keys.'
    }]);

    /* S3 bucket for react app CDN */
    this._frontendS3Bucket = new s3.Bucket(this, 'frontend-bucket', {
      accessControl: s3.BucketAccessControl.PRIVATE,
      bucketName: `${stack.stackName}-${stack.region}-${stack.account}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      serverAccessLogsBucket: this._accessLogBucket,
      serverAccessLogsPrefix: 'frontend-bucket/',
    });

    NagSuppressions.addResourceSuppressions(this._frontendS3Bucket, [{
      id: 'NIST.800.53.R4-S3BucketDefaultLockEnabled',
      reason: `Cannot set object lock for static content, as it would prevent
                uploading new web application versions.`
    }, {
      id: 'NIST.800.53.R4-S3BucketReplicationEnabled',
      reason: 'There is no need to replicate static WEB application content.'
    }, {
      id: 'NIST.800.53.R4-S3BucketVersioningEnabled',
      reason: 'No need to have versioning for static WEB application content.'
    }, {
      id: 'NIST.800.53.R5-S3BucketReplicationEnabled',
      reason: 'There is no need to replicate static WEB application content.'
    }, {
      id: 'NIST.800.53.R5-S3BucketVersioningEnabled',
      reason: 'No need to have versioning for static WEB application content.'
    }, {
      id: 'NIST.800.53.R5-S3DefaultEncryptionKMS',
      reason: 'CloudFront does not support KMS encrypted S3 buckets.'
    }]);
  }

  private _withALBValidation(appConfig: AppConfig) {
    if (!appConfig.vpcName) {
      throw new Error('VPC Name parameter (VPCName) is required when using ALB to serve the app');
    }
  }

  private _withALBCheckForCustomLogoutURL(appConfig: AppConfig) {
    if (appConfig.logoutUrl) {
      this._customLogoutUrl = appConfig.logoutUrl.replace(
        '{appDns}', `https://${appConfig.domainName || ''}`);
    }
  }

  withALB(appConfig: AppConfig): AppElb {
    this._withALBValidation(appConfig);
    this._withALBCheckForCustomLogoutURL(appConfig);

    const subnetSelector = ec2.SubnetFilter.byCidrRanges([PrivateIPAddressRange.ClassA]);

    const vpc = ec2.Vpc.fromLookup(this, 'vpc', { vpcName: appConfig.vpcName });

    vpc.addGatewayEndpoint('S3GatewayEndpoint', {
      service: ec2.GatewayVpcEndpointAwsService.S3
    });

    const vpcEndpointSecurityGroup = new ec2.SecurityGroup(this, 'S3EndpointSG', {
      allowAllOutbound: false,
      vpc,
      securityGroupName: this._resourceName('s3-sg')
    });

    const vpcEndpoint = vpc.addInterfaceEndpoint('S3InterfaceEndpoint', {
      securityGroups: [vpcEndpointSecurityGroup],
      service: ec2.InterfaceVpcEndpointAwsService.APIGATEWAY,
      subnets: {
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        subnetFilters: [subnetSelector]
      },
      privateDnsEnabled: false,
    });

    const vpcEndpointIps = new custom_resources.AwsCustomResource(
      this,
      'VPCEndpointIPs',
      {
        onUpdate: {
          action: 'describeNetworkInterfaces',
          parameters: {
            NetworkInterfaceIds: vpcEndpoint.vpcEndpointNetworkInterfaceIds,
          },
          outputPaths: vpc.selectSubnets({
            subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
            subnetFilters: [subnetSelector]
          }).subnets.map((_, i) => `NetworkInterfaces.${i}.PrivateIpAddress`),
          physicalResourceId: custom_resources.PhysicalResourceId.of('EndpointNics'),
          service: 'EC2'
        },
        policy: custom_resources.AwsCustomResourcePolicy.fromSdkCalls({
          resources: custom_resources.AwsCustomResourcePolicy.ANY_RESOURCE
        }
        ),
        functionName: this._resourceName('cf-sdk-eni-ip')
      }
    );

    NagSuppressions.addResourceSuppressions(vpcEndpointIps, [{
      id: 'AwsSolutions-IAM5',
      reason: 'ec2.DescribeNetworkInterfaces does not support resource restrictions'
    }, {
      id: 'NIST.800.53.R4-IAMNoInlinePolicy',
      reason: 'The inline IAM policy is auto-generated by CDK.'
    }, {
      id: 'NIST.800.53.R5-IAMNoInlinePolicy',
      reason: 'The inline IAM policy is auto-generated by CDK.'
    }], true);

    NagSuppressions.addResourceSuppressionsByPath(
      Stack.of(this),
      `/${Stack.of(this).node.path}/AWS679f53fac002430cb0da5b7982bd2287/Resource`,
      [{
        id: 'AwsSolutions-L1',
        reason: 'The Lambda function is managed by AWS CDK via the Custom Resources framework.'
      }, {
        id: 'NIST.800.53.R4-LambdaInsideVPC',
        reason: 'The Lambda function is managed by AWS CDK via the Custom Resources framework.'
      }, {
        id: 'NIST.800.53.R5-LambdaConcurrency',
        reason: 'The Lambda function is managed by AWS CDK via the Custom Resources framework.'
      }, {
        id: 'NIST.800.53.R5-LambdaDLQ',
        reason: 'The Lambda function is managed by AWS CDK via the Custom Resources framework.'
      }, {
        id: 'NIST.800.53.R5-LambdaInsideVPC',
        reason: 'The Lambda function is managed by AWS CDK via the Custom Resources framework.'
      }, {
        id: 'PCI.DSS.321-LambdaInsideVPC',
        reason: 'The Lambda function is managed by AWS CDK via the Custom Resources framework.'
      }, {
        id: 'AwsSolutions-IAM4',
        reason: 'The Lambda function is managed by AWS CDK via the Custom Resources framework.'
      }],
      true
    );

    const endpointIps = vpc.
      selectSubnets({
        subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        subnetFilters: [subnetSelector]
      }).
      subnets.
      map((_, i) => vpcEndpointIps.
        getResponseField(`NetworkInterfaces.${i}.PrivateIpAddress`)
      );

    const albSecurityGroup = new ec2.SecurityGroup(this, 'ALBSecurityGroup', {
      allowAllOutbound: false,
      vpc,
      securityGroupName: this._resourceName('alb-sg')
    });

    vpcEndpointSecurityGroup.addIngressRule(
      ec2.Peer.securityGroupId(albSecurityGroup.securityGroupId),
      ec2.Port.tcp(443),
      'Allow HTTPS traffic from ALB'
    );

    albSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(PrivateIPAddressRange.ClassA),
      ec2.Port.tcp(443),
      'Allow HTTPS traffic from Class A private IP space.'
    );
    albSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(PrivateIPAddressRange.ClassB),
      ec2.Port.tcp(443),
      'Allow HTTPS traffic from Class B private IP space.'
    );
    albSecurityGroup.addIngressRule(
      ec2.Peer.ipv4(PrivateIPAddressRange.ClassC),
      ec2.Port.tcp(443),
      'Allow HTTPS traffic from Class C private IP space.'
    );

    albSecurityGroup.addEgressRule(
      ec2.Peer.ipv4(vpc.vpcCidrBlock),
      ec2.Port.tcp(443),
      'Allow HTTPS traffic to this VPC.'
    );

    this._alb = new albv2.ApplicationLoadBalancer(
      this, 'ALB', {
        deletionProtection: false,
        dropInvalidHeaderFields: true,
        securityGroup: albSecurityGroup,
        vpc,
        vpcSubnets: {
          subnetFilters: [subnetSelector]
        },
        loadBalancerName: this._resourceName('alb')
      }
    );

    NagSuppressions.addResourceSuppressions(this._alb, [{
      id: 'NIST.800.53.R4-ALBWAFEnabled',
      reason: 'This is a private ALB.'
    }, {
      id: 'NIST.800.53.R5-ALBWAFEnabled',
      reason: 'This is a private ALB.'
    }], true);

    if (TEST_ENVIRONMENTS.has(this._appEnvironment)) {
      NagSuppressions.addResourceSuppressions(this._alb, [{
        id: 'NIST.800.53.R4-ELBDeletionProtectionEnabled',
        reason: 'Deletion protection disabled for test environments.'
      }, {
        id: 'NIST.800.53.R5-ELBDeletionProtectionEnabled',
        reason: 'Deletion protection disabled for test environments.'
      }], true);
    }

    this._alb.logAccessLogs(this._accessLogBucket, 'web-app-alb');

    this._albListener = this._alb.addListener(
      'ALBHttpsListener', {
        certificates: [this._certificate],
        open: false,
        port: 443,
        protocol: albv2.ApplicationProtocol.HTTPS,
      }
    );

    this._albTargetGroup = new albv2.ApplicationTargetGroup(
      this,
      'ALBTargetGroup', {
        healthCheck: {
          healthyHttpCodes: '200,403',
          path: '/',
          protocol: albv2.Protocol.HTTPS
        },
        port: 443,
        protocol: albv2.ApplicationProtocol.HTTPS,
        targetType: albv2.TargetType.IP,
        targets: endpointIps.map(ip => new albv2_targets.IpTarget(ip)),
        vpc,
        targetGroupName: this._resourceName('tg')
      }
    );

    this._albLambdaTarget = new lambda_nodejs.NodejsFunction(this, 'alb-target', {
      runtime: lambda.Runtime.NODEJS_24_X,
      environment: {
        APP_BUCKET_NAME: this._frontendS3Bucket.bucketName,
        DOMAIN_NAME: this._domainName,
        POWERTOOLS_LOG_LEVEL: 'INFO',
      },
      functionName: this._resourceName('cdn')
    });

    if (this._albLambdaTarget.role !== undefined) {
      NagSuppressions.addResourceSuppressions(this._albLambdaTarget.role, [{
        id: 'AwsSolutions-IAM4',
        reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.',
      }, {
        id: 'AwsSolutions-IAM5',
        reason: 's3:GetObject*, Action::s3:GetBucket*, s3:List* are autogenerated by CDK.',
      }], true);
    }

    this._frontendS3Bucket.grantRead(this._albLambdaTarget);

    this._albListener.addTargetGroups('AddALBTargetGroup', {
      targetGroups: [this._albTargetGroup]
    });

    NagSuppressions.addResourceSuppressions(this._albLambdaTarget, [{
      id: 'NIST.800.53.R4-LambdaInsideVPC',
      reason: 'Lambda@Edge does not support VPC configuration.',
    }, {
      id: 'NIST.800.53.R5-LambdaConcurrency',
      reason: 'Lambda@Edge does not support reserved concurrency.',
    }, {
      id: 'NIST.800.53.R5-LambdaDLQ',
      reason: 'Lambda@Edge does not support dead letter queues.',
    }, {
      id: 'NIST.800.53.R5-LambdaInsideVPC',
      reason: 'Lambda@Edge does not support VPC configuration.',
    }, {
      id: 'AwsSolutions-IAM4',
      reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.',
    }, {
      id: 'AwsSolutions-IAM5',
      reason: 's3:GetObject*, Action::s3:GetBucket*, s3:List* are autogenerated by CDK.',
    }, {
      id: 'NIST.800.53.R4-IAMNoInlinePolicy',
      reason: 's3:GetObject*, Action::s3:GetBucket*, s3:List* are autogenerated by CDK.',
    }, {
      id: 'NIST.800.53.R5-IAMNoInlinePolicy',
      reason: 's3:GetObject*, Action::s3:GetBucket*, s3:List* are autogenerated by CDK.',
    }], true);

    const accessLogGroup = new logs.LogGroup(
      this,
      'CDNAPIAccessLogGroup',
      {
        removalPolicy: RemovalPolicy.DESTROY,
        retention: logs.RetentionDays.TWO_MONTHS,
        logGroupName: this._resourceName('api-access-log')
      }
    );

    NagSuppressions.addResourceSuppressions(
      accessLogGroup,
      [{
        id: 'NIST.800.53.R4-CloudWatchLogGroupEncrypted',
        reason: 'Log group is encrypted with default master key.',
      }, {
        id: 'NIST.800.53.R5-CloudWatchLogGroupEncrypted',
        reason: 'Log group is encrypted with default master key.',
      }, {
        id: 'PCI.DSS.321-CloudWatchLogGroupEncrypted',
        reason: 'Log group is encrypted with default master key.',
      }]
    );

    const restApi = new apigateway.LambdaRestApi(this, 'StaticContentAPI', {
      restApiName: this._resourceName('cdn'),
      domainName: {
        domainName: this._domainName,
        certificate: this._certificate,
      },
      handler: this._albLambdaTarget,
      endpointTypes: [apigateway.EndpointType.PRIVATE],
      policy: new iam.PolicyDocument({
        statements: [
          new iam.PolicyStatement({
            actions: ['execute-api:Invoke'],
            conditions: {
              StringEquals: {
                'aws:sourceVpce': vpcEndpoint.vpcEndpointId
              }
            },
            resources: ['execute-api:/*'],
            principals: [new iam.AnyPrincipal()]
          })
        ]
      }),
      deployOptions: {
        accessLogDestination: new apigateway.LogGroupLogDestination(accessLogGroup),
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
        tracingEnabled: true,
      },
      binaryMediaTypes: ['*/*'],
      integrationOptions: {
        contentHandling: apigateway.ContentHandling.CONVERT_TO_BINARY,
      }
    });

    new apigateway.RequestValidator(this, 'ApiGWRequestValidator', {
      restApi: restApi,
      requestValidatorName: 'requestValidatorName',
      validateRequestBody: true,
      validateRequestParameters: true,
    });

    NagSuppressions.addResourceSuppressions(
      restApi.deploymentStage,
      [{
        id: 'AwsSolutions-APIG3',
        reason: 'AWS WAFv2 is not configured as of yet since we do not know who will have access to the API.',
      },
      {
        id: 'NIST.800.53.R5-APIGWAssociatedWithWAF',
        reason: 'AWS WAFv2 is not configured as of yet since we do not know who will have access to the API.',
      },
      {
        id: 'PCI.DSS.321-APIGWAssociatedWithWAF',
        reason: 'AWS WAFv2 is not configured as of yet since we do not know who will have access to the API.',
      },
      {
        id: 'NIST.800.53.R5-APIGWSSLEnabled',
        reason: 'Stage is using the default SSL certificate.',
      },
      {
        id: 'PCI.DSS.321-APIGWSSLEnabled',
        reason: 'Stage is using the default SSL certificate.',
      },
      {
        id: 'NIST.800.53.R4-APIGWCacheEnabledAndEncrypted',
        reason: 'Cache for API is disabled.',
      },
      {
        id: 'NIST.800.53.R5-APIGWCacheEnabledAndEncrypted',
        reason: 'Cache for API is disabled.',
      },
      {
        id: 'PCI.DSS.321-APIGWCacheEnabledAndEncrypted',
        reason: 'Cache for API is disabled.',
      },
      ]
    );

    NagSuppressions.addResourceSuppressions(
      restApi,
      [{
        id: 'AwsSolutions-APIG4',
        reason: 'This is a private API. Auth logic is in the Lambda backend'
      }, {
        id: 'AwsSolutions-COG4',
        reason: 'This is a private API. Auth logic is in the Lambda backend',
      }],
      true,
    );

    NagSuppressions.addStackSuppressions(
      Stack.of(this),
      [{
        id: 'AwsSolutions-IAM4',
        reason: 'AmazonAPIGatewayPushToCloudWatchLogs is enough for API Gateway to write logs to CloudWatch.',
        appliesTo: [
          'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs'
        ],
      }]
    );

    return this;
  }

  private _withUserPoolInitCallbackUrls(): [string[], string[]] {
    const callbackUrls: string[] = [];
    const callbackUrlsLogout: string[] = [];
    if (TEST_ENVIRONMENTS.has(this._appEnvironment)) {
      callbackUrls.push(
        'http://localhost:3000'
      );
      callbackUrlsLogout.push(
        'http://localhost:3000'
      );
    }
    return [callbackUrls, callbackUrlsLogout];
  }

  withUserPool(userPool: WebUserPool): AppElb {

    /* Cognito web app client for Frontend */
    const [callbackUrls, callbackUrlsLogout] = this._withUserPoolInitCallbackUrls();
    callbackUrls.pushIf(() => !!this._domainName, `https://${this._domainName}`);
    callbackUrls.pushIf(() => !!this._alb, `https://${this._alb.loadBalancerDnsName}`);

    callbackUrlsLogout.pushIf(() => !!this._customLogoutUrl, this._customLogoutUrl);
    callbackUrlsLogout.pushIf(() => !!this._alb, `https://${this._alb.loadBalancerDnsName}/logout`);

    userPool.withWebAppClient(callbackUrls, callbackUrlsLogout);

    /* Create SSM parameters for Cognito User Pool configuration */
    new ssm.StringParameter(this, 'user-pool-id', {
      parameterName: `/${this._appName}-${this._appEnvironment}/user-pool-id`,
      stringValue: userPool.getUserPoolId(),
    });

    new ssm.StringParameter(this, 'user-pool-domain-prefix', {
      parameterName: `/${this._appName}-${this._appEnvironment}/user-pool-domain`,
      stringValue: this.getDNS(userPool),
    });

    new ssm.StringParameter(this, 'user-pool-client-id', {
      parameterName: `/${this._appName}-${this._appEnvironment}/user-pool-client-id`,
      stringValue: userPool.getUserPoolClientId(),
    });

    new ssm.StringParameter(this, 'user-pool-client-ids', {
      parameterName: `/${this._appName}-${this._appEnvironment}/user-pool-client-ids`,
      stringValue: userPool.getUserPoolClientIds().join(','),
    });

    this._albLambdaTarget.addEnvironment('USER_POOL_ID', userPool.getUserPoolId());
    this._albLambdaTarget.addEnvironment('USER_POOL_APP_ID', userPool.getUserPoolClientId());
    this._albLambdaTarget.addEnvironment('USER_POOL_DOMAIN', this.getDNS(userPool));

    return this;
  }

  getDomainName(): string {
    if (this._alb) {
      return this._alb.loadBalancerDnsName;
    }
    throw new Error('No CDN is configured.');
  }

  getCustomDomainName(): string | undefined {
    return this._domainName;
  }

  getBucketName(): string {
    return this._frontendS3Bucket.bucketName;
  }

  getCustomLogoutUrl(): string {
    if (this._customLogoutUrl) {
      return this._customLogoutUrl;
    } else if (this._alb) {
      return `https://${this._alb.loadBalancerDnsName}/logout`;
    }
    return 'n/a';
  }

  private getDNS(userPool: WebUserPool): string {
    let loginDNS = userPool.getUserPoolCustomLoginFQDN();
    if (!loginDNS) {
      loginDNS = userPool.getUserPoolLoginFQDN();
    }
    return loginDNS;
  }

}