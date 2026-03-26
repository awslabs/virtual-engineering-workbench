// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Construct } from 'constructs';
import {
  aws_s3 as s3,
  aws_cloudfront as cloudfront,
  aws_cloudfront_origins as origins,
  aws_lambda_nodejs as lambda_node,
  aws_ssm as ssm,
  aws_iam as iam,
  aws_lambda as lambda,
  Stack, RemovalPolicy, Duration, FileSystem,
  aws_certificatemanager as acm,
  CustomResource,
} from 'aws-cdk-lib';
import fs from 'fs';
import { WebUserPool } from './app-user-pool';
import { NagSuppressions } from 'cdk-nag';
import path from 'path';
import { AppConfig } from '../app-config';
import { LambdaEdgeMonitoring } from './cloudwatch/lambda-edge-monitoring';

/* eslint @typescript-eslint/naming-convention: "off" */

enum HttpStatus {
  OK = 200,
  Unauthorized = 403,
  NotFound = 404
}

export interface AppCdnCustomDomainOption {
  customDomains?: string[],
  cert?: acm.ICertificate,
}

const TEST_ENVIRONMENTS = new Set<string>(['dev', 'qa']);

export type IPPrefixList = { [key: string]: string };

export class AppCdn extends Construct {
  private readonly _appName: string;
  private readonly _appEnvironment: string;
  private readonly _frontendS3Bucket: s3.Bucket;
  private readonly _frontendErrorsS3Bucket: s3.Bucket;
  private readonly _accessLogBucket: s3.Bucket;
  private _lambdaAtEdge: lambda_node.NodejsFunction;
  private _lambdaAtEdgeVersion: lambda.Version;
  private _distribution: cloudfront.Distribution;
  private _domainName?: string;
  private _cfAclArn: string;
  private _customLogoutUrl: string;
  private _lambdaAtEdgeClientIp: lambda_node.NodejsFunction;
  private _lambdaAtEdgeVersionClientIp: lambda.Version;

