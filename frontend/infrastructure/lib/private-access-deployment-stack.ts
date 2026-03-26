// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Construct } from 'constructs';
import {
  Aspects,
  CfnOutput,
  Stack,
  StackProps,
} from 'aws-cdk-lib';
import { WebUserPool } from './constructs/app-user-pool';
import { AppElb } from './constructs/app-elb';
import { AppConfig } from './app-config';
import { AwsSolutionsChecks, NIST80053R4Checks, NIST80053R5Checks } from 'cdk-nag';

/* eslint complexity: "off" */

export class PrivateAccessDeploymentStack extends Stack {

  constructor(scope: Construct, id: string, props: StackProps & {
    appName: string,
    appEnvironment: string,
    deploymentQualifier: string,
    formatResourceName: (resourceName: string) => string,
    appConfig: AppConfig,
  }) {
    super(scope, id, props);

    if (!props.appConfig.domainName) {
      throw new Error('Domain name is required when making a private deployment.');
    }


    if (!props.appConfig.certArn) {
      throw new Error('Certificate ARN is required when making a private deployment.');
    }

    const webUserPool = new WebUserPool(this, 'web-user-pool', {
      appName: `${props.appName}-${props.appEnvironment}`,
      environment: props.appEnvironment,
      allowCustomUserLogin: props.appConfig.allowCustomUserLogin,
      requireCustomUserLogin2FA: props.appConfig.requireCustomUserLogin2FA,
    }).
      withDomainPrefix(`${props.appName}-${props.appEnvironment}-login-${props.deploymentQualifier}`).
      withPostAuthenticationLogging();

    if (props.appConfig.oidcSecretName !== undefined) {
      webUserPool.withIdentityProvider(props.appConfig.oidcSecretName);
    }

    if (props.appConfig.customLoginDNSEnabled &&
      !!props.appConfig.domainNameLogin &&
      !!props.appConfig.certArnLogin
    ) {
      webUserPool.withCustomLoginDomain(props.appConfig.domainNameLogin, props.appConfig.certArnLogin);
    }

    const cdn = new AppElb(this, 'web-app-elb', {
      appName: props.appName,
      appEnvironment: props.appEnvironment,
      domainName: props.appConfig.domainName,
      certificateArn: props.appConfig.certArn,
      formatResourceName: props.formatResourceName,
    }).
      withALB(props.appConfig).
      withUserPool(webUserPool);

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

    new CfnOutput(this, 'ic-frontend-s3-output', {
      exportName: `${this.stackName}-S3BucketName`,
      value: cdn.getBucketName(),
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
