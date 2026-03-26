import { LoginRequest, ProvisionedProductLoginType, LoginResponse } from '.';
import { provisioningAPI } from '../../../../../services';

export class SSHLoginType extends ProvisionedProductLoginType {

  constructor(
    private readonly _provisioningApi: typeof provisioningAPI,
  ) { super(); }

  async doLoginPrivate(loginRequest: LoginRequest): Promise<LoginResponse> {
    const instanceName = loginRequest.provisionedProduct.provisionedProductId || 'Unknown';

    const keyResp = await this._provisioningApi.getSSHKey(
      loginRequest.provisionedProduct.projectId,
      loginRequest.provisionedProduct.provisionedProductId,
    );

    return {
      type: 'file',
      loginFile: {
        loginFileContent: keyResp.sshKey ?? '',
        loginFileName: `connect_${instanceName}.key`,
      }
    };
  }
}