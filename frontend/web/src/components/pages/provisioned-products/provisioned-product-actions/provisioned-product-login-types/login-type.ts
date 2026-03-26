import { ProvisionedProduct } from '../../../../../services/API/proserve-wb-provisioning-api';
import { sanitizePath } from '../../../../../utils/os-path';
import { LoginContext, LoginRequest, LoginResponse } from './interface';

export abstract class ProvisionedProductLoginType {
  public doLogin(loginRequest: LoginRequest): Promise<LoginResponse> {
    return this.doLoginPrivate(loginRequest, {});
  }

  abstract doLoginPrivate(loginRequest: LoginRequest, context: LoginContext): Promise<LoginResponse>;

  protected getLoginFileName(provisionedProduct: ProvisionedProduct) {
    const instanceName = provisionedProduct.provisionedProductId || 'Unknown';
    return sanitizePath(
      `${provisionedProduct.productName}__${provisionedProduct.stage}__` +
        `${provisionedProduct.versionName}__${instanceName}`
    );
  }
}