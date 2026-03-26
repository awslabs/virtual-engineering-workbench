/* eslint-disable @stylistic/max-len */
export const ROUTE_REGULAR_EXPRESSIONS = {
  newMyWorkbenches: /^\/my-workbenches\/.*|\/my-workbenches$/giu,
  allWorkbenchesNew: /^\/available-products-new\/.*|\/available-products-new$/giu,
  administrationMembers: /^\/administration\/members\/.*|\/administration\/members$/giu,
  programs: /^\/programs$/giu,
  hilDevices: /^\/hil-devices$/giu,
  hilDeviceDetails: /^\/hil-device-details\/.*$/giu,
  configurations: /^\/hardware\/hardware-configurations\/.*|\/hardware\/hardware-configurations$/giu,
  administrationTechnologies: /^\/administration\/technologies\/.*|\/administration\/technologies$/giu,
  createProgram: /^\/programs\/create-program\/.*|\/programs\/create-program$/giu,
  updateProgram: /^\/programs\/update-program\/.*|\/programs\/update-program$/giu,
  createProduct: /^\/products\/create-product\/.*|\/products\/create-product$/giu,
  createProductVersion: /^\/products\/.*\/create-product-version\/.*|\/products\/.*\/create-product-version$/giu,
  updateProductVersion: /^\/products\/.*\/update-product-version\/.*$/giu,
  products: /^\/products$/giu,
  product: /^\/products\/product\/.*|\/products\/product$/giu,
  productVersionDetails: /^\/products\/product\/.*|\/products\/product$/giu,
  compareProductVersions: /^\/products\/product\/.+\/compare-versions$/giu,
  components: /^\/components$/giu,
  createComponent: /^\/components-create$/giu,
  viewComponent: /^\/components\/.+$/giu,
  createComponentVersion: /^\/components\/.+\/versions-create$/giu,
  updateComponentVersion: /^\/components\/.+\/versions-update\/.*$/giu,
  viewComponentVersion: /^\/components\/.+\/versions\/.*$/giu,
  compareComponentVersions: /^\/components\/.+\/compare-versions$/giu,
  recipes: /^\/recipes$/giu,
  createRecipe: /^\/recipes-create$/giu,
  viewRecipe: /^\/recipes\/.+$/giu,
  createRecipeVersion: /^\/recipe\/.+\/versions-create$/giu,
  updateRecipeVersion: /^\/recipe\/.+\/versions-update$/giu,
  viewRecipeVersion: /^\/recipes\/.+\/versions\/.*$/giu,
  images: /^\/images$/giu,
  mandatoryComponentsLists: /^\/mandatory-components-lists$/giu,
  createMandatoryComponentsList: /^\/mandatory-components-lists\/create$/giu,
  updateMandatoryComponentsList: /^\/mandatory-components-lists\/update\/.*$/giu,
  viewMandatoryComponentsList: /^\/mandatory-components-lists\/.+$/giu,
  vvplMappingsList: /^\/validation-verification-mappings$/giu,
  vvplMappingsCreate: /^\/validation-verification-mappings-create$/giu,
  vvplMappingsUpdate: /^\/validation-verification-mappings-update\/.*$/giu,
  findArtifacts: /^\/find-artifacts$/giu,
  sharedImages: /^\/shared-images$/giu,
  viewSharedImage: /^\/shared-images\/.+$/giu,
  provisionedProductsAdministration: /^\/administration\/provisioned-products$/giu,
  myVirtualTargets: /^\/my-virtual-targets\/.*|\/my-virtual-targets$/giu,
  availableVirtualTargets: /^\/available-virtual-targets\/.*|\/available-virtual-targets$/giu,
  pipelines: /^\/pipelines$/giu,
  createPipeline: /^\/pipelines-create$/giu,
  updatePipeline: /^\/pipelines\/.*\/pipelines-update$/giu,
};


