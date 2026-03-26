import { DCVLoginType } from './dcv-login-type';
import { LoginContext, LoginRequest, LoginResponse } from './interface';
import { i18n } from './translations';

export class DCVFileLoginType extends DCVLoginType {
  doLoginPrivate(loginRequest: LoginRequest, context: LoginContext): Promise<LoginResponse> {
    if (!loginRequest.connectAddress) {
      throw Error(i18n.errorConnectionAddress);
    }

    const username = loginRequest.user?.userId.toUpperCase() || '-';
    const dcvBody =
      '[connect]\n' +
      `host=${loginRequest.connectAddress}\n` +
      `port=${this.getPort(context)}\n` +
      `user=${loginRequest.userDomain.toLocaleLowerCase()}\\${username.toLocaleLowerCase()}\n` +
      `sessionid=${this.getSessionId(context)}\n` +
      `authtoken=${this.getAuthToken(context)}\n\n` +
      '[version]\n' +
      'format=1.0\n\n' +
      '[options]\n' +
      'fullscreen=true\n' +
      `useallmonitors=${loginRequest.extendToAllMonitors}`;

    return Promise.resolve({
      type: 'file',
      loginFile: {
        loginFileContent: dcvBody,
        loginFileName: `${this.getLoginFileName(loginRequest.provisionedProduct)}.dcv`,
      }
    });
  }
}
