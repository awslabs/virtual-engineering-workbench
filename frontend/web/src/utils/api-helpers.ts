import { provisioningAPI } from '../services';

/* eslint @typescript-eslint/explicit-module-boundary-types: off, @typescript-eslint/no-explicit-any: off */
export async function extractErrorResponseMessage(e: any): Promise<string> {
  if (e.response && e.response instanceof Response) {
    const resp = await e.response.clone().json();
    return resp.message;
  }
  return e.message;
}

export async function extractErrorResponseValidationError(e: any): Promise<string> {
  if (e.response && e.response instanceof Response) {
    const resp = await e.response.clone().json();
    return resp.validationError || '';
  }
  return '';
}

export async function extractAllErrorMessages(e: any): Promise<string> {
  return `${await extractErrorResponseMessage(e)} ${await extractErrorResponseValidationError(e)}`;
}

export function getApis() {
  const serviceApis = {
    provisioningAPI: provisioningAPI,
  };
  return serviceApis;
}
