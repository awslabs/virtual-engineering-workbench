import { CONSTANTS } from './constants';
import { LoginContext } from './interface';
import { ProvisionedProductLoginType } from './login-type';

export abstract class DCVLoginType extends ProvisionedProductLoginType {
  protected getPort(context: LoginContext): number {
    return context.portOverride ? context.portOverride : CONSTANTS.dcvPort;
  }

  protected getSessionId(context: LoginContext) {
    return context.sessionId ?? CONSTANTS.dcvDefaultSessionName;
  }

  protected getAuthToken(context: LoginContext) {
    return context.authToken ?? '';
  }
}