export enum RouteNames {
  UpgradeWorkbenchV2 = 'UpgradeWorkbenchV2',
  ProvisionWorkbench = 'ProvisionWorkbench',
  ProvisionWorkbenchUseMapping = 'ProvisionWorkbenchUseMapping',
  AvailableWorkbenches = 'AvailableWorkbenches',
  MyWorkbenches = 'MyWorkbenches',
  WorkbenchDetails = 'WorkbenchDetails',
  Programs = 'Programs',
  OnboardProjectAccount = 'OnboardProjectAccount',
  ProjectUserAssignment = 'ProjectUserAssignment',
  ProjectMembers = 'ProjectMembers',
  Technologies = 'Technologies',
  TechnologyDetails = 'TechnologyDetails',
  AddTechnology = 'AddTechnology',
  UpdateTechnology = 'UpdateTechnology',
  HelpPage = 'HelpPage',
  CreateProgram = 'CreateProgram',
  UpdateProgram = 'UpdateProgram',
  CreateProduct = 'CreateProduct',
  CreateProductVersion = 'CreateProductVersion',
  UpdateProductVersion = 'UpdateProductVersion',
  Products = 'Products',
  Product = 'Product',
  ProductVersionDetails = 'ProductVersionDetails',
  CompareProductVersions = 'CompareProductVersions',
  Components = 'Components',
  CreateComponent = 'CreateComponent',
  ViewComponent = 'ViewComponent',
  UpdateComponent = 'UpdateComponent',
  CreateComponentVersion = 'CreateComponentVersion',
  UpdateComponentVersion = 'UpdateComponentVersion',
  ViewComponentVersion = 'ViewComponentVersion',
  CompareComponentVersions = 'CompareComponentVersions',
  Recipes = 'Recipes',
  CreateRecipe = 'CreateRecipe',
  ViewRecipe = 'ViewRecipe',
  CreateRecipeVersion = 'CreateRecipeVersion',
  UpdateRecipeVersion = 'UpdateRecipeVersion',
  ViewRecipeVersion = 'ViewRecipeVersion',
  Images = 'Images',
  MandatoryComponentsLists = 'MandatoryComponentsLists',
  CreateMandatoryComponentsList = 'CreateMandatoryComponentsList',
  UpdateMandatoryComponentsList = 'UpdateMandatoryComponentsList',
  ViewMandatoryComponentsList = 'ViewMandatoryComponentsList',
  Pipelines = 'Pipelines',
  CreatePipeline = 'CreatePipeline',
  UpdatePipeline = 'UpdatePipeline',
  ProvisionedProductsAdministration = 'ProvisionedProductsAdministration',
  MyVirtualTargets = 'MyVirtualTargets',
  AvailableVirtualTargets = 'AvailableVirtualTargets',
  ProvisionVirtualTarget = 'ProvisionVirtualTarget',
  UpgradeVirtualTarget = 'UpgradeVirtualTarget',
  VirtualTargetDetails = 'VirtualTargetDetails',
  NotFoundErrorPage = 'NotFoundErrorPage',
}

export const USER_NAVIGATION_MAP = [{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.newMyWorkbenches,
  routeName: RouteNames.MyWorkbenches,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.allWorkbenchesNew,
  routeName: RouteNames.AvailableWorkbenches,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.administrationMembers,
  routeName: RouteNames.ProjectMembers,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.administrationTechnologies,
  routeName: RouteNames.Technologies,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.administrationTechnologies,
  routeName: RouteNames.TechnologyDetails,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.administrationTechnologies,
  routeName: RouteNames.AddTechnology,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.administrationTechnologies,
  routeName: RouteNames.UpdateTechnology,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.createProgram,
  routeName: RouteNames.CreateProgram,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.updateProgram,
  routeName: RouteNames.UpdateProgram,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.createProduct,
  routeName: RouteNames.Products,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.products,
  routeName: RouteNames.Products,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.product,
  routeName: RouteNames.Products,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.compareProductVersions,
  routeName: RouteNames.Products,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.productVersionDetails,
  routeName: RouteNames.Products,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.createProductVersion,
  routeName: RouteNames.Products,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.updateProductVersion,
  routeName: RouteNames.Products,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.components,
  routeName: RouteNames.Components,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.createComponent,
  routeName: RouteNames.Components,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.viewComponent,
  routeName: RouteNames.Components,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.compareComponentVersions,
  routeName: RouteNames.Components,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.createComponentVersion,
  routeName: RouteNames.Components,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.updateComponentVersion,
  routeName: RouteNames.Components,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.updateComponentVersion,
  routeName: RouteNames.Components,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.viewComponentVersion,
  routeName: RouteNames.Components,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.recipes,
  routeName: RouteNames.Recipes,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.createRecipe,
  routeName: RouteNames.Recipes,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.viewRecipe,
  routeName: RouteNames.Recipes,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.createRecipeVersion,
  routeName: RouteNames.Recipes,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.updateComponentVersion,
  routeName: RouteNames.Recipes,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.viewRecipeVersion,
  routeName: RouteNames.Recipes,
}, {
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.images,
  routeName: RouteNames.Images,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.pipelines,
  routeName: RouteNames.Pipelines,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.createPipeline,
  routeName: RouteNames.Pipelines,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.updatePipeline,
  routeName: RouteNames.Pipelines,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.mandatoryComponentsLists,
  routeName: RouteNames.MandatoryComponentsLists,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.createMandatoryComponentsList,
  routeName: RouteNames.MandatoryComponentsLists,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.updateMandatoryComponentsList,
  routeName: RouteNames.MandatoryComponentsLists,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.provisionedProductsAdministration,
  routeName: RouteNames.ProvisionedProductsAdministration,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.myVirtualTargets,
  routeName: RouteNames.MyVirtualTargets,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.availableVirtualTargets,
  routeName: RouteNames.AvailableVirtualTargets,
},
{
  pathRegexMatcher: ROUTE_REGULAR_EXPRESSIONS.myVirtualTargets,
  routeName: RouteNames.VirtualTargetDetails,
},
];
