import { WORKBENCH_CONNECTION_TYPE } from '../../../workbenches/workbenches.static';
import { provisioningAPI } from '../../../../../services';
import {
  DCVBrowserLoginType,
  DCVFileLoginType,
  RDPLoginType,
  SSHLoginType,
  ProvisionedProductLoginType
} from '.';
import { i18n } from './translations';

export class LoginConfig {

  constructor(
    private readonly _loginTypes: Map<string, ProvisionedProductLoginType> = new Map(),
  ) { }

  public registerLoginOption(login: string, loginType: ProvisionedProductLoginType) {
    this._loginTypes.set(login, loginType);
    return this;
  }

  public getLoginType(login: string): ProvisionedProductLoginType {
    if (!this._loginTypes.has(login)) {
      throw new Error(i18n.errorLogin(login));
    }
    return this._loginTypes.get(login) as ProvisionedProductLoginType;
  }

  public static initLoginConfig() {
    return new LoginConfig().
      registerLoginOption(
        WORKBENCH_CONNECTION_TYPE.RDP,
        new RDPLoginType()).
      registerLoginOption(
        WORKBENCH_CONNECTION_TYPE.SSH,
        new SSHLoginType(provisioningAPI)).
      registerLoginOption(
        WORKBENCH_CONNECTION_TYPE.DcvBrowser,
        new DCVBrowserLoginType()).
      registerLoginOption(
        WORKBENCH_CONNECTION_TYPE.DcvFile,
        new DCVFileLoginType());
  }
}
