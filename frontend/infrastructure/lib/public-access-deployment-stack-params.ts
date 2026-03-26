// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Construct } from 'constructs';
import {
  Stack,
  StackProps,
  aws_ssm as ssm,
} from 'aws-cdk-lib';
import { AppConfig } from './app-config';
import { AwsCustomResource, AwsCustomResourcePolicy, AwsSdkCall, PhysicalResourceId } from 'aws-cdk-lib/custom-resources';

/* eslint complexity: "off" */

export class PublicAccessDeploymentParamsStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps & {
    appName: string,
    appEnvironment: string,
    deploymentQualifier: string,
    formatResourceName: (resourceName: string) => string,
    appConfig: AppConfig,
  }) {
    super(scope, id, props);

    const userPoolIdParamName = `/${props.appName}-${props.appEnvironment}/user-pool-id`;
    const userPoolDomainParamName = `/${props.appName}-${props.appEnvironment}/user-pool-domain`;
    const cognitoClientParamName = `/${props.appName}-${props.appEnvironment}/user-pool-client-id`;
    const cognitoClientsParamName = `/${props.appName}-${props.appEnvironment}/user-pool-client-ids`;

    for (const paramName of [userPoolIdParamName, userPoolDomainParamName, cognitoClientParamName, cognitoClientsParamName]) {
      const paramId = paramName.split('/').slice(-1)[0];

      const getParamValueRequest = new AwsCustomResource(this, `ParamGetter-${paramId}`, {
        onUpdate: {
          service: 'SSM',
          action: 'getParameter',
          parameters: {
            Name: paramName
          },
          region: 'us-east-1',
          physicalResourceId: PhysicalResourceId.of(`${paramId}-getter`),
        } as AwsSdkCall,
        policy: AwsCustomResourcePolicy.fromSdkCalls({
          resources: AwsCustomResourcePolicy.ANY_RESOURCE
        })
      });

      const paramValue = getParamValueRequest.getResponseField('Parameter.Value');

      new ssm.StringParameter(this, paramId, {
        parameterName: paramName,
        stringValue: paramValue,
      });
    }
  }
}