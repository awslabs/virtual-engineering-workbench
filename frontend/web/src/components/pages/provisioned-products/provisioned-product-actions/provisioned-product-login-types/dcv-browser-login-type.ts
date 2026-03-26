import { LoginContext, LoginRequest, LoginResponse } from '.';
import { CONSTANTS } from './constants';
import { DCVLoginType } from './dcv-login-type';
import { i18n } from './translations';

export class DCVBrowserLoginType extends DCVLoginType {

  doLoginPrivate(loginRequest: LoginRequest, context: LoginContext): Promise<LoginResponse> {
    if (!loginRequest.connectAddress) {
      throw Error(i18n.errorConnectionAddress);
    }

    let params = `#${this.getSessionId(context)}`;
    if (context.authToken) {
      params = `?authToken=${context.authToken}${params}`;
    }

    const port = this.getPort(context);

    const loginUrl = port !== CONSTANTS.https ?
      `https://${loginRequest.connectAddress}:${port}/${params}` :
      `https://${loginRequest.connectAddress}/${params}`;

    return Promise.resolve({
      type: 'browser',
      loginUrl: loginUrl,
    });
  }
}
