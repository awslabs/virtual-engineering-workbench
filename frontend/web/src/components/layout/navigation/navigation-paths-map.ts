import { RouteNames } from './navigation.static';

type RouteConfig = {
  path: string,
};

export const ROUTES: { [key in RouteNames]: RouteConfig } = {
  ProvisionWorkbench: {
    path: '/available-products-new/:id',
  },
  ProvisionWorkbenchUseMapping: {
    path: '/available-products-new/:id/mapping/:jobName/:platformType',
  },
  UpgradeWorkbenchV2: {
    path: '/my-workbenches/upgrade',
  },
  AvailableWorkbenches: {
    path: '/available-products-new',
  },
  MyWorkbenches: {
    path: '/my-workbenches',
  },
  WorkbenchDetails: {
    path: '/my-workbenches/:id'
  },
  Programs: {
    path: '/programs',
  },
  OnboardProjectAccount: {
    path: '/administration/project/onboard-account',
  },
  ProjectUserAssignment: {
    path: '/administration/project/assign-user',
  },
  ProjectMembers: {
    path: '/administration/members',
  },
  Technologies: {
    path: '/administration/technologies',
  },
  TechnologyDetails: {
    path: '/administration/technologies/:id',
  },
  AddTechnology: {
    path: '/administration/technologies/add',
  },
  UpdateTechnology: {
    path: '/administration/technologies/update/:id',
  },
  HelpPage: {
    path: '/help',
  },
  CreateProgram: {
    path: '/programs/create-program'
  },
  UpdateProgram: {
    path: '/programs/update-program'
  },
  CreateProduct: {
    path: '/products/create-product',
  },
  CreateProductVersion: {
    path: '/products/:id/create-product-version',
  },
  UpdateProductVersion: {
    path: '/products/:productId/update-product-version/:versionId',
  },
  Products: {
    path: '/products'
  },
  Product: {
    path: '/products/product/:id'
  },
  ProductVersionDetails: {
    path: '/products/product/:productId/version/:versionId'
  },
  CompareProductVersions: {
    path: '/products/product/:productId/compare-versions'
  },
  Components: {
    path: '/components'
  },
  CreateComponent: {
    path: '/components-create'
  },
  ViewComponent: {
    path: '/components/:componentId'
  },
  UpdateComponent: {
    path: '/components/:componentId/update'
  },
  CreateComponentVersion: {
    path: '/components/:componentId/versions-create'
  },
  UpdateComponentVersion: {
    path: '/components/:componentId/versions-update/:versionId'
  },
  ViewComponentVersion: {
    path: '/components/:componentId/versions/:versionId'
  },
  CompareComponentVersions: {
    path: '/components/:componentId/compare-versions'
  },
  Recipes: {
    path: '/recipes'
  },
  CreateRecipe: {
    path: '/recipes-create'
  },
  ViewRecipe: {
    path: '/recipes/:recipeId'
  },
  CreateRecipeVersion: {
    path: '/recipes/:recipeId/versions-create'
  },
  UpdateRecipeVersion: {
    path: '/recipes/:recipeId/versions-update/:versionId'
  },
  ViewRecipeVersion: {
    path: '/recipes/:recipeId/versions/:versionId'
  },
  Images: {
    path: '/images'
  },
  MandatoryComponentsLists: {
    path: '/mandatory-components-lists'
  },
  CreateMandatoryComponentsList: {
    path: '/mandatory-components-lists/create'
  },
  UpdateMandatoryComponentsList: {
    path: '/mandatory-components-lists/update/:platform/:architecture/:osVersion'
  },
  ViewMandatoryComponentsList: {
    path: '/mandatory-components-lists/:platform/:architecture/:osVersion'
  },
  Pipelines: {
    path: '/pipelines'
  },
  CreatePipeline: {
    path: '/pipelines-create'
  },
  UpdatePipeline: {
    path: '/pipelines/:pipelineId/pipelines-update'
  },
  ProvisionedProductsAdministration: {
    path: '/administration/provisioned-products'
  },
  MyVirtualTargets: {
    path: '/my-virtual-targets'
  },
  AvailableVirtualTargets: {
    path: '/available-virtual-targets'
  },
  ProvisionVirtualTarget: {
    path: '/available-virtual-targets/:id'
  },
  UpgradeVirtualTarget: {
    path: '/my-virtual-targets/upgrade'
  },
  VirtualTargetDetails: {
    path: '/my-virtual-targets/:id'
  },
  NotFoundErrorPage: {
    path: '*'
  },
};
