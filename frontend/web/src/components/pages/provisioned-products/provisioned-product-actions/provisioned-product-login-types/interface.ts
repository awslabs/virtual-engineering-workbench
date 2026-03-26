import { UserType } from '../../../../session-management/logged-user';
import { ProvisionedProduct } from '../../../../../services/API/proserve-wb-provisioning-api';

export type LoginResponseType = 'browser' | 'file';

export interface LoginRequest {
  user: UserType,
  userDomain: string,
  provisionedProduct: ProvisionedProduct,
  connectAddress?: string,
  vpnConnection: boolean,
  extendToAllMonitors: boolean,
}

export interface LoginContext {
  sessionId?: string,
  authToken?: string,
  portOverride?: number,
  loginUrl?: string,
}

export interface LoginResponse {
  type: LoginResponseType,
  loginUrl?: string,
  loginFile?: {
    loginFileContent: string,
    loginFileName: string,
  },
}