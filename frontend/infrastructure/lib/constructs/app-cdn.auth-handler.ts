// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { CloudFrontRequestEvent, CloudFrontRequestHandler } from 'aws-lambda';
import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';
import config from './app-cdn.auth-handler.config.json';
import { AsyncHandler, LogLevel } from '../helpers/async-handler';

const DEFAULT_REGION = 'us-east-1';
const COOKIE_EXPIRATION_DAYS = 2;
const ssmParamNames = {
  userPoolIdParamName: `/${config.AppName}/user-pool-id`,
  userPoolClientIdParamName: `/${config.AppName}/user-pool-client-id`,
  userPoolDomainParamName: `/${config.AppName}/user-pool-domain`
};

const ssmClient = new SSMClient({ region: DEFAULT_REGION });

/* Comment to force redeploy */
export const handler: CloudFrontRequestHandler =
  async (event: CloudFrontRequestEvent) => AsyncHandler.handleAsync(
    event,
    {
      region: DEFAULT_REGION,
      logLevel: (config.LogLevel || 'info') as LogLevel,
      cookieExpirationDays: COOKIE_EXPIRATION_DAYS,
      userPoolIdResolver:
        async () => (
          await ssmClient.send(new GetParameterCommand({ Name: ssmParamNames.userPoolIdParamName }))
        ).Parameter?.Value || '',
      userPoolClientIdResolver:
        async () => (
          await ssmClient.send(new GetParameterCommand({ Name: ssmParamNames.userPoolClientIdParamName }))
        ).Parameter?.Value || '',
      userPoolDomainResolver:
        async () => (
          await ssmClient.send(new GetParameterCommand({ Name: ssmParamNames.userPoolDomainParamName }))
        ).Parameter?.Value || '',
    });
