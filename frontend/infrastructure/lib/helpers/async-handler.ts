// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { CloudFrontRequestEvent, CloudFrontRequestResult } from 'aws-lambda';
import { Authenticator } from 'cognito-at-edge';
import { AuthenticatorWithCookieDeduplication } from './authenticator-with-cookie-deduplication';

/* global AuthenticatorLogLevel */
export type LogLevel = 'fatal' | 'error' | 'warn' | 'info' | 'debug' | 'trace' | 'silent';

type AsyncHandlerParams = {
  region: string,
  logLevel?: LogLevel,
  cookieExpirationDays: number,
  userPoolIdResolver: () => Promise<string>,
  userPoolClientIdResolver: () => Promise<string>,
  userPoolDomainResolver: () => Promise<string>,
};
export class AsyncHandler {

  private static _authenticatorInstance: Authenticator;

  public static async handleAsync(event: CloudFrontRequestEvent, {
    region,
    logLevel,
    cookieExpirationDays,
    userPoolIdResolver,
    userPoolClientIdResolver,
    userPoolDomainResolver
  } : AsyncHandlerParams): Promise<CloudFrontRequestResult> {

    if (AsyncHandler._authenticatorInstance === undefined) {

      const [userPoolId, userPoolAppId, userPoolDomain] = await Promise.all([
        userPoolIdResolver(),
        userPoolClientIdResolver(),
        userPoolDomainResolver()]
      );

      AsyncHandler._authenticatorInstance = new Authenticator({
        region,
        logLevel,
        userPoolId,
        userPoolAppId,
        userPoolDomain,
        cookieExpirationDays,
        disableCookieDomain: true,
      });

      AsyncHandler._authenticatorInstance = AuthenticatorWithCookieDeduplication.decorate(AsyncHandler._authenticatorInstance, {
        userPoolAppId,
      });
    }

    return AsyncHandler._authenticatorInstance.handle(event);
  }
}