  constructor(scope: Construct, id: string, props: {
    appName: string,
    appEnvironment: string,
  }) {
    super(scope, id);

    this._appName = props.appName;
    this._appEnvironment = props.appEnvironment;

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

    /* S3 bucket for VEW UI landing page */
    /* S3 bucket for custom error pages */
    this._frontendErrorsS3Bucket = new s3.Bucket(this, 'frontend-errors', {
      accessControl: s3.BucketAccessControl.PRIVATE,
      bucketName: `${stack.stackName}-errors-${stack.region}-${stack.account}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      serverAccessLogsBucket: this._accessLogBucket,
      serverAccessLogsPrefix: 'frontend-errors/',
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

    NagSuppressions.addResourceSuppressions(this._frontendErrorsS3Bucket, [{
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

  withLambdaProtection(): AppCdn {
    /*  
      Lambda@Edge to check for Cognito JWT in cookies 
      Lambda@Edge does not support environment variables, 
      so putting the environment name in a file dynamically... 
    */

    const jsonIndentSpaces = 4;
    fs.writeFileSync('./lib/constructs/app-cdn.auth-handler.config.json', JSON.stringify({
      AppName: `${this._appName}-${this._appEnvironment}`,
      LogLevel: TEST_ENVIRONMENTS.has(this._appEnvironment) ? 'debug' : 'info',
    }, null, jsonIndentSpaces));

    const assetHash = FileSystem.fingerprint(path.resolve(process.cwd(), 'lib'), {
      exclude: [
        'app-config.ts',
        'infrastructure-stack.ts',
        'constructs/app-cdn.ts',
        'constructs/app-user-pool.ts',
        'constructs/*.json',
        'constructs/__mocks__/*.json',
        'constructs/*.test.ts',
        'app-user-pool.post-authentication-trigger.ts',
      ]
    });
    const hashPrefix = assetHash.substring(0, 5);
    const defaultRefreshTokenTimeOutLambdaAtEdge = 5;
    this._lambdaAtEdge = new lambda_node.NodejsFunction(this, 'auth-handler', {
      runtime: lambda.Runtime.NODEJS_24_X,
      description: `Lambda@Edge to handle user authentication flow at CloudFront CDN. ${hashPrefix}`,
      bundling: {
        assetHash
      },
      timeout: Duration.seconds(defaultRefreshTokenTimeOutLambdaAtEdge),
    });

    this._lambdaAtEdgeVersion = new lambda.Version(this, `auth-handler-version-${hashPrefix}`, {
      lambda: this._lambdaAtEdge,
    });

    this._lambdaAtEdge.applyRemovalPolicy(RemovalPolicy.RETAIN);

    if (this._lambdaAtEdge.role !== undefined) {
      NagSuppressions.addResourceSuppressions(this._lambdaAtEdge.role, [{
        id: 'AwsSolutions-IAM4',
        reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.',
      }]);
    }

    NagSuppressions.addResourceSuppressions(this._lambdaAtEdge, [{
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
    }]);

    return this;
  }

  withLambdaMonitoring(): AppCdn {
    if (!this._lambdaAtEdge) {
      throw new Error('Lambda@Edge is not defined.');
    }

    const formatResourceName = (resource: string) => `${Stack.of(this).stackName}-${resource}`;

    const edgeLogProcessingLambda = new lambda_node.NodejsFunction(this, 'log-monitor-handler', {
      functionName: formatResourceName('log-monitor'),
      runtime: lambda.Runtime.NODEJS_24_X,
      description: 'Processes Lambda@Edge logs and produces metrics for suspicious activity.',
      timeout: Duration.seconds(5),
      environment: {
        POWERTOOLS_METRICS_NAMESPACE: 'VirtualEngineeringWorkbench',
        POWERTOOLS_SERVICE_NAME: 'CDNLambdaEdgeAuthorizer',
      }
    });

    const lambdaEdgeMonitorConfigurator = new LambdaEdgeMonitoring(this, 'lambda-at-edge-monitor', {
      formatResourceName,
    });

    const configuratorResource = new CustomResource(this, 'lambda-at-edge-monitor-cr', {
      serviceToken: lambdaEdgeMonitorConfigurator.serviceToken,
      properties: {
        LogGroupName: `/aws/lambda/${Stack.of(this).region}.${this._lambdaAtEdge.functionName}`,
        SubscriptionFilterName: formatResourceName('monitoring'),
        SubscriptionFilterDestinationArn: edgeLogProcessingLambda.functionArn,
        SubscriptionFilterPatterns: [
          'Unable to fetch tokens from grant code',
          'Unable to fetch tokens from refreshToken',
        ],
        AccountId: Stack.of(this).account,
      },
    });

    configuratorResource.node.addDependency(edgeLogProcessingLambda);

    if (edgeLogProcessingLambda.role !== undefined) {
      NagSuppressions.addResourceSuppressions(edgeLogProcessingLambda.role, [{
        id: 'AwsSolutions-IAM4',
        reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.',
      }]);
    }

    NagSuppressions.addResourceSuppressions(edgeLogProcessingLambda, [{
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
    }]);

    return this;
  }

  withLambdaClientIpHandler(): AppCdn {
    /*  
      Lambda@Edge to modify response to add client-ip
    */

    const assetHash = FileSystem.fingerprint(
      path.resolve(process.cwd(), 'lib/constructs/app-cdn.client-ip-handler.ts'));
    const hashPrefix = assetHash.substring(0, 5);

    this._lambdaAtEdgeClientIp = new lambda_node.NodejsFunction(this, 'client-ip-handler', {
      runtime: lambda.Runtime.NODEJS_24_X,
      description: `Lambda@Edge to add client-ip to the response headers. ${hashPrefix}`,
      bundling: {
        assetHash
      }
    });

    this._lambdaAtEdgeClientIp.applyRemovalPolicy(RemovalPolicy.RETAIN);

    this._lambdaAtEdgeVersionClientIp = new lambda.Version(this, `client-ip-handler-version-${hashPrefix}`, {
      lambda: this._lambdaAtEdgeClientIp,
    });

    if (this._lambdaAtEdgeClientIp.role !== undefined) {
      NagSuppressions.addResourceSuppressions(this._lambdaAtEdgeClientIp.role, [{
        id: 'AwsSolutions-IAM4',
        reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.',
      }]);
    }

    NagSuppressions.addResourceSuppressions(this._lambdaAtEdgeClientIp, [{
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
    }]);

    return this;
  }

  withWAF(cfAclArn: string): AppCdn {
    this._cfAclArn = cfAclArn;

    return this;
  }

  private _getCertificate(appConfig: AppConfig) {
    return appConfig.certArn ?
      acm.Certificate.fromCertificateArn(this, 'Certificate', appConfig.certArn)
      : undefined;
  }

  private _getDomainNames(appConfig: AppConfig) {
    return appConfig.domainName ? [appConfig.domainName] : undefined;
  }

  withCDN(appConfig: AppConfig): AppCdn {

    const certificate = this._getCertificate(appConfig);

    const domainNames = this._getDomainNames(appConfig);

    this._domainName = appConfig.domainName;

    /* CDN */
    const responseHeadersPolicy = new cloudfront.ResponseHeadersPolicy(
      this, 'frontend-distribution-response-headers', {
        responseHeadersPolicyName: `prevent-browser-cache-${this._appEnvironment}`,
        comment: 'Adds response headers to prevent browser from caching static web app content.',
        customHeadersBehavior: {
          customHeaders: [
            { header: 'Cache-Control', value: 'no-store, must-revalidate', override: true },
            { header: 'Pragma', value: 'no-cache', override: true },
            { header: 'Expires', value: '0', override: true },
          ],
        },
      });

    const appOriginWeb = origins.S3BucketOrigin.withOriginAccessControl(this._frontendS3Bucket);
    const errorsOrigin = origins.S3BucketOrigin.withOriginAccessControl(this._frontendErrorsS3Bucket);

    const defaultErrorResponseTTLSeconds = 10;
    this._distribution = new cloudfront.Distribution(this, 'frontend-distribution', {
      defaultBehavior: {
        origin: appOriginWeb,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD,
        compress: true,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED_FOR_UNCOMPRESSED_OBJECTS,
        edgeLambdas: [{
          eventType: cloudfront.LambdaEdgeEventType.VIEWER_REQUEST,
          functionVersion: this._lambdaAtEdgeVersion
        }],
        responseHeadersPolicy,
      },
      additionalBehaviors: {
        '/errors/*': {
          origin: errorsOrigin,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachedMethods: cloudfront.CachedMethods.CACHE_GET_HEAD,
          compress: true,
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED_FOR_UNCOMPRESSED_OBJECTS,
          edgeLambdas: [{
            eventType: cloudfront.LambdaEdgeEventType.ORIGIN_RESPONSE,
            functionVersion: this._lambdaAtEdgeVersionClientIp
          }],
          responseHeadersPolicy,
        },
      },
      httpVersion: cloudfront.HttpVersion.HTTP1_1,
      enableIpv6: false,
      defaultRootObject: 'index.html',
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      errorResponses: [{
        httpStatus: HttpStatus.NotFound,
        responseHttpStatus: HttpStatus.OK,
        responsePagePath: '/index.html',
        ttl: Duration.seconds(defaultErrorResponseTTLSeconds)
      }, {
        httpStatus: HttpStatus.Unauthorized,
        responseHttpStatus: HttpStatus.Unauthorized,
        responsePagePath: '/index.html',
        ttl: Duration.seconds(defaultErrorResponseTTLSeconds)
      }],
      webAclId: this._cfAclArn,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      logBucket: this._accessLogBucket,
      logFilePrefix: 'frontend-distribution/',
      certificate,
      domainNames,
    });

    for (const bucket of [this._frontendS3Bucket, this._frontendErrorsS3Bucket]) {

      const listBucketPermissions = new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['s3:ListBucket'],
        principals: [
          new iam.ServicePrincipal('cloudfront.amazonaws.com')
        ],
        resources: [
          bucket.bucketArn,
        ],
        conditions: {
          StringEquals: {
            'AWS:SourceArn': `arn:aws:cloudfront::${Stack.of(this).account}:distribution/${this._distribution.distributionId}`
          }
        }
      });

      bucket.addToResourcePolicy(listBucketPermissions);
    }

    if (appConfig.logoutUrl) {
      this._customLogoutUrl = appConfig.logoutUrl.replace(
        '{appDns}', `https://${appConfig.domainName || ''}`);
    } else {
      this._customLogoutUrl = `https://${this._distribution.distributionDomainName}/logout`;
    }

    NagSuppressions.addResourceSuppressions(this._distribution, [{
      id: 'AwsSolutions-CFR4',
      reason: `Distributions with the default CloudFront viewer 
               certificate are non-compliant with enforcing TLSv1.1 or TLSv1.2.`,
    }]);

    return this;
  }

  withUserPool(userPool: WebUserPool): AppCdn {

    /* Cognito web app client for Frontend */
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

    if (this._domainName) {
      callbackUrls.push(`https://${this._domainName}`);
    } else {
      callbackUrls.push(`https://${this._distribution.distributionDomainName}`);
    }

    if (this._customLogoutUrl) {
      callbackUrlsLogout.push(this._customLogoutUrl);
    } else {
      callbackUrlsLogout.push(`https://${this._distribution.distributionDomainName}/logout`);
    }

    userPool.withWebAppClient(callbackUrls, callbackUrlsLogout);

    /*  
      CloudFront Lambda@Edge does not support environment variables. 
      For this reason they will be fetched from SSM by the Lambda@Edge during runtime. 
    */
    const userPoolParam = new ssm.StringParameter(this, 'user-pool-id', {
      parameterName: `/${this._appName}-${this._appEnvironment}/user-pool-id`,
      stringValue: userPool.getUserPoolId(),
    });

    const userPoolClientParam = new ssm.StringParameter(this, 'user-pool-domain-prefix', {
      parameterName: `/${this._appName}-${this._appEnvironment}/user-pool-domain`,
      stringValue: this.getDNS(userPool),
    });

    const cognitoClientParamName = `/${this._appName}-${this._appEnvironment}/user-pool-client-id`;
    new ssm.StringParameter(this, 'user-pool-client-id', {
      parameterName: cognitoClientParamName,
      stringValue: userPool.getUserPoolClientId(),
    });

    new ssm.StringParameter(this, 'user-pool-client-ids', {
      parameterName: `/${this._appName}-${this._appEnvironment}/user-pool-client-ids`,
      stringValue: userPool.getUserPoolClientIds().join(','),
    });

    const stack = Stack.of(this);

    const lambdaAtEdgeManagedPolicy = new iam.ManagedPolicy(this, 'auth-lambda-ssm-access', {
      managedPolicyName: `CDNAuthLambdaSSMAccess-${this._appEnvironment}`,
      description: 'Grants Lambda@Edge function access to the SSM parameters with OIDC data.',
      path: '/VirtualWorkbench/',
      statements: [new iam.PolicyStatement({
        actions: ['ssm:GetParameter'],
        resources: [
          userPoolParam.parameterArn,
          userPoolClientParam.parameterArn,
          `arn:aws:ssm:${stack.region}:${stack.account}:parameter${cognitoClientParamName}`
        ]
      })]
    });

    this._lambdaAtEdge.role?.addManagedPolicy(lambdaAtEdgeManagedPolicy);

    return this;
  }

  private getDNS(userPool: WebUserPool): string {
    let loginDNS = userPool.getUserPoolCustomLoginFQDN();
    if (!loginDNS) {
      loginDNS = userPool.getUserPoolLoginFQDN();
    }
    return loginDNS;
  }

  getDomainName(): string {
    return this._distribution.domainName;
  }

  getCustomDomainName(): string | undefined {
    return this._domainName;
  }

  getDistributionId(): string {
    return this._distribution.distributionId;
  }

  getBucketName(): string {
    return this._frontendS3Bucket.bucketName;
  }


  getCustomLogoutUrl(): string {
    return this._customLogoutUrl;
  }

  getErrorsBucketName(): string {
    return this._frontendErrorsS3Bucket.bucketName;
  }

}