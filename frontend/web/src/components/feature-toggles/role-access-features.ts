import { ProjectRoles } from '../../state';

export interface RoleAccessConfigItem {
  feature: string,
  rolesWithAccess: ProjectRoles[],
}

enum RoleAccessFeatureNames {
  UpdateUserProfile = 'UpdateUserProfile',
  GetUserProfile = 'GetUserProfile',
  GetWorkbenchMetadata = 'GetWorkbenchMetadata',
  GetProductVersionDetail = 'GetProductVersionDetail',
  ListAllProductVersions = 'ListAllProductVersions',
  ProductDetailsPage = 'ProductDetailsPage',
  GetInstanceDetails = 'GetInstanceDetails',
  ProvisionWorkbench = 'ProvisionWorkbench',
  RemoveWorkbench = 'RemoveWorkbench',
  WorkbenchDetailsPage = 'WorkbenchDetailsPage',
  ListAllProducts = 'ListAllProducts',
  ListMyWorkbenches = 'ListMyWorkbenches',
  ProgramAdministration = 'ProgramAdministration',
  ProgramDetails = 'ProgramDetails',
  AddUserToProgram = 'AddUserToProgram',
  RemovePlatformUserFromProgram = 'RemovePlatformUserFromProgram',
  ReassignRoleOfProgramUser = 'ReassignRoleOfProgramUser',
  ManageRoleFrontendAdmin = 'ManageRoleFrontendAdmin',
  ListAllUsersAndRoles = 'ListAllUsersAndRoles',
  OnboardAccount = 'OnboardAccount',
  ManageEnrolments = 'ManageEnrolments',
  ManageTechnologies = 'ManageTechnologies',
  ManagePlatform = 'ManagePlatform',
  ListAllPipelines = 'ListAllPipelines',
  ManageProducts = 'ManageProducts',
  ProductPackagingForceReleaseComponent = 'ProductPackagingForceReleaseComponent',
  ProductPackagingForceReleaseRecipe = 'ProductPackagingForceReleaseRecipe',
  ManageProdProducts = 'ManageProdProducts',
  ListProdAndQaProducts = 'ListProdAndQaProducts',
  ChooseStageInProductSelection = 'ChooseStageInProductSelection',
  OldAllWorkbenchesScreen = 'OldAllWorkbenchesScreen',
  ArchiveProducts = 'ArchiveProducts',
  ListMyVirtualTargets = 'ListMyVirtualTargets',
  RemoveVirtualTarget = 'RemoveVirtualTarget',
  ProvisionVirtualTarget = 'ProvisionVirtualTarget',
  ShowInactivePrograms = 'ShowInactivePrograms',

  ManageMandatoryComponents = 'ManageMandatoryComponents',
  ProvisionExperimentalWorkbench = 'ProvisionExperimentalWorkbench',
  AuthorizeUserIp = 'AuthorizeUserIp',
  ProvisionedProductsAdministration = 'ProvisionedProductsAdministration',
  Pipelines = 'Pipelines',
}

const ALL_ROLE_ACCESS = [
  ProjectRoles.Admin,
  ProjectRoles.ProgramOwner,
  ProjectRoles.PowerUser,
  ProjectRoles.PlatformUser,
  ProjectRoles.BetaUser,
  ProjectRoles.ProductContributor];

