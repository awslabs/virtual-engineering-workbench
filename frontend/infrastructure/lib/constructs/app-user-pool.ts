// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Construct } from 'constructs';
import {
  aws_cognito as cognito,
  aws_lambda_nodejs as lambda_node,
  Stack,
  SecretValue,
  Duration,
  aws_wafv2,
  aws_lambda as lambda,
  RemovalPolicy,
} from 'aws-cdk-lib';
import { ProviderAttribute, UserPoolIdentityProviderOidc } from 'aws-cdk-lib/aws-cognito';
import { NagSuppressions } from 'cdk-nag';


export class WebUserPool extends Construct {

  private readonly _userPool: cognito.UserPool;
  private readonly _appName: string;
  private readonly _environment: string;
  private _userPoolWebAppClient: cognito.UserPoolClient;
  private _userPoolAppClients: cognito.UserPoolClient[];
  private _userPoolDomain: cognito.UserPoolDomain;
  private _userPoolCustomDomain: cognito.CfnUserPoolDomain;
  private _allowCustomUserLogin: boolean;

  constructor(scope: Construct, id: string, props: {
    appName: string,
    environment: string,
    allowCustomUserLogin?: boolean,
    requireCustomUserLogin2FA?: boolean,
  }) {
    super(scope, id);

    this._appName = props.appName;
    this._environment = props.environment;
    this._allowCustomUserLogin = props.allowCustomUserLogin ?? false;
    this._userPoolAppClients = [];

    this._userPool = new cognito.UserPool(this, 'my-app-user-pool', {
      userPoolName: `${this._appName.replace(/[^a-zA-Z0-9]/gu, '-')}-user-pool`,
      selfSignUpEnabled: false,
      mfa: props.requireCustomUserLogin2FA ? cognito.Mfa.REQUIRED : cognito.Mfa.OFF,
      mfaSecondFactor: { sms: false, otp: true },
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
        tempPasswordValidity: Duration.days(3),
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: true
        }
      },
      customAttributes: {
        user_tid: new cognito.StringAttribute({
          mutable: true
        })
      },
      signInAliases: {
        username: false,
        email: true
      },
      autoVerify: {
        email: true
      },
    });

    this._userPool.applyRemovalPolicy(
      props.environment === 'dev' ? RemovalPolicy.DESTROY : RemovalPolicy.RETAIN
    );

    NagSuppressions.addResourceSuppressions(this._userPool,
      [{
        id: 'AwsSolutions-COG2',
        reason: 'Users will authenticate using Identity Federation. There is no need for MFA.'
      }]
    );

    const cfnConstruct = this._userPool.node.defaultChild as cognito.CfnUserPool;
    cfnConstruct.userPoolAddOns = {
      advancedSecurityMode: 'ENFORCED',
    };

  }

  withDomainPrefix(domainPrefix: string): WebUserPool {

    this._userPoolDomain = this._userPool.addDomain('my-app-cognito-domain', {
      cognitoDomain: {
        domainPrefix,
      },
    });

    return this;
  }


  withCustomLoginDomain(customAppDomain: string, certificateArn: string): WebUserPool {

    const userPoolId = this._userPool.userPoolId;

    this._userPoolCustomDomain = new cognito.CfnUserPoolDomain(this, 'my-app-custom-domain', {
      domain: customAppDomain,
      userPoolId,
      customDomainConfig: {
        certificateArn
      },
    });


    return this;
  }

  withIdentityProvider(identityProviderSecretName: string): WebUserPool {

    this._userPool.registerIdentityProvider(new UserPoolIdentityProviderOidc(this, 'oidc-provider', {
      userPool: this._userPool,
      name: 'CorporateLogin',
      clientId: SecretValue.
        secretsManager(identityProviderSecretName, {
          jsonField: 'ClientID'
        }).toString(),
      clientSecret: SecretValue.
        secretsManager(identityProviderSecretName, {
          jsonField: 'ClientSecret'
        }).toString(),
      issuerUrl: SecretValue.
        secretsManager(identityProviderSecretName, {
          jsonField: 'Issuer'
        }).toString(),
      scopes: ['openid', 'email', 'profile'],
      attributeMapping: {
        email: ProviderAttribute.other('email'),
        givenName: ProviderAttribute.other('given_name'),
        familyName: ProviderAttribute.other('family_name'),
        custom: {
          'custom:user_tid': ProviderAttribute.other('sub'), // eslint-disable-line
        }
      },
    }));

    return this;
  }

  withWebAppClient(callbackUrls: string[], callbackUrlsLogout: string[], generateSecret = false): WebUserPool {
    this._userPoolWebAppClient = this._withClient('web-client', callbackUrls, callbackUrlsLogout, generateSecret);
    this._userPoolAppClients.push(this._userPoolWebAppClient);
    return this;
  }

  withClient(name: string, callbackUrls: string[], callbackUrlsLogout: string[], generateSecret = false): WebUserPool {
    this._userPoolAppClients.push(this._withClient(name, callbackUrls, callbackUrlsLogout, generateSecret));
    return this;
  }

  private _withClient(name: string, callbackUrls: string[], callbackUrlsLogout: string[], generateSecret = false): cognito.UserPoolClient {
    const supportedIdentityProviders: cognito.UserPoolClientIdentityProvider[] = this._userPool.identityProviders.map(
      idp => cognito.UserPoolClientIdentityProvider.custom(idp.providerName)
    );
    if (supportedIdentityProviders.length === 0 || this._allowCustomUserLogin) {
      supportedIdentityProviders.push(cognito.UserPoolClientIdentityProvider.COGNITO);
    }

    return this._userPool.addClient(name, {
      userPoolClientName: `${this._appName.replace(/[^a-zA-Z0-9]/gu, '-')}-${name}`,
      supportedIdentityProviders,
      authFlows: {
        adminUserPassword: false,
        custom: false,
        userPassword: false,
        userSrp: true
      },
      disableOAuth: false,
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
          implicitCodeGrant: false,
          clientCredentials: false
        },
        scopes: [ cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE ],
        callbackUrls,
        logoutUrls: callbackUrlsLogout,
      },
      refreshTokenValidity: Duration.hours(48),
      accessTokenValidity: Duration.minutes(60),
      idTokenValidity: Duration.minutes(60),
      generateSecret,
    });
  }

  withWAF(webAclArn: string): WebUserPool {
    new aws_wafv2.CfnWebACLAssociation(
      this,
      'WAFACLAssociationCognito',
      {
        resourceArn: this._userPool.userPoolArn,
        webAclArn
      }
    );
    return this;
  }

  withPostAuthenticationLogging(): WebUserPool {
    const functionName = `${this._appName}-user-pool-post-authentication`;
    const triggerLambda = new lambda_node.NodejsFunction(this, 'post-authentication-trigger', {
      runtime: lambda.Runtime.NODEJS_24_X,
      environment: {
        POWERTOOLS_SERVICE_NAME: functionName, // eslint-disable-line
        LOG_LEVEL: this._environment.toLocaleLowerCase() === 'prod' ? 'INFO' : 'DEBUG', // eslint-disable-line
      },
      functionName,
      reservedConcurrentExecutions: 10
    });

    this._userPool.addTrigger(cognito.UserPoolOperation.POST_AUTHENTICATION, triggerLambda);

    this._postAuthenticationLoggingSuppressions(triggerLambda);

    return this;
  }

  private _postAuthenticationLoggingSuppressions(triggerLambda: lambda.IFunction) {
    NagSuppressions.addResourceSuppressions(triggerLambda, [{
      id: 'NIST.800.53.R4-LambdaInsideVPC',
      reason: 'Environment does not have a VPC',
    }, {
      id: 'NIST.800.53.R5-LambdaInsideVPC',
      reason: 'Environment does not have a VPC',
    }, {
      id: 'NIST.800.53.R5-LambdaDLQ',
      reason: 'Lambda is synchronous and does not need a DLQ.',
    }]);

    if (triggerLambda.role !== undefined) {
      NagSuppressions.addResourceSuppressions(triggerLambda.role, [{
        id: 'AwsSolutions-IAM4',
        reason: 'Lambda is using a default Lambda execution role policy for CloudWatch access.',
      }]);
    }

  }

  getUserPoolId(): string {
    return this._userPool.userPoolId;
  }

  getUserPoolLoginFQDN(): string {
    const stack = Stack.of(this);

    return `${this._userPoolDomain.domainName}.auth.${stack.region}.amazoncognito.com`;
  }

  getUserPoolCustomLoginFQDN(): string {
    if (this._userPoolCustomDomain) {
      return this._userPoolCustomDomain.domain;
    }
    return '';
  }

  getUserPoolCustomLoginCloudFrontURL(): string {
    if (this._userPoolCustomDomain) {
      return this._userPoolCustomDomain.attrCloudFrontDistribution;
    }
    return '';
  }

  getUserPoolClientId(): string {
    return this._userPoolWebAppClient.userPoolClientId;
  }

  getUserPoolClientIds(): string[] {
    return this._userPoolAppClients.map(x => x.userPoolClientId);
  }

  getProviderName(): string {
    return this._userPool.userPoolProviderName;
  }

  getUserPool(): cognito.UserPool {
    return this._userPool;
  }

  getUserPoolClient(): cognito.UserPoolClient {
    return this._userPoolWebAppClient;
  }

  getLoginDomain() {
    return this._userPoolDomain;
  }

}