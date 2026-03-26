/* eslint-disable @stylistic/max-len */
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Amplify } from 'aws-amplify';
import {
  DefaultApi,
  Configuration,
  CreateProductRequest,
  CreateProductVersionRequest,
  UpdateProductVersionRequest,
  GetProductsResponse,
  GetProductResponse,
  GetAmisResponse,
  GetProductVersionResponse,
  PromoteProductVersionRequest,
  RetireProductVersionRequest,
  GetAvailableProductVersionsResponse,
  GetAvailableProductsResponse,
  RestoreProductVersionResponse,
  ValidateProductVersionRequest,
  GetLatestTemplateResponse,
  GetLatestMajorVersionsResponse,
} from './proserve-wb-publishing-api';
import { getAccessToken } from '..';

const PUBLISHING_API_NAME = 'PublishingAPI';


/**
 *  Configure client SDK
 */
function prepareClient(): DefaultApi {
  const config = Amplify.getConfig();
  const basePath = config.API?.REST?.[PUBLISHING_API_NAME]?.endpoint || '';
  const apiConfig = new Configuration({ basePath: basePath });
  return new DefaultApi(apiConfig);
}

export const publishingAPI = {
  createProduct: async(projectId: string, body: CreateProductRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createProduct({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      createProductRequest: body
    });
  },

  createProductVersion: async(projectId: string, productId: string, body: CreateProductVersionRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createProductVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      createProductVersionRequest: body
    });
  },

  validateProductVersion: async(projectId: string, productId: string, body: ValidateProductVersionRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.validateProductVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      validateProductVersionRequest: body
    });
  },

  updateProductVersion: async(projectId: string, productId: string, versionId: string, body: UpdateProductVersionRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateProductVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      versionId: versionId,
      updateProductVersionRequest: body
    });
  },

  promoteProductVersion: async(projectId: string, productId: string, versionId: string, body: PromoteProductVersionRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.promoteProductVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      versionId: versionId,
      promoteProductVersionRequest: body
    });
  },

  archiveProduct: async(projectId: string, productId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.archiveProduct({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId
    });
  },

  getAvailableProducts: async(projectId: string, productType: string): Promise<GetAvailableProductsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getAvailableProducts({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productType: productType,
    });
  },

  getProducts: async(projectId: string): Promise<GetProductsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProducts({
      authorization: `Bearer ${access}`,
      projectId: projectId
    });
  },

  getProduct: async(projectId: string, productId: string): Promise<GetProductResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProduct({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId
    });
  },

  getAmis: async(projectId: string): Promise<GetAmisResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getAmis({
      authorization: `Bearer ${access}`,
      projectId: projectId
    });
  },

  getLatestTemplate: async(projectId: string, productId: string, versionId?: string): Promise<GetLatestTemplateResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getLatestTemplate({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      versionId: versionId,
    });
  },

  getLatestMajorVersions: async(projectId: string, productId: string): Promise<GetLatestMajorVersionsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getLatestMajorVersions({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
    });
  },

  getProductVersion: async (
    projectId: string,
    productId: string,
    versionId: string): Promise<GetProductVersionResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProductVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      versionId: versionId
    });
  },

  getAvailableProductVersions: async(projectId: string, productId: string, stage: string, region: string): Promise<GetAvailableProductVersionsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getAvailableProductVersions({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      region: region,
      stage: stage
    });
  },

  retryProductVersion: async(
    projectId: string,
    productId: string,
    versionId: string,
    awsAccountIds: string[]): Promise<void | object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.retryProductVersion({
      authorization: `Bearer ${access}`,
      projectId,
      productId,
      versionId,
      retryProductVersionRequest: {
        awsAccountIds,
      }
    });
  },

  retireProductVersion: async(projectId: string, productId: string, versionId: string, body: RetireProductVersionRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.retireProductVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      versionId: versionId,
      retireProductVersionRequest: body
    });
  },

  restoreProductVersion: async(
    projectId: string,
    productId: string,
    versionId: string): Promise<RestoreProductVersionResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.restoreProductVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      versionId: versionId
    });
  },

  setAsRecommendedVersion: async(
    projectId: string,
    productId: string,
    versionId: string): Promise<any> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.setRecommendedVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      productId: productId,
      versionId: versionId
    });
  },
};