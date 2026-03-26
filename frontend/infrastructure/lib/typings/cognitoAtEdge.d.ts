// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
/* eslint max-classes-per-file: "off" */

type AuthenticatorLogLevel = 'fatal' | 'error' | 'warn' | 'info' | 'debug' | 'trace' | 'silent';

type SameSite = 'Strict' | 'Lax' | 'None';

type AuthenticatorParams = {
  region: string,
  userPoolId: string,
  userPoolAppId: string,
  userPoolDomain: string,
  cookieExpirationDays?: number,
  logLevel?: AuthenticatorLogLevel,
  sameSite?: SameSite,
  disableCookieDomain?: boolean,
};

declare module 'cognito-at-edge' {
  import { CloudFrontRequestEvent, CloudFrontRequestResult } from 'aws-lambda';

  export interface AuthenticatorInterface {
    handle(event: CloudFrontRequestEvent): Promise<CloudFrontRequestResult>,
  }

  export class Authenticator implements AuthenticatorInterface {
    constructor(params: AuthenticatorParams);

    handle(event: CloudFrontRequestEvent): Promise<CloudFrontRequestResult>;
  }
}

declare module 'cognito-at-edge/dist/util/cookie' {
  export interface Cookie {
    name: string,
    value: string,
  }

  export interface CookieAttributes {
    /**
     * The Domain attribute specifies those hosts to which the cookie will be sent.
     * Refer to {@link https://www.rfc-editor.org/rfc/rfc6265#section-4.1.2.3 RFC 6265 section 4.1.2.3.} for more details.
     */
    domain?: string,

    /**
     * The Expires attribute indicates the maximum lifetime of the cookie, represented as the date and time at which
     * the cookie expires.
     * Refer to {@link https://www.rfc-editor.org/rfc/rfc6265#section-4.1.2.1 RFC 6265 section 4.1.2.1.} for more details.
     */
    expires?: Date,

    /**
     * The HttpOnly attribute limits the scope of the cookie to HTTP requests.
     * Refer to {@link https://www.rfc-editor.org/rfc/rfc6265#section-4.1.2.6 RFC 6265 section 4.1.2.6.} for more details.
     */
    httpOnly?: boolean,

    /**
     * The SameSite attribute allows you to declare if your cookie should be restricted to a first-party or same-site context.
     * Refer to {@link https://httpwg.org/http-extensions/draft-ietf-httpbis-rfc6265bis.html#name-samesite-cookies RFC 6265 section 8.8.} for more details.
     */
    sameSite?: SameSite,

    /**
     * The Max-Age attribute indicates the maximum lifetime of the cookie, represented as the number of seconds until
     * the cookie expires.
     * Refer to {@link https://www.rfc-editor.org/rfc/rfc6265#section-4.1.2.2 RFC 6265 section 4.1.2.2.} for more details.
     */
    maxAge?: number,

    /**
     * The scope of each cookie is limited to a set of paths, controlled by the Path attribute.
     * Refer to {@link https://www.rfc-editor.org/rfc/rfc6265#section-4.1.2.4 RFC 6265 section 4.1.2.4.} for more details.
     */
    path?: string,

    /**
     * The Secure attribute limits the scope of the cookie to "secure" channels (where "secure" is defined by the user agent).
     * Refer to {@link https://www.rfc-editor.org/rfc/rfc6265#section-4.1.2.5 RFC 6265 section 4.1.2.5.} for more details.
     */
    secure?: boolean,
  }

  export class Cookies {
    static parse(cookiesString: string): Cookie[];
    static serialize(name: string, value: string, attributes: CookieAttributes): string;
  }
}
