// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Amplify } from 'aws-amplify';
import {
  DefaultApi,
  Configuration,
  GetAvailableProductsResponse,
  GetProvisionedProductResponse,
  GetAvailableProductVersionsResponse,
  ProvisioningParameter,
  LaunchProductRequest,
  GetProvisionedProductsResponse,
  GetUserProfileResponse,
  UpdateUserProfileRequest,
  UpdateProvisionedProductRequest,
  GetProvisionedProductSSHKeyResponse,
  AdditionalConfiguration,
  GetProvisionedProductUserSecretResponse,
  GetAllProvisionedProductsResponse,
} from './proserve-wb-provisioning-api';
import { getAccessToken } from '..';

const PROVISIONING_API_NAME = 'ProvisioningAPI';

// TODO: use type of productType from api spec. Currently, not available
export type ProvisionedProductType = string; // 'virtualTarget' | 'workbench'

/**
 *  Configure client SDK
 */
function prepareClient(): DefaultApi {
  const config = Amplify.getConfig();
  const basePath = config.API?.REST?.[PROVISIONING_API_NAME]?.endpoint || '';
  const apiConfig = new Configuration({ basePath: basePath });
  return new DefaultApi(apiConfig);
}


export const provisioningAPI = {
  getAvailableProducts: async (
    projectId: string,
    productType: ProvisionedProductType
  ): Promise<GetAvailableProductsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getAvailableProducts({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productType: productType,
    });
  },

  getProvisionedProduct: async (
    projectId: string,
    provisionedProductId: string
  ): Promise<GetProvisionedProductResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProvisionedProduct({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      provisionedProductId: provisionedProductId,
    });
  },

  getProjectProvisionedProducts: async (
    projectId: string
  ): Promise<GetAllProvisionedProductsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProjectProvisionedProducts({
      authorization: `Bearer ${access}`,
      projectId: projectId,
    });
  },


  getPaginatedProvisionedProducts: async (
    projectId: string,
    nextToken?: string,
  ): Promise<GetAllProvisionedProductsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProjectPaginatedProvisionedProducts({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      pagingKey: nextToken
    });
  },

  getAvailableProductVersions: async (
    projectId: string,
    productId: string,
    stage: string,
    region: string
  ): Promise<GetAvailableProductVersionsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getAvailableProductVersions({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      stage: stage,
      region: region,
    });
  },

  launchProduct: async (
    projectId: string,
    productId: string,
    versionId: string,
    provisioningParameters: ProvisioningParameter[],
    stage: string,
    region: string,
    additionalConfigurations?: AdditionalConfiguration[]
  ): Promise<object> => {
    const access = await getAccessToken();
    const request: LaunchProductRequest = {
      productId: productId,
      provisioningParameters: provisioningParameters,
      versionId: versionId,
      stage: stage,
      region: region,
      additionalConfigurations: additionalConfigurations
    };
    const api = prepareClient();
    return api.launchProduct({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      launchProductRequest: request,
    });
  },

  upgradeProvisionedProduct: async (
    projectId: string,
    provisionedProductId: string,
    provisioningParameters: ProvisioningParameter[],
    versionId: string
  ): Promise<object> => {
    const access = await getAccessToken();
    const updateProvisionedProductRequest: UpdateProvisionedProductRequest = {
      provisioningParameters,
      versionId
    };
    const api = prepareClient();
    return api.updateProvisionedProduct({
      authorization: `Bearer ${access}`,
      projectId,
      provisionedProductId,
      updateProvisionedProductRequest,
    });
  },

  removeProvisionedProduct: async (
    projectId: string,
    provisionedProductId: string
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.removeProvisionedProduct({
      authorization: `Bearer ${access}`,
      projectId,
      provisionedProductId,
    });
  },

  removeProvisionedProducts: async (
    projectId: string,
    provisionedProductIds: string[]
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.removeProvisionedProducts({
      authorization: `Bearer ${access}`,
      projectId,
      removeProvisionedProductsRequest: {
        provisionedProductIds
      }
    });
  },

  startProvisionedProduct: async (
    projectId: string,
    provisionedProductId: string
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.startProvisionedProduct({
      authorization: `Bearer ${access}`,
      projectId,
      provisionedProductId,
    });
  },

  stopProvisionedProduct: async (
    projectId: string,
    provisionedProductId: string
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.stopProvisionedProduct({
      authorization: `Bearer ${access}`,
      projectId,
      provisionedProductId,
    });
  },

  stopProvisionedProducts: async (
    projectId: string,
    provisionedProductIds: string[]
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.stopProvisionedProducts({
      authorization: `Bearer ${access}`,
      projectId,
      stopProvisionedProductsRequest: {
        provisionedProductIds
      }
    });
  },

  getProvisionedProducts: async (
    projectId: string,
    productType: ProvisionedProductType
  ): Promise<GetProvisionedProductsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProvisionedProducts({
      authorization: `Bearer ${access}`,
      projectId,
      productType,
    });
  },

  getUserProfile: async (): Promise<GetUserProfileResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getUserProfile({
      authorization: `Bearer ${access}`
    });
  },

  updateUserProfile: async (updateUserProfileRequest: UpdateUserProfileRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateUserProfile({
      authorization: `Bearer ${access}`,
      updateUserProfileRequest,
    });
  },

  getSSHKey: async(projectId: string, provisionedProductId: string):
  Promise<GetProvisionedProductSSHKeyResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProvisionedProductSSHKey({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      provisionedProductId: provisionedProductId,
    });
  },

  getUserCredential: async(projectId: string, provisionedProductId: string):
  Promise<GetProvisionedProductUserSecretResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProvisionedProductUserCredentials({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      provisionedProductId: provisionedProductId,
    });
  },

  authorizeUserIpAddress: async (projectId: string, provisionedProductId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.authorizeUserIpAddress({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      provisionedProductId: provisionedProductId
    });
  },
};

export type ServiceAPI = typeof provisioningAPI;