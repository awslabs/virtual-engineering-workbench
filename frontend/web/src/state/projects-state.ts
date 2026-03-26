// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { atom, selector } from 'recoil';

export enum ProjectRoles {
  Admin = 'ADMIN',
  PowerUser = 'POWER_USER',
  ProgramOwner = 'PROGRAM_OWNER',
  PlatformUser = 'PLATFORM_USER',
  BetaUser = 'BETA_USER',
  ProductContributor = 'PRODUCT_CONTRIBUTOR'
}

const USER_ROLES = new Set<string>([
  ProjectRoles.PlatformUser,
  ProjectRoles.PowerUser,
  ProjectRoles.BetaUser,
  ProjectRoles.ProductContributor]);
const ADMIN_ROLES = new Set<string>([ProjectRoles.Admin, ProjectRoles.ProgramOwner]);
const ALL_ROLES = new Set<string>([
  ...USER_ROLES,
  ...ADMIN_ROLES,
]);

export interface Project {
  id: string,
  name: string,
  description: string,
  isActive: boolean,
  roles?: string[],
}

export const projectsState = atom<Project[]>({
  key: 'projects',
  default: []
});

export const filteredProjectsForAdminOwnerState = selector<Project[]>({
  key: 'filteredProjectsForAdminOwner',
  get: ({ get }) => {
    const list = get(projectsState);

    return list.filter(
      (project: Project) => project.
        roles?.
        some(x => ADMIN_ROLES.has(x))
    );
  },
});

export const filteredProjectsForUserState = selector<Project[]>({
  key: 'filteredProjectsForUser',
  get: ({ get }) => {
    const list = get(projectsState);

    return list.filter(
      (project: Project) => project.
        roles?.
        some(x => USER_ROLES.has(x))
    );
  },
});

export const filteredAvailableProjectsState = selector<Project[]>({
  key: 'filteredAvailableProjectsState',
  get: ({ get }) => {
    const list = get(projectsState);

    return list.filter((project: Project) => !project.roles?.some(x => ALL_ROLES.has(x)));
  },
});

export const filteredProjectsWithAnyRole = selector<Project[]>({
  key: 'filteredProjectsWithAnyRole',
  get: ({ get }) => {
    const list = get(projectsState);

    return list.filter(
      (project: Project) => project.
        roles?.
        some(x => ALL_ROLES.has(x))
    );
  },
});
