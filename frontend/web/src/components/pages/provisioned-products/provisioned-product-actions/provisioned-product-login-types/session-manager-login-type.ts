import { LoginRequest, ProvisionedProductLoginType, LoginResponse } from '.';
import { provisioningAPI } from '../../../../../services';

export class SessionManagerLoginType extends ProvisionedProductLoginType {

  constructor(
    private readonly _provisioningApi: typeof provisioningAPI,
  ) { super(); }

  async doLoginPrivate(loginRequest: LoginRequest): Promise<LoginResponse> {
    const { projectId, provisionedProductId } = loginRequest.provisionedProduct;

    const credentials = await this._provisioningApi.getSessionCredentials(projectId, provisionedProductId);

    return {
      type: 'command',
      // The leading space keeps the credentials out of the history of a shell set to skip such commands.
      command: ` AWS_ACCESS_KEY_ID=${credentials.accessKeyId} ` +
        `AWS_SECRET_ACCESS_KEY=${credentials.secretAccessKey} ` +
        `AWS_SESSION_TOKEN=${credentials.sessionToken} ` +
        `aws ssm start-session --region ${credentials.region} --target ${credentials.instanceId}`,
    };
  }
}
