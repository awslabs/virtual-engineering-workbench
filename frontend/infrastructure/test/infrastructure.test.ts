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

  static get(
    oidcSecretName: string | undefined = undefined,
    logoutUrl: string | null = 'http://localhost',
    oidcUserIdClaim?: string,
    domainName?: string,
    additionalAppClients?: unknown,
  ) {
    const cdkCfg: { [key: string]: unknown } = {
      LogoutUrl: logoutUrl ?? undefined,
      OIDCSecretName: oidcSecretName,
      OIDCUserIdClaim: oidcUserIdClaim,
      AdditionalAppClients: additionalAppClients,
    };
    for (const key of Object.keys(cdkCfg)) {
      if (cdkCfg[key] === undefined) {
        delete cdkCfg[key];
      }
    }

    const app = new App({
      context: {
        'use-custom-domain': domainName,
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

test('User Pool Client should resolve an OIDC logout URL against the CloudFront domain', () => {
  // ARRANGE
  const logoutUrl = 'https://identity.example/logout?return_to={appDns}/login';

  // ACT
  const stack = FEStack.get('fake-secret-name', logoutUrl);

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    LogoutURLs: Match.arrayWith([{
      'Fn::Join': [
        '',
        [
          'https://identity.example/logout?return_to=https://',
          {
            'Fn::GetAtt': [
              Match.stringLikeRegexp('webappcdnfrontenddistribution.*'),
              'DomainName'
            ]
          },
          '/login'
        ]
      ]
    }])
  }));
});

test('User Pool Client should resolve an OIDC logout URL against the custom application domain', () => {
  // ACT
  const stack = FEStack.get(
    'fake-secret-name',
    'https://identity.example/logout?return_to={appDns}/login',
    undefined,
    'workbench.example.com',
  );

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    LogoutURLs: Match.arrayWith([
      'https://identity.example/logout?return_to=https://workbench.example.com/login'
    ])
  }));
});

test('User Pool Client should use the custom application domain for Cognito logout', () => {
  // ACT
  const stack = FEStack.get(
    'fake-secret-name',
    null,
    undefined,
    'workbench.example.com',
  );

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    LogoutURLs: Match.arrayWith(['https://workbench.example.com/logout'])
  }));
});

test('User Pool Client should keep the Cognito logout URL when OIDC is not configured', () => {
  // ACT
  const stack = FEStack.get();

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    LogoutURLs: Match.arrayWith(['http://localhost'])
  }));
});

test('User Pool Client should be configured only with the corporate OIDC identity provider', () => {
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

test('OIDC user ID should default to the subject claim', () => {
  // ACT
  const stack = FEStack.get('fake-secret-name');

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolIdentityProvider', Match.objectLike({
    AttributeMapping: Match.objectLike({
      'custom:user_tid': 'sub',
    }),
  }));
});

test('Configured OIDC user ID claim should be mapped to the VEW user ID attribute', () => {
  // ACT
  const stack = FEStack.get(
    'fake-secret-name',
    'http://localhost',
    'https://workbench.example.com/claims/user_id',
  );

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolIdentityProvider', Match.objectLike({
    AttributeMapping: Match.objectLike({
      'custom:user_tid': 'https://workbench.example.com/claims/user_id',
    }),
  }));
});

test('OIDC verified email claim should be mapped to Cognito', () => {
  // ACT
  const stack = FEStack.get('fake-secret-name');

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolIdentityProvider', Match.objectLike({
    AttributeMapping: Match.objectLike({
      email_verified: 'email_verified',
    }),
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
    ExplicitAuthFlows: ['ALLOW_REFRESH_TOKEN_AUTH'],
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

const APP_CLIENT = {
  Name: 'example-app',
  CallbackUrls: ['https://app.example.com/callback'],
  GenerateSecret: true,
  RefreshTokenValidityHours: 720,
};

test('should contain an additional User Pool Client per configured app client', () => {
  // ACT
  const stack = FEStack.get(undefined, 'http://localhost', undefined, undefined, [APP_CLIENT]);

  // ASSERT
  const template = Template.fromStack(stack);
  template.resourceCountIs('AWS::Cognito::UserPoolClient', 2);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    ClientName: 'my-app-dev-example-app',
    CallbackURLs: ['https://app.example.com/callback'],
    LogoutURLs: [],
    GenerateSecret: true,
    AllowedOAuthFlows: ['code'],
    AllowedOAuthScopes: ['openid', 'email', 'profile'],
    ExplicitAuthFlows: ['ALLOW_REFRESH_TOKEN_AUTH'],
    RefreshTokenValidity: 720 * 60,
  }));
});

test('Additional User Pool Client should keep the web client refresh token validity by default', () => {
  // ACT
  const stack = FEStack.get(undefined, 'http://localhost', undefined, undefined, [
    { Name: 'example-app', CallbackUrls: APP_CLIENT.CallbackUrls },
  ]);

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    ClientName: 'my-app-dev-example-app',
    GenerateSecret: false,
    RefreshTokenValidity: 48 * 60,
  }));
});

test('Additional User Pool Client should be configured only with the corporate identity provider', () => {
  // ACT
  const stack = FEStack.get('oidc-secret', 'http://localhost', undefined, undefined, [APP_CLIENT]);

  // ASSERT
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::Cognito::UserPoolClient', Match.objectLike({
    ClientName: 'my-app-dev-example-app',
    SupportedIdentityProviders: Match.not(Match.arrayWith(['COGNITO'])),
  }));
});

test('Additional User Pool Client id should be accepted by the API authorizer', () => {
  // ACT
  const stack = FEStack.get(undefined, 'http://localhost', undefined, undefined, [APP_CLIENT]);

  // ASSERT
  const template = Template.fromStack(stack);
  const [appClientId] = Object.keys(template.findResources('AWS::Cognito::UserPoolClient', {
    Properties: { ClientName: 'my-app-dev-example-app' },
  }));
  const [webClientId] = Object.keys(template.findResources('AWS::Cognito::UserPoolClient', {
    Properties: { ClientName: 'my-app-dev-web-client' },
  }));
  template.hasResourceProperties('AWS::SSM::Parameter', {
    Name: '/my-app-dev/user-pool-client-ids',
    Value: { 'Fn::Join': ['', [{ Ref: appClientId }, ',', { Ref: webClientId }]] },
  });
  template.hasOutput('appclientexampleappidoutput', { Value: { Ref: appClientId } });
});

test.each([
  ['a name with upper case', [{ ...APP_CLIENT, Name: 'ExampleApp' }]],
  ['the web client name', [{ ...APP_CLIENT, Name: 'web-client' }]],
  ['a duplicate name', [APP_CLIENT, APP_CLIENT]],
  ['names that differ only in dashes', [APP_CLIENT, { ...APP_CLIENT, Name: 'exampleapp' }]],
  ['an entry that is not an object', [null]],
  ['a GenerateSecret that is not a boolean', [{ ...APP_CLIENT, GenerateSecret: 'true' }]],
  ['no callback URL', [{ ...APP_CLIENT, CallbackUrls: [] }]],
  ['a plain http callback URL', [{ ...APP_CLIENT, CallbackUrls: ['http://app.example.com/callback'] }]],
  ['a fractional refresh token validity', [{ ...APP_CLIENT, RefreshTokenValidityHours: 1.5 }]],
  ['a value that is not a list', APP_CLIENT],
])('Additional app clients should reject %s', (_, clients) => {
  expect(() => FEStack.get(undefined, 'http://localhost', undefined, undefined, clients))
    .toThrow(/AdditionalAppClients/u);
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
