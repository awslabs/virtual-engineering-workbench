// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import {
  Match, Template
} from 'aws-cdk-lib/assertions';
import { App, Stack } from 'aws-cdk-lib';
import * as Infrastructure from '../lib/public-access-deployment-stack';
import { AppConfig } from '../lib/app-config';

/* eslint jest/expect-expect: "off" */
/* eslint @typescript-eslint/naming-convention: "off" */

class FEStack {

  static get(oidcSecretName: string | undefined = undefined) {
    const cdkCfg: { [key: string]: string } = {
      LogoutUrl: 'http://localhost',
    };
    if (oidcSecretName !== undefined) {
      cdkCfg.OIDCSecretName = oidcSecretName;
    }

    const app = new App({
      context: {
        config: {
          dev: cdkCfg
        }
      }
    });

    const config = AppConfig.loadForEnvironment(app, 'dev');

    return new Infrastructure.PublicAccessDeploymentStack(app, 'MyTestStack', {
      stackName: 'ui-test',
      deploymentQualifier: 'abc',
      env: {
        region: 'us-east-1'
      },
      appName: 'my-app',
      appEnvironment: 'dev',
      formatResourceName: (resourceName: string) => `test-${resourceName}`,
      appConfig: config,
      wafProps: {
        provisionApiAcl: true,
      },
    });
  }
}

test('should contain 4 S3 buckets', () => {
  // ACT
  const stack = FEStack.get();
  const totalExpectedBuckets = 3;

  // ASSERT
  const template = Template.fromStack(stack);
  template.resourceCountIs('AWS::S3::Bucket', totalExpectedBuckets);
});

test('S3 bucket should be private', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::S3::Bucket',
    Match.objectLike(
      {
        BucketName: { 'Fn::Join': ['', ['ui-test-us-east-1-', { Ref: 'AWS::AccountId' }]] },
        AccessControl: 'Private',
        PublicAccessBlockConfiguration: {
          BlockPublicAcls: true,
          BlockPublicPolicy: true,
          IgnorePublicAcls: true,
          RestrictPublicBuckets: true,
        }
      }
    ));
});

test('S3 bucket should have origin access policy configured', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::S3::BucketPolicy',
    Match.objectLike({
      Bucket: { Ref: Match.stringLikeRegexp('webappcdnfrontendbucket.*') },
      PolicyDocument: {
        Statement: Match.arrayWith([Match.objectLike({
          Action: 's3:GetObject',
          Condition: {
            StringEquals: {
              'AWS:SourceArn': {
                'Fn::Join': [
                  '',
                  Match.arrayWith([Match.objectLike(
                    { Ref: Match.stringLikeRegexp('webappcdnfrontenddistribution.*') }
                  )])
                ]
              }
            }
          }
        })])
      }
    }));
});

test('should contain one User Pool Client', () => {
  // ACT
  const stack = FEStack.get();
  const totalExpectedUserPoolClients = 1;

  // ASSERT
  const template = Template.fromStack(stack);
  template.resourceCountIs('AWS::Cognito::UserPoolClient', totalExpectedUserPoolClients);
});

test('User Pool Client should have a CloudFront callback url', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    CallbackURLs: Match.arrayWith([
      {
        'Fn::Join': [
          '',
          ['https://',
            {
              'Fn::GetAtt': [
                Match.stringLikeRegexp('webappcdnfrontenddistribution.*'),
                'DomainName'
              ]
            }
          ]]
      }
    ])
  }));
});

test('User Pool Client should be configured only with MyCorpOIDC identity provider', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get('fake-secret-name');

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    SupportedIdentityProviders: Match.arrayWith([
      Match.objectLike({ Ref: Match.stringLikeRegexp('webuserpooloidcprovider.*') })
    ]),
  }));
});

test('User Pool Client should be configured only with Cognito identity provider when OIDC params do not exist', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    SupportedIdentityProviders: Match.arrayWith([
      Match.exact('COGNITO')
    ]),
  }));
});

test('User Pool Client should be configured with authorization code grant flow only', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    AllowedOAuthFlows: ['code'],
  }));
});

test('User Pool Client should be configured with explicit auth flows', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    ExplicitAuthFlows: ['ALLOW_USER_SRP_AUTH', 'ALLOW_REFRESH_TOKEN_AUTH'],
  }));
});

test('User Pool Client should be configured with openid, email and profile scopes.', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    AllowedOAuthScopes: ['openid', 'email', 'profile'],
  }));
});

test('should have CloudFront distribution', () => {
  // ARRANGE
  const expectedDistributionCount = 1;

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.resourceCountIs('AWS::CloudFront::Distribution', expectedDistributionCount);
});

// test('CloudFront distribution should have WAF configured', () => {
//   // ARRANGE
//
//   // ACT
//   const stack = FEStack.get();
//
//   // ASSERT
//   const template = Template.fromStack(stack);
//   template.hasResourceProperties('AWS::CloudFront::Distribution', Match.objectLike({
//     DistributionConfig: {
//       WebACLId: {
//         Ref: Match.stringLikeRegexp('cfaclarnParameter')
//       }
//     }
//   }));
// });

test('CloudFront distribution should have Lambda@Edge auth lambda', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::CloudFront::Distribution', Match.objectLike({
    DistributionConfig: {
      DefaultCacheBehavior: {
        LambdaFunctionAssociations: [{
          EventType: 'viewer-request',
          LambdaFunctionARN: { Ref: Match.stringLikeRegexp('webappcdnauthhandler.*') }
        }]
      }
    }
  }));
});

test('FE stack should have cloudwatch alarm', () => {
  // ARRANGE
  const expectedCloudWatchAlarmCount = 3;

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.resourceCountIs('AWS::CloudWatch::Alarm', expectedCloudWatchAlarmCount);
});

test('should contain required output parameters', () => {
  // ARRANGE

  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasOutput('icwebclientidoutput', Match.objectLike({}));
  template.hasOutput('cdnfqdnoutput', Match.objectLike({}));
  template.hasOutput('cdndistributionidoutput', Match.objectLike({}));
  template.hasOutput('icfrontends3output', Match.objectLike({}));
});