const roleAccessFeatures: RoleAccessConfigItem[] = [
  {
    feature: RoleAccessFeatureNames.UpdateUserProfile,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.GetUserProfile,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.GetWorkbenchMetadata,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.GetProductVersionDetail,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.ListAllProductVersions,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.ProductDetailsPage,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.GetInstanceDetails,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.ProvisionWorkbench,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.RemoveWorkbench,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.WorkbenchDetailsPage,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.ListMyWorkbenches,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.OldAllWorkbenchesScreen,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.ReassignRoleOfProgramUser,
    rolesWithAccess: [ProjectRoles.Admin, ProjectRoles.ProgramOwner]
  },
  {
    feature: RoleAccessFeatureNames.ListAllUsersAndRoles,
    rolesWithAccess: [ProjectRoles.Admin, ProjectRoles.ProgramOwner]
  },
  {
    feature: RoleAccessFeatureNames.ProgramAdministration,
    rolesWithAccess: [ProjectRoles.Admin]
  },
  {
    feature: RoleAccessFeatureNames.ProgramDetails,
    rolesWithAccess: [ProjectRoles.Admin, ProjectRoles.ProgramOwner]
  },
  {
    feature: RoleAccessFeatureNames.AddUserToProgram,
    rolesWithAccess: [ProjectRoles.Admin]
  },
  {
    feature: RoleAccessFeatureNames.RemovePlatformUserFromProgram,
    rolesWithAccess: [ProjectRoles.Admin]
  },
  {
    feature: RoleAccessFeatureNames.OnboardAccount,
    rolesWithAccess: [ProjectRoles.Admin]
  },
  {
    feature: RoleAccessFeatureNames.ManageEnrolments,
    rolesWithAccess: [ProjectRoles.ProgramOwner, ProjectRoles.Admin]
  },
  {
    feature: RoleAccessFeatureNames.ManageRoleFrontendAdmin,
    rolesWithAccess: [ProjectRoles.Admin],
  },
  {
    feature: RoleAccessFeatureNames.ManageTechnologies,
    rolesWithAccess: [ProjectRoles.Admin]
  },
  {
    feature: RoleAccessFeatureNames.ManagePlatform,
    rolesWithAccess: [ProjectRoles.Admin]
  },
  {
    feature: RoleAccessFeatureNames.ListAllPipelines,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.ManageProducts,
    rolesWithAccess: [
      ProjectRoles.ProductContributor,
      ProjectRoles.PowerUser,
      ProjectRoles.ProgramOwner,
      ProjectRoles.Admin]
  },
  {
    feature: RoleAccessFeatureNames.ManageProdProducts,
    rolesWithAccess: [ProjectRoles.PowerUser, ProjectRoles.ProgramOwner, ProjectRoles.Admin]
  },
  {
    feature: RoleAccessFeatureNames.ListAllProducts,
    rolesWithAccess: [
      ProjectRoles.Admin,
      ProjectRoles.ProgramOwner,
      ProjectRoles.PowerUser,
      ProjectRoles.ProductContributor]
  },
  {
    feature: RoleAccessFeatureNames.ListProdAndQaProducts,
    rolesWithAccess: [
      ProjectRoles.Admin,
      ProjectRoles.ProgramOwner,
      ProjectRoles.PowerUser,
      ProjectRoles.BetaUser,
      ProjectRoles.ProductContributor]
  },
  {
    feature: RoleAccessFeatureNames.ChooseStageInProductSelection,
    rolesWithAccess: [
      ProjectRoles.Admin,
      ProjectRoles.ProgramOwner,
      ProjectRoles.PowerUser,
      ProjectRoles.BetaUser,
      ProjectRoles.ProductContributor]
  },
  {
    feature: RoleAccessFeatureNames.ArchiveProducts,
    rolesWithAccess: [
      ProjectRoles.ProgramOwner,
      ProjectRoles.Admin
    ]
  },
  {
    feature: RoleAccessFeatureNames.ListMyVirtualTargets,
    rolesWithAccess: ALL_ROLE_ACCESS
  }, {

    feature: RoleAccessFeatureNames.RemoveVirtualTarget,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.ProvisionVirtualTarget,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.ProductPackagingForceReleaseComponent,
    rolesWithAccess: [
      ProjectRoles.Admin,
      ProjectRoles.ProgramOwner,
      ProjectRoles.PowerUser,
    ]
  },
  {
    feature: RoleAccessFeatureNames.ProductPackagingForceReleaseRecipe,
    rolesWithAccess: [
      ProjectRoles.Admin,
      ProjectRoles.ProgramOwner,
      ProjectRoles.PowerUser,
    ]
  },
  {
    feature: RoleAccessFeatureNames.ShowInactivePrograms,
    rolesWithAccess: [ProjectRoles.Admin]
  },

  {
    feature: RoleAccessFeatureNames.ManageMandatoryComponents,
    rolesWithAccess: [
      ProjectRoles.Admin
    ]
  },
  {
    feature: RoleAccessFeatureNames.ProvisionExperimentalWorkbench,
    rolesWithAccess: [
      ProjectRoles.Admin,
      ProjectRoles.ProgramOwner,
      ProjectRoles.PowerUser,
      ProjectRoles.BetaUser,
      ProjectRoles.ProductContributor]
  },
  {
    feature: RoleAccessFeatureNames.AuthorizeUserIp,
    rolesWithAccess: ALL_ROLE_ACCESS
  },
  {
    feature: RoleAccessFeatureNames.ProvisionedProductsAdministration,
    rolesWithAccess: [ProjectRoles.Admin, ProjectRoles.ProgramOwner]
  },
  {
    feature: RoleAccessFeatureNames.Pipelines,
    rolesWithAccess: [
      ProjectRoles.Admin,
      ProjectRoles.ProgramOwner,
    ]
  },
];

export default roleAccessFeatures;