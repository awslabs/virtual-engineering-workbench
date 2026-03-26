// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Amplify } from 'aws-amplify';
import {
  DefaultApi,
  Configuration,
  CreateComponentRequest,
  UpdateComponentRequest,
  GetComponentsResponse,
  GetComponentResponse,
  GetComponentVersionResponse,
  GetComponentVersionsResponse,
  CreateComponentVersionRequest,
  UpdateComponentVersionRequest,
  GetComponentVersionTestExecutionsResponse,
  GetComponentVersionTestExecutionLogsUrlResponse,
  CreateRecipeRequest,
  GetRecipesResponse,
  GetRecipeVersionsResponse,
  GetRecipeResponse,
  GetRecipeVersionResponse,
  CreateRecipeVersionRequest,
  GetComponentsVersionsResponse,
  UpdateRecipeVersionRequest,
  GetRecipeVersionTestExecutionsResponse,
  GetRecipeVersionTestExecutionLogsUrlResponse,
  GetPipelinesResponse,
  GetRecipesVersionsResponse,
  CreatePipelineRequest,
  UpdatePipelineRequest,
  GetPipelinesAllowedBuildTypesResponse,
  GetPipelineResponse,
  GetImagesResponse,
  CreateImageRequest,
  GetMandatoryComponentsListsResponse,
  GetMandatoryComponentsListResponse,
  UpdateMandatoryComponentsListRequest,
  CreateMandatoryComponentsListRequest,
  ValidateComponentVersionRequest,
  CreateComponentResponse,
} from './proserve-wb-packaging-api';
import { getAccessToken } from '..';

const PACKAGING_API_NAME = 'PackagingAPI';

/**
 *  Configure client SDK
 */
function prepareClient(): DefaultApi {
  const config = Amplify.getConfig();
  const basePath = config.API?.REST?.[PACKAGING_API_NAME]?.endpoint || '';
  const apiConfig = new Configuration({ basePath: basePath });
  return new DefaultApi(apiConfig);
}

