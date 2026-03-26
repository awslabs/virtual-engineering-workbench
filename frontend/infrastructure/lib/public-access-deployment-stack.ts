// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Construct } from 'constructs';
import {
  Aspects,
  CfnOutput,
  Duration,
  Fn,
  Stack,
  StackProps,
  aws_sns as sns,
  aws_cloudwatch as cloudwatch,
} from 'aws-cdk-lib';
import { WebUserPool } from './constructs/app-user-pool';
import { CfAlarm } from './constructs/cloudwatch/l3-alarm-cf';
import { AppCdn } from './constructs/app-cdn';
import { AppConfig } from './app-config';
import { SnsAction } from 'aws-cdk-lib/aws-cloudwatch-actions';
import { Alarm, Color, ComparisonOperator, Dashboard, GraphWidget, Metric, SingleValueWidget } from 'aws-cdk-lib/aws-cloudwatch';
import { WafInfrastructure, WafInfrastructureProps } from './constructs/waf/waf-infrastructure';
import { AwsSolutionsChecks, NIST80053R4Checks, NIST80053R5Checks } from 'cdk-nag';

/* eslint complexity: "off" */

export class PublicAccessDeploymentStack extends Stack {

  constructor(scope: Construct, id: string, props: StackProps & {
    appName: string,
    appEnvironment: string,
    deploymentQualifier: string,
    formatResourceName: (resourceName: string) => string,
    appConfig: AppConfig,
    wafProps: Omit<WafInfrastructureProps, 'appEnvironment' | 'formatResourceName'>,
  }) {
    super(scope, id, props);

    const waf = new WafInfrastructure(this, 'waf', {
      appEnvironment: props.appEnvironment,
      formatResourceName: props.formatResourceName,
      ...props.wafProps,
    });
    const cognitoACLArn = waf.cognitoAclArn;
    const cfACLArn = waf.cloudfrontAclArn;

    const webUserPool = new WebUserPool(this, 'web-user-pool', {
      appName: `${props.appName}-${props.appEnvironment}`,
      environment: props.appEnvironment,
      allowCustomUserLogin: props.appConfig.allowCustomUserLogin,
      requireCustomUserLogin2FA: props.appConfig.requireCustomUserLogin2FA,
    }).
      withWAF(waf.cognitoAclArn).
      withDomainPrefix(`${props.appName}-${props.appEnvironment}-login-${props.deploymentQualifier}`).
      withPostAuthenticationLogging();

    if (props.appConfig.oidcSecretName !== undefined) {
      webUserPool.withIdentityProvider(props.appConfig.oidcSecretName);
    }

    if (props.appConfig.customLoginDNSEnabled &&
      !!props.appConfig.domainNameLogin &&
      !!props.appConfig.certArn
    ) {
      webUserPool.withCustomLoginDomain(props.appConfig.domainNameLogin, props.appConfig.certArn);
    }

    const cdn = new AppCdn(this, 'web-app-cdn', {
      appName: props.appName,
      appEnvironment: props.appEnvironment,
    }).
      withWAF(waf.cloudfrontAclArn).
      withLambdaProtection().
      withLambdaClientIpHandler().
      withCDN(props.appConfig).
      withUserPool(webUserPool);

    /* VEW WEB App Infrastructure Monitoring:
    * - CloudWatch Metric [LambdaExecutionError, LambdaValidationError,
    5xxErrorRate, 4xxErrorRate, Requests, Wafv2_BlockRequests, wafv2_AllowedRequests]
    * - CloudWatch Alarms [CloudFront - 5xxError, WAFv2 - BlockRequests(cloudfront/cognito)]
    * - CloudWatch Dashboard
    * */

    // import SNS topic from BE(Backend repo) by constructing the topicArn
    const snsTopicArn = Stack.of(this).formatArn({
      region: 'us-east-1',
      service: 'sns',
      account: this.account,
      resource: `proserve-wb-monitoring-alarm-topic-${props.appEnvironment}`,

    });
    const snsTopic = sns.Topic.fromTopicArn(this, 'DelegationRole', snsTopicArn);

    const wafv2CognitoAllowedRequests = new Metric({
      metricName: 'AllowedRequests',
      namespace: 'AWS/WAFV2',
      color: Color.GREEN,
      label: 'Cognito AllowedRequests',
      dimensionsMap: {
        Rule: 'CognitoACL',
        WebACL: Fn.select(
          2,
          Fn.split('/', cognitoACLArn)
        ),
        Region: 'us-east-1',
      },
      statistic: 'Sum',
      period: Duration.seconds(300),
    });

    const wafv2CognitoBlockedRequests = new Metric({
      metricName: 'BlockedRequests',
      namespace: 'AWS/WAFV2',
      color: Color.RED,
      label: 'Cognito BlockedRequests',
      dimensionsMap: {
        Rule: 'CognitoACL',
        WebACL: Fn.select(
          2,
          Fn.split('/', cognitoACLArn)
        ),
        Region: 'us-east-1',
      },
      statistic: 'Sum',
      period: Duration.seconds(300),
    });

    const wafv2CloudfrontAutomatedTestTokenAllowedRequests = new Metric({
      metricName: 'AllowedRequests',
      namespace: 'AWS/WAFV2',
      color: Color.BLUE,
      label: 'RegressionToken AllowedRequests',
      dimensionsMap: {
        Rule: 'automated-test-token',
        WebACL: Fn.select(
          2,
          Fn.split('/', cfACLArn)
        ),
      },
      statistic: 'Sum',
      period: Duration.seconds(300),
    });

    const wafv2CloudfrontAllowedRequests = new Metric({
      metricName: 'AllowedRequests',
      namespace: 'AWS/WAFV2',
      color: Color.GREEN,
      label: 'CF AllowedRequests',
      dimensionsMap: {
        Rule: 'CloudFrontACL',
        WebACL: Fn.select(
          2,
          Fn.split('/', cfACLArn)
        ),
      },
      statistic: 'Sum',
      period: Duration.seconds(300),
    });

    const wafv2CloudfrontBlockedRequests = new Metric({
      metricName: 'BlockedRequests',
      namespace: 'AWS/WAFV2',
      color: Color.RED,
      label: 'CF BlockedRequests',
      dimensionsMap: {
        Rule: 'CloudFrontACL',
        WebACL: Fn.select(
          2,
          Fn.split('/', cfACLArn)
        ),
      },
      statistic: 'Sum',
      period: Duration.seconds(300),
    });

    const cf5xxErrorRate = new Metric({
      namespace: 'AWS/CloudFront',
      metricName: '5xxErrorRate',
      color: Color.RED,
      label: 'CloudFront 5xx Rate',
      dimensionsMap: {
        DistributionId: cdn.getDistributionId(),
        Region: 'Global',
      },
      statistic: 'Average',
      period: Duration.seconds(3600),
    });

    const cf4xxErrorRate = new Metric({
      namespace: 'AWS/CloudFront',
      metricName: '4xxErrorRate',
      color: Color.RED,
      label: 'CloudFront 4xx Rate',
      dimensionsMap: {
        DistributionId: cdn.getDistributionId(),
        Region: 'Global',
      },
      statistic: 'Average',
      period: Duration.seconds(3600),
    });

    const cf5xxErrorAlarm = new Alarm(this, 'cloudfrontErrors', {
      alarmName: `proserve-wb-monitoring-cloudfront-5xx-failures-alarm-${props.appEnvironment}`,
      alarmDescription: 'This alarm fires when there are 500 errors returned by VIEW Web App[Cloudfront]',
      comparisonOperator: ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      threshold: 1,
      evaluationPeriods: 1,
      datapointsToAlarm: 1,
      metric: new Metric({
        namespace: 'AWS/CloudFront',
        metricName: '5xxErrorRate',
        color: Color.RED,
        dimensionsMap: {
          DistributionId: cdn.getDistributionId(),
          Region: 'Global',
        },
        statistic: 'Sum',
        period: Duration.seconds(300),
      }),
    });
    cf5xxErrorAlarm.addAlarmAction(new SnsAction(snsTopic));

    const wafv2BlockedRequestsAggregated = new cloudwatch.MathExpression({
      label: 'WAF Block Rate',
      expression: 'SUM(METRICS())',
      usingMetrics: {
        m1: wafv2CognitoBlockedRequests,
        m2: wafv2CloudfrontBlockedRequests
      }
    });

    const anomalyCloudfrontDetector = new cloudwatch.CfnAnomalyDetector(this, 'AnomalyCfDetector', {
      configuration: {
        metricTimeZone: 'UTC',
      },
      dimensions: [
        {
          name: 'Rule',
          value: 'CloudFrontACL',
        },
        {
          name: 'WebACL',
          value: Fn.select(
            2,
            Fn.split('/', cfACLArn)
          ),
        },
      ],
      metricName: 'BlockedRequests',
      namespace: 'AWS/WAFV2',
      stat: 'Sum',
    });

    const anomalyCognitoDetector = new cloudwatch.CfnAnomalyDetector(this, 'AnomalyCognitoDetector', {
      configuration: {
        metricTimeZone: 'UTC',
      },
      dimensions: [
        {
          name: 'Rule',
          value: 'CognitoACL',
        },
        {
          name: 'Region',
          value: 'us-east-1',
        },
        {
          name: 'WebACL',
          value: Fn.select(
            2,
            Fn.split('/', cognitoACLArn)
          ),
        },
      ],
      metricName: 'BlockedRequests',
      namespace: 'AWS/WAFV2',
      stat: 'Sum',
    });

    new CfAlarm(this, 'anomalyCfAlarm', {
      alarmName: `proserve-wb-monitoring-wafv2-cloudfront-blocked-requests-alarm-${props.appEnvironment}`,
      alarmDescription: 'This alarm fires when there are elevated WAFv2 cloudfront ACL BlockedRequests',
      alarmActions: [snsTopic.topicArn],
      metrics: [
        {
          expression: 'ANOMALY_DETECTION_BAND(m1, 2)',
          id: 'ad1',
        },
        {
          id: 'm1',
          metricStat: {
            metric: {
              metricName: anomalyCloudfrontDetector.metricName,
              namespace: anomalyCloudfrontDetector.namespace,
              dimensions: [
                {
                  name: 'Rule',
                  value: 'CloudFrontACL',
                },
                {
                  name: 'WebACL',
                  value: Fn.select(
                    2,
                    Fn.split('/', cfACLArn)
                  ),
                },
              ],
            },
            period: Duration.minutes(5).toSeconds(),
            stat: 'Sum',
          },
        },
      ],
    });

    new CfAlarm(this, 'anomalyCognitoAlarm', {
      alarmName: `proserve-wb-monitoring-wafv2-cognito-blocked-requests-alarm-${props.appEnvironment}`,
      alarmDescription: 'This alarm fires when there are elevated WAFv2 cognito ACL BlockedRequests',
      alarmActions: [snsTopic.topicArn],
      metrics: [
        {
          expression: 'ANOMALY_DETECTION_BAND(m1, 2)',
          id: 'ad1',
        },
        {
          id: 'm1',
          metricStat: {
            metric: {
              metricName: anomalyCognitoDetector.metricName,
              namespace: anomalyCognitoDetector.namespace,
              dimensions: [
                {
                  name: 'Rule',
                  value: 'CognitoACL',
                },
                {
                  name: 'Region',
                  value: 'us-east-1',
                },
                {
                  name: 'WebACL',
                  value: Fn.select(
                    2,
                    Fn.split('/', cognitoACLArn)
                  ),
                },
              ],
            },
            period: Duration.minutes(5).toSeconds(),
            stat: 'Sum',
          },
        },
      ],
    });

    /* VEW WEB App Dashboard */

    const cf5XXRate = new SingleValueWidget({
      title: 'CloudFront 5xx / 1hr',
      height: 4,
      width: 8,
      setPeriodToTimeRange: true,
      metrics: [cf5xxErrorRate],
    });

    const cf4XXRate = new SingleValueWidget({
      title: 'CloudFront 4xx / 1hr',
      height: 4,
      width: 8,
      setPeriodToTimeRange: true,
      metrics: [cf4xxErrorRate],
    });

    const wafBlock = new SingleValueWidget({
      title: 'WAF Block / 1hr',
      height: 4,
      width: 8,
      setPeriodToTimeRange: true,
      metrics: [wafv2BlockedRequestsAggregated],
    });
    const cloudfrontGraph = new GraphWidget({
      title: 'CloudFront',
      width: 12,
      right: [
        cf5xxErrorRate, cf4xxErrorRate
      ],
      left: [
        new Metric({
          namespace: 'AWS/CloudFront',
          metricName: 'LambdaExecutionError',
          color: Color.ORANGE,
          dimensionsMap: {
            DistributionId: cdn.getDistributionId(),
            Region: 'Global',
          },
          statistic: 'Sum',
          period: Duration.seconds(300),
        }),
        new Metric({
          namespace: 'AWS/CloudFront',
          metricName: 'LambdaValidationError',
          color: Color.ORANGE,
          dimensionsMap: {
            DistributionId: cdn.getDistributionId(),
            Region: 'Global',
          },
          statistic: 'Sum',
          period: Duration.seconds(300),
        }),
        new Metric({
          namespace: 'AWS/CloudFront',
          metricName: 'Requests',
          color: Color.GREEN,
          dimensionsMap: {
            DistributionId: cdn.getDistributionId(),
            Region: 'Global',
          },
          statistic: 'Sum',
          period: Duration.seconds(300),
        }),
      ],
    });

    const wafv2Graph = new GraphWidget({
      title: 'WAF',
      width: 12,
      left: [
        wafv2CloudfrontAllowedRequests, wafv2CognitoAllowedRequests, wafv2CloudfrontAutomatedTestTokenAllowedRequests
      ],
      right: [
        wafv2CloudfrontBlockedRequests, wafv2CognitoBlockedRequests
      ],
    });

    const cwDashboardUrl = new Dashboard(this, 'monitoring-dashboard', {
      dashboardName: `proserve-wb-monitoring-dashboard-frontend-${props.appEnvironment}`,
      widgets: [
        [cf5XXRate, cf4XXRate, wafBlock],
        [cloudfrontGraph, wafv2Graph]
      ],
    });

    /* Outputs */
    new CfnOutput(this, 'ic-web-client-id-output', {
      exportName: `${this.stackName}-IcWebClientId`,
      value: webUserPool.getUserPoolClientId()
    });

    new CfnOutput(this, 'cdn-fqdn-output', {
      exportName: `${this.stackName}-CdnFqdn`,
      value: cdn.getDomainName(),
    });

    new CfnOutput(this, 'cdn-custom-fqdn-output', {
      exportName: `${this.stackName}-CustomFqdn`,
      value: cdn.getCustomDomainName() || 'not available',
    });

    new CfnOutput(this, 'cdn-distribution-id-output', {
      exportName: `${this.stackName}-CdnDistributionId`,
      value: cdn.getDistributionId(),
    });

    new CfnOutput(this, 'ic-frontend-s3-output', {
      exportName: `${this.stackName}-S3BucketName`,
      value: cdn.getBucketName(),
    });

    new CfnOutput(this, 'ic-frontend-errors-s3-output', {
      exportName: `${this.stackName}-S3ErrorsBucketName`,
      value: cdn.getErrorsBucketName(),
    });

    new CfnOutput(this, 'user-pool-output-id', {
      exportName: `${this.stackName}-UserPoolId`,
      value: webUserPool.getUserPoolId(),
    });

    new CfnOutput(this, 'user-pool-output-domain', {
      exportName: `${this.stackName}-UserPoolDomain`,
      value: webUserPool.getUserPoolLoginFQDN()
    });

    new CfnOutput(this, 'user-pool-output-logout-url', {
      exportName: `${this.stackName}-UserPoolLogoutUrl`,
      value: cdn.getCustomLogoutUrl()
    });

    new CfnOutput(this, 'monitoring-topic-output', {
      exportName: `${this.stackName}-topicArn`,
      value: snsTopic.topicArn
    });

    new CfnOutput(this, 'monitoring-dashboard-output', {
      exportName: `${this.stackName}-MonitoringDashboardUrl`,
      value: `https://${this.region}.console.aws.amazon.com/cloudwatch/home?region=${this.region}#dashboards/dashboard/${cwDashboardUrl.dashboardName}`
    });


    this.tryOutputCognitoLoginCustomDNSOutputs(props.appConfig, webUserPool);

    /* cdk-nag checks */
    Aspects.of(this).add(new AwsSolutionsChecks({ reports: true, verbose: true }));
    Aspects.of(this).add(new NIST80053R4Checks({ reports: true, verbose: true }));
    Aspects.of(this).add(new NIST80053R5Checks({ reports: true, verbose: true }));
  }

  tryOutputCognitoLoginCustomDNSOutputs(appConfig: AppConfig, webUserPool: WebUserPool) {
    if (appConfig.customLoginDNSEnabled && !!appConfig.domainNameLogin && !!appConfig.certArn) {
      new CfnOutput(this, 'user-pool-output-custom-domain', {
        exportName: `${this.stackName}-UserPoolCustomDomain`,
        value: webUserPool.getUserPoolCustomLoginFQDN()
      });

      new CfnOutput(this, 'user-pool-output-custom-domain-cloudfront', {
        exportName: `${this.stackName}-UserPoolCustomDomainCloudFront`,
        value: webUserPool.getUserPoolCustomLoginCloudFrontURL()
      });
    }
  }
}

/* Helper functions*/
const createSingleValueWidget = (title: string, metrics: cloudwatch.IMetric[]) => {
  return new SingleValueWidget({
    title,
    height: 4,
    width: 8,
    setPeriodToTimeRange: true,
    metrics: []
  });
};