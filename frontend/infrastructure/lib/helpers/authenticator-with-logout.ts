import { CloudFrontRequestEvent, CloudFrontRequestResult } from 'aws-lambda';
import { AuthenticatorInterface } from 'cognito-at-edge';

type CloudFrontHeader = {
  key?: string | undefined,
  value: string,
};

type ParamDict = {
  [key: string]: string,
};

class AuthenticatorWithLogout implements AuthenticatorInterface {

  private constructor(
    private readonly _inner: AuthenticatorInterface
  ) { }

  public static decorate(inner: AuthenticatorInterface): AuthenticatorInterface {
    return new AuthenticatorWithLogout(inner);
  }


  async handle(event: CloudFrontRequestEvent): Promise<CloudFrontRequestResult> {

    const result = await this._inner.handle(event);
    if (result?.headers === undefined) {
      return result;
    }
    if (!AuthenticatorWithLogout.isCloudFrontRedirectForLogout(event, result)) {
      return result;
    }
    const loginRedirectHeader = AuthenticatorWithLogout.getLoginRedirectHeader(result);
    if (loginRedirectHeader === undefined) {
      return result;
    }
    result.headers.location = [AuthenticatorWithLogout.alterRedirectQueryParams(loginRedirectHeader, [
      AuthenticatorWithLogout.injectIdpProviderName,
      AuthenticatorWithLogout.resetState
    ])];
    return result;

  }

  static isCloudFrontRedirectForLogout(request: CloudFrontRequestEvent, result: CloudFrontRequestResult) {
    return this.isLogOutUri(request) && this.isCloudFrontRedirectResponse(result);
  }

  static isLogOutUri(request: CloudFrontRequestEvent): boolean {
    const cf = request.Records[0];
    return cf.cf.request.uri === '/logout';
  }

  static isCloudFrontRedirectResponse(result: CloudFrontRequestResult): boolean {
    return !!result && 'status' in result && result.status === '302';
  }

  static getLoginRedirectHeader(result: CloudFrontRequestResult): CloudFrontHeader | undefined {
    if (result?.headers?.location?.length !== 1) {
      return undefined;
    }

    const locationHeader = result.headers.location[0];

    if (!/.+\/authorize\?.+/giu.test(locationHeader.value)) {
      return undefined;
    }

    return locationHeader;
  }

  static alterRedirectQueryParams(header: CloudFrontHeader, mappers: ((params: ParamDict) => ParamDict)[]) {
    let params = header.value.split('&').reduce((prev, curr) => {
      const keyValue = curr.split('=');
      if (keyValue.length === 1) {
        prev[keyValue[0]] = '';
      } else if (keyValue.length === 2) {
        prev[keyValue[0]] = keyValue[1];
      }
      return prev;
    }, {} as ParamDict);

    params = mappers.reduce((prev, curr) => curr(prev), params);
    const paramsArray: string[] = [];
    for (const [k, v] of Object.entries(params)) {
      paramsArray.push(`${k}=${v}`);
    }
    header.value = paramsArray.join('&');
    return header;
  }

  static injectIdpProviderName(params: ParamDict): ParamDict {
    params.identity_provider = 'na';
    return params;
  }

  static resetState(params: ParamDict): ParamDict {
    params.state = '/';
    return params;
  }

}

export { AuthenticatorWithLogout };