export const packagingAPI = {
  archiveComponent: async (projectId: string, componentId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.archiveComponent({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      componentId: componentId,
      body: {},
    });
  },

  createComponent: async (
    projectId: string, body: CreateComponentRequest
  ): Promise<CreateComponentResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createComponent({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      createComponentRequest: body,
    });
  },

  getComponents: async(projectId: string): Promise<GetComponentsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getComponents({
      authorization: `Bearer ${access}`,
      projectId: projectId,
    });
  },

  getComponent: async(projectId: string, componentId: string): Promise<GetComponentResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getComponent({
      authorization: `Bearer ${access}`,
      projectId,
      componentId,
    });
  },

  shareComponent: async(projectId: string, componentId: string, projectIds: string[]): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.shareComponent({
      authorization: `Bearer ${access}`,
      projectId,
      componentId,
      shareComponentRequest: { projectIds },
    });
  },

  updateComponent: async(
    projectId: string,
    componentId: string,
    updateComponentRequest: UpdateComponentRequest
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateComponent({
      authorization: `Bearer ${access}`,
      projectId,
      componentId,
      updateComponentRequest,
    });
  },

  getComponentVersion: async(
    projectId: string,
    componentId: string,
    versionId: string
  ): Promise<GetComponentVersionResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getComponentVersion({
      authorization: `Bearer ${access}`,
      projectId,
      componentId,
      versionId,
    });
  },

  getComponentVersions: async(
    projectId: string,
    componentId: string
  ): Promise<GetComponentVersionsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getComponentVersions({
      authorization: `Bearer ${access}`,
      projectId,
      componentId,
    });
  },

  createComponentVersion: async(
    projectId: string,
    componentId: string,
    createComponentVersionRequest: CreateComponentVersionRequest
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createComponentVersion({
      authorization: `Bearer ${access}`,
      projectId,
      componentId,
      createComponentVersionRequest,
    });
  },

  updateComponentVersion: async(
    projectId: string,
    componentId: string,
    versionId: string,
    body: UpdateComponentVersionRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateComponentVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      versionId: versionId,
      componentId: componentId,
      updateComponentVersionRequest: body,
    });
  },

  releaseComponentVersion: async(
    projectId: string,
    componentId: string,
    versionId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.releaseComponentVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      versionId: versionId,
      componentId: componentId,
      body: {},
    });
  },

  retireComponentVersion: async(
    projectId: string,
    componentId: string,
    versionId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.retireComponentVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      versionId: versionId,
      componentId: componentId,
      body: {},
    });
  },

  getComponentVersionTestExecutions: async(
    projectId: string,
    componentId: string,
    versionId: string,
  ): Promise<GetComponentVersionTestExecutionsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getComponentVersionTestExecutions({
      authorization: `Bearer ${access}`,
      projectId,
      componentId,
      versionId,
    });
  },

  getComponentVersionTestExecutionLogsUrl: async(
    projectId: string,
    componentId: string,
    versionId: string,
    testExecutionId: string,
    instanceId: string
  ): Promise<GetComponentVersionTestExecutionLogsUrlResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getComponentVersionTestExecutionLogsUrl({
      authorization: `Bearer ${access}`,
      projectId,
      componentId,
      versionId,
      testExecutionId,
      instanceId,
    });
  },

  getComponentsVersions: async(
    projectId: string,
    status: string[],
    platform: string,
    os: string,
    arch: string,
    global?: boolean,
  ): Promise<GetComponentsVersionsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getComponentsVersions({
      authorization: `Bearer ${access}`,
      projectId,
      status,
      platform,
      os,
      arch,
      ...global && { global: true },
    });
  },

  archiveRecipe: async (projectId: string, recipeId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.archiveRecipe({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      recipeId: recipeId,
      body: {},
    });
  },

  createRecipe: async(projectId: string, body: CreateRecipeRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createRecipe({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      createRecipeRequest: body,
    });
  },

  getRecipes: async(projectId: string): Promise<GetRecipesResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getRecipes({
      authorization: `Bearer ${access}`,
      projectId: projectId,
    });
  },

  getRecipe: async(projectId: string, recipeId: string): Promise<GetRecipeResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getRecipe({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      recipeId: recipeId,
    });
  },

  getRecipeVersions: async(projectId: string, recipeId: string): Promise<GetRecipeVersionsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getRecipeVersions({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      recipeId: recipeId,
    });
  },
  getRecipeVersion: async(
    projectId: string,
    recipeId: string,
    versionId: string):
  Promise<GetRecipeVersionResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getRecipeVersion({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      recipeId: recipeId,
      versionId: versionId,
    });
  },

  createRecipeVersion: async(
    projectId: string,
    recipeId: string,
    createRecipeVersionRequest: CreateRecipeVersionRequest
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createRecipeVersion({
      authorization: `Bearer ${access}`,
      projectId,
      recipeId,
      createRecipeVersionRequest,
    });
  },

  updateRecipeVersion: async(
    projectId: string,
    recipeId: string,
    versionId: string,
    updateRecipeVersionRequest: UpdateRecipeVersionRequest
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateRecipeVersion({
      authorization: `Bearer ${access}`,
      projectId,
      recipeId,
      versionId,
      updateRecipeVersionRequest,
    });
  },

  releaseRecipeVersion: async(
    projectId: string,
    recipeId: string,
    versionId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.releaseRecipeVersion({
      authorization: `Bearer ${access}`,
      projectId,
      recipeId,
      versionId,
      body: {},
    });
  },

  retireRecipeVersion: async(
    projectId: string,
    recipeId: string,
    versionId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.retireRecipeVersion({
      authorization: `Bearer ${access}`,
      projectId,
      recipeId,
      versionId,
      body: {},
    });
  },

  getRecipeVersionTestExecutions: async(
    projectId: string,
    recipeId: string,
    versionId: string,
  ): Promise<GetRecipeVersionTestExecutionsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getRecipeVersionTestExecutions({
      authorization: `Bearer ${access}`,
      projectId,
      recipeId,
      versionId,
    });
  },

  getRecipeVersionTestExecutionLogsUrl: async(
    projectId: string,
    recipeId: string,
    versionId: string,
    testExecutionId: string,
  ): Promise<GetRecipeVersionTestExecutionLogsUrlResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getRecipeVersionTestExecutionLogsUrl({
      authorization: `Bearer ${access}`,
      projectId,
      recipeId,
      versionId,
      testExecutionId,
    });
  },

  getRecipesVersions: async(
    projectId: string,
    status: string,
  ): Promise<GetRecipesVersionsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getRecipesVersions({
      authorization: `Bearer ${access}`,
      projectId,
      status,
    });
  },

  getPipelines: async(projectId: string): Promise<GetPipelinesResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getPipelines({
      authorization: `Bearer ${access}`,
      projectId: projectId,
    });
  },

  getPipeline: async(projectId: string, pipelineId: string): Promise<GetPipelineResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getPipeline({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      pipelineId: pipelineId,
    });
  },

  createPipeline: async(projectId: string, body: CreatePipelineRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createPipeline({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      createPipelineRequest: body,
    });
  },

  updatePipeline: async(
    projectId: string,
    pipelineId: string,
    body: UpdatePipelineRequest
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updatePipeline({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      pipelineId: pipelineId,
      updatePipelineRequest: body,
    });
  },

  retirePipeline: async(
    projectId: string,
    pipelineId: string
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.retirePipeline({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      pipelineId: pipelineId,
      body: {},
    });
  },

  getAllowedBuildTypes: async(
    projectId: string,
    recipeId: string,
  ): Promise<GetPipelinesAllowedBuildTypesResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getPipelinesAllowedBuildTypes({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      recipeId: recipeId,
    });
  },

  getImages: async(projectId: string): Promise<GetImagesResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getImages({
      authorization: `Bearer ${access}`,
      projectId: projectId,
    });
  },

  createImage: async(projectId: string, body: CreateImageRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createImage({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      createImageRequest: body,
    });
  },

  getMandatoryComponentsLists: async(
    projectId: string,
  ): Promise<GetMandatoryComponentsListsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getMandatoryComponentsLists({
      authorization: `Bearer ${access}`,
      projectId: projectId,
    });
  },

  getMandatoryComponentsList: async(
    projectId: string,
    mandatoryComponentsListPlatform: string,
    mandatoryComponentsListArchitecture: string,
    mandatoryComponentsListOsVersion: string
  ): Promise<GetMandatoryComponentsListResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getMandatoryComponentsList({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      mandatoryComponentsListArchitecture: mandatoryComponentsListArchitecture,
      mandatoryComponentsListOsVersion: mandatoryComponentsListOsVersion,
      mandatoryComponentsListPlatform: mandatoryComponentsListPlatform,
    });
  },

  updateMandatoryComponentsList: async(
    projectId: string,
    body: UpdateMandatoryComponentsListRequest
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateMandatoryComponentsList({
      authorization: `Bearer ${access}`,
      projectId,
      updateMandatoryComponentsListRequest: body,
    });
  },

  createMandatoryComponentsList: async(
    projectId: string,
    createMandatoryComponentsListRequest: CreateMandatoryComponentsListRequest
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createMandatoryComponentsList({
      authorization: `Bearer ${access}`,
      projectId,
      createMandatoryComponentsListRequest,
    });
  },

  validateComponentVersion: async (
    projectId: string,
    componentId: string,
    validateComponentVersionRequest: ValidateComponentVersionRequest
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.validateComponentVersion({
      authorization: `Bearer ${access}`,
      projectId,
      componentId,
      validateComponentVersionRequest,
    });
  },
};

export type PackagingAPI = typeof packagingAPI;