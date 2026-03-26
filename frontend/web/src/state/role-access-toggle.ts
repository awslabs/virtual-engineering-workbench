// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { atom } from 'recoil';
import roleAccessFeatures from '../components/feature-toggles/role-access-features';
import { ProjectRoles } from '.';

export enum RoleBasedFeature {
  ProgramAdministration,
  ProgramDetails,
  AddUserToProgram,
  RemovePlatformUserFromProgram,
  OnboardAccount,
  ReassignRoleOfProgramUser,
  ManageRoleFrontendAdmin,
  ListAllUsersAndRoles,
  ListMyWorkbenches,
  ListAllProducts,
  WorkbenchDetailsPage,
  RemoveWorkbench,
  ProvisionWorkbench,
  GetInstanceDetails,
  ProductDetailsPage,
  ListAllProductVersions,
  GetProductVersionDetail,
  GetWorkbenchMetadata,
  GetUserProfile,
  UpdateUserProfile,
  SeeProgramsDropdownItem,
  ListAllPrograms,
  ManageEnrolments,
  ManageTechnologies,
  ManagePlatform,
  ListAllPipelines,
  ManageProducts,
  ManageProdProducts,
  ListProdAndQaProducts,
  ChooseStageInProductSelection,
  OldAllWorkbenchesScreen,
  ArchiveProducts,
  ListMyVirtualTargets,
  RemoveVirtualTarget,
  ProvisionVirtualTarget,
  ProductPackagingForceReleaseComponent,
  ProductPackagingForceReleaseRecipe,
  ShowInactivePrograms,

  ManageMandatoryComponents,
  ProvisionExperimentalWorkbench,
  ProvisionedProductsAdministration,
  Pipelines,
}

export interface RoleAccessItem {
  feature: RoleBasedFeature,
  rolesWithAccess: ProjectRoles[],
}

function loadRoleAccessItems():RoleAccessItem[] {
  const items:RoleAccessItem[] = [];
  for (const fet of roleAccessFeatures) {
    items.push({
      feature: RoleBasedFeature[fet.feature as keyof typeof RoleBasedFeature],
      rolesWithAccess: fet.rolesWithAccess,
    });
  }
  return items;
}

export const roleAccessToggleState = atom<RoleAccessItem[]>({
  key: 'roleAccessToggles',
  default: loadRoleAccessItems()
});
