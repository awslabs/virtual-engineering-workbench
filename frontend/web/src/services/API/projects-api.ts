// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { Amplify } from 'aws-amplify';
import {
  DefaultApi,
  Configuration,
  GetProjectAccountsResponse,
  GetProjectsResponse,
  OnBoardProjectAccountRequest,
  GetProjectAssignmentsResponse,
  GetUserRolesResponse,
  AssignUserRequest,
  ReAssignUsersRequest,
  GetProjectEnrolmentsResponse,
  UpdateEnrolmentsRequest,
  GetTechnologiesResponse,
  AddTechnologyRequest,
  UpdateTechnologyRequest,
  RemoveUsersRequest,
} from './proserve-wb-projects-api';
import { getAccessToken } from '..';

const DEFAULT_PAGE_SIZE = '10';
const PROJECTS_API_NAME = 'ProjectsAPI';
const CACHE_CONTROL_HEADER = 'Cache-Control';
const AUTHORIZATION_HEADER = 'Authorization';

/**
 *  Configure client SDK
 */
function prepareClient(): DefaultApi {
  const config = Amplify.getConfig();
  const basePath = config.API?.REST?.[PROJECTS_API_NAME]?.endpoint || '';
  const apiConfig = new Configuration({ basePath: basePath });
  return new DefaultApi(apiConfig);
}

export const projectsAPI = {

  getProjects: async(): Promise<GetProjectsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProjects({
      authorization: `Bearer ${access}`,
      pageSize: Number(DEFAULT_PAGE_SIZE)
    });
  },

  getProjectEnrolments: async(
    projectId: string,
    pageSize: string,
    nextToken?: string,
    status?: string
  ): Promise<GetProjectEnrolmentsResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProjectEnrolments({
      projectId,
      authorization: `Bearer ${access}`,
      pageSize: Number(pageSize || DEFAULT_PAGE_SIZE),
      nextToken: nextToken ? JSON.parse(nextToken) : undefined,
      status
    });
  },

  updateEnrolments: async(projectId: string, body: UpdateEnrolmentsRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateEnrolments({
      projectId,
      authorization: `Bearer ${access}`,
      updateEnrolmentsRequest: body
    });
  },

  getProjectAccounts: async (
    projectId: string,
    invalidateCache?: boolean
  ): Promise<GetProjectAccountsResponse> => {
    const access = await getAccessToken();

    const headers: { [key: string]: string } = {};
    headers[AUTHORIZATION_HEADER] = `Bearer ${access}`;
    if (invalidateCache) {
      headers[CACHE_CONTROL_HEADER] = 'max-age=0';
    }

    const api = prepareClient();
    return api.getProjectAccounts({
      authorization: `Bearer ${access}`,
      projectId: projectId
    },
    { headers: headers });
  },

  enrolUser: async(projectId: string, body: object): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.enrolUser({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      body
    });
  },

  onboardProjectAccount: async(projectId: string, body: OnBoardProjectAccountRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.addProjectAccount({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      onBoardProjectAccountRequest: body
    });
  },

  reonboardProjectAccount: async(projectId: string, accountIds: string[]): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.reonboardProjectAccount({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      reonboardProjectAccountRequest: {
        accountIds: accountIds
      }
    });
  },

  getProjectUsers: async (
    projectId: string,
  ): Promise<GetProjectAssignmentsResponse> => {
    const access = await getAccessToken();
    const headers: { [key: string]: string } = {};
    headers[CACHE_CONTROL_HEADER] = 'max-age=0, no-cache';
    headers[AUTHORIZATION_HEADER] = `Bearer ${access}`;
    const api = prepareClient();
    return api.getProjectUsers({
      authorization: `Bearer ${access}`,
      projectId: projectId,
    },
    { headers: headers });
  },

  getUserRoles: async(projectId: string, userId: string): Promise<GetUserRolesResponse> => {
    const access = await getAccessToken();
    const headers: { [key: string]: string } = {};
    headers[CACHE_CONTROL_HEADER] = 'max-age=0, no-cache';
    headers[AUTHORIZATION_HEADER] = `Bearer ${access}`;
    const api = prepareClient();
    return api.getUserRoles({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      userId: userId
    },
    { headers: headers });
  },

  assignProjectUser: async(projectId: string, body: AssignUserRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.addProjectUser({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      assignUserRequest: body
    });
  },

  removeProjectUser: async(projectId: string, userId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.removeProjectUser({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      userId: userId
    });
  },

  removeProjectUsers: async(projectId: string, body: RemoveUsersRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.removeProjectUsers({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      removeUsersRequest: body
    });
  },

  reassignProjectUsers: async(
    projectId: string,
    body: ReAssignUsersRequest
  ): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.reAssignProjectUsers({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      reAssignUsersRequest: body
    });
  },

  getTechnologies: async(
    projectId: string,
    pageSize: string,
    nextToken?: string): Promise<GetTechnologiesResponse> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getTechnologies({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      pageSize: Number(pageSize),
      nextToken: nextToken ? JSON.parse(nextToken) : undefined,
    });
  },

  addTechnology: async(projectId: string, body: AddTechnologyRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.addTechnology({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      addTechnologyRequest: body
    });
  },

  updateTechnology: async(
    projectId: string,
    techId: string,
    body: UpdateTechnologyRequest): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateTechnology({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      techId: techId,
      updateTechnologyRequest: body
    });
  },

  deleteTechnology: async(projectId: string, techId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.deleteTechnology({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      techId: techId,
    });
  },

  activateProjectAccount: async(projectId: string, accountId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateProjectAccount({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      accountId: accountId,
      updateProjectAccountRequest: {
        accountStatus: 'Active'
      }
    });
  },

  deactivateProjectAccount: async(projectId: string, accountId: string): Promise<object> => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateProjectAccount({
      authorization: `Bearer ${access}`,
      projectId: projectId,
      accountId: accountId,
      updateProjectAccountRequest: {
        accountStatus: 'Inactive'
      }
    });
  },

  createProject: async(
    name: string,
    description: string,
    isActive: boolean
  ) => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.createProject({
      authorization: `Bearer ${access}`,
      createProjectRequest: {
        name: name,
        description: description,
        isActive: isActive
      }
    });
  },

  getProject: async(
    projectId: string
  ) => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.getProject({
      authorization: `Bearer ${access}`,
      projectId
    });
  },

  updateProject: async(
    projectId: string,
    name: string,
    description: string,
    isActive: boolean
  ) => {
    const access = await getAccessToken();
    const api = prepareClient();
    return api.updateProject({
      authorization: `Bearer ${access}`,
      projectId,
      updateProjectRequest: {
        name: name,
        description: description,
        isActive: isActive
      }
    });
  },

};