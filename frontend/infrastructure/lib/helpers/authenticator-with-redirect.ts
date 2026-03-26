import { CloudFrontRequestEvent, CloudFrontRequestResult, CloudFrontRequest, CloudFrontResultResponse } from 'aws-lambda';
import { AuthenticatorInterface } from 'cognito-at-edge';
import pino from 'pino';

/* eslint no-console: "off" */
/* eslint complexity: "off" */

class AuthenticatorWithRedirect implements AuthenticatorInterface {

  private _logger = pino({
    level: 'info',
    base: null,
  });

  private constructor(
    private readonly _inner: AuthenticatorInterface
  ) { }

  public static decorate(inner: AuthenticatorInterface): AuthenticatorInterface {
    return new AuthenticatorWithRedirect(inner);
  }

  async handle(event: CloudFrontRequestEvent): Promise<CloudFrontRequestResult> {

    const request = event.Records[0].cf.request;

    // handle auth flow
    let result: CloudFrontRequestResult | null = null;
    try {
      result = await this._inner.handle(event);
    } catch (error) {
      this._logger.error(JSON.stringify({
        message: 'Unable to handle user AuthN/AuthZ.',
        error,
      }));
      return request;
    }

    // if user is authenticated, forward request
    if (AuthenticatorWithRedirect.isCloudFrontRequest(result)) {
      return result;
    }

    // if usr just authenticated successfully, forward request.
    if (AuthenticatorWithRedirect.isCognitoAtEdgeSuccessfulAuthResponse(result)) {
      return result;
    }

    // if user is not authenticated but wants to login, return result
    if (AuthenticatorWithRedirect.isCloudFrontRedirectResponse(result) && AuthenticatorWithRedirect.isRequestingLogin(request)) {
      return result;
    }

    // if user is not authenticated, return the request as-is
    return request;
  }

  static isRequestingLogin(request: CloudFrontRequest): boolean {
    return request.uri === '/login';
  }

  static isCloudFrontRequest(request: CloudFrontRequestResult): request is CloudFrontRequest {
    return (request as CloudFrontRequest).uri !== undefined;
  }

  static isCloudFrontResultResponse(response: CloudFrontRequestResult): response is CloudFrontResultResponse {
    return (response as CloudFrontResultResponse).status !== undefined;
  }

  static isCloudFrontRedirectResponse(result: CloudFrontRequestResult): boolean {
    return AuthenticatorWithRedirect.isCloudFrontResultResponse(result) && result.status === '302';
  }

  static isCognitoAtEdgeSuccessfulAuthResponse(result: CloudFrontRequestResult): boolean {
    return AuthenticatorWithRedirect.isCloudFrontResultResponse(result) && 'set-cookie' in (result.headers || {});
  }
}

export { AuthenticatorWithRedirect };
