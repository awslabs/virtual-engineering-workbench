import { RouteNames } from './navigation.static';
import {
  AvailableProductsNew,
  ProvisionProductNew,
  Programs,
  OnboardProjectAccount,
  ProjectUserAssignment,
  Members,
  Technologies,
  AddTechnology,
  UpdateTechnology,
  ProjectAccounts,
  HelpPage,
  CreateProgram,
  UpdateProgram,
  CreateProduct,
  CreateProductVersion,
  UpdateProductVersion,
  Products,
  ProductOverview,
  ProductVersionDetails,
  CompareProductVersions,
  Components,
  CreateComponent,
  ViewComponent,
  UpdateComponent,
  CreateComponentVersion,
  UpdateComponentVersion,
  ViewComponentVersion,
  CompareComponentVersions,
  i18nWorkbench,
  i18nProvisionWorkbench,
  i18nWorkbenchSteps,
  Recipes,
  CreateRecipe,
  ViewRecipe,
  CreateRecipeVersion,
  UpdateRecipeVersion,
  ViewRecipeVersion,
  Images,
  Pipelines,
  CreatePipeline,
  UpdatePipeline,
  MandatoryComponentsLists,
  CreateMandatoryComponentsList,
  UpdateMandatoryComponentsList,
  ViewMandatoryComponentsList,
  ProvisionedProductsAdministration,
  i18nVirtualTarget,
  i18nProvisionVirtualTarget,
  i18nVirtualTargetSteps,
} from '../../pages';

import { NotFound } from '../../error-pages';
import { provisioningAPI, packagingAPI } from '../../../services';
import { MyWorkbenches } from '../../pages/workbenches/workbenches-list';
import {
  UpgradeProvisionedProduct,
  i18nWorkbenchUpgrade,
  i18nVirtualTargetUpgrade
} from '../../pages/products/upgrade-provisioned-product';
import { WorkbenchDetails } from '../../pages/workbenches/workbench-details-v2/page';
import { MyVirtualTargets } from '../../pages/virtual-targets/virtual-targets-list';
import { VirtualTargetDetails } from '../../pages/virtual-targets/virtual-target-details';
import { ReactNode } from 'react';


type RouteConfig = {
  component: ReactNode,
};

export const ROUTES: { [key in RouteNames]: RouteConfig } = {
  ProvisionWorkbench: {
    component: <ProvisionProductNew
      i18n={i18nProvisionWorkbench}
      i18nSteps={i18nWorkbenchSteps}
      baseRouteName={RouteNames.AvailableWorkbenches}
      completionRouteName={RouteNames.MyWorkbenches} />,
  },
  ProvisionWorkbenchUseMapping: {
    component: <ProvisionProductNew
      i18n={i18nProvisionWorkbench}
      i18nSteps={i18nWorkbenchSteps}
      baseRouteName={RouteNames.AvailableWorkbenches}
      completionRouteName={RouteNames.MyWorkbenches} />,
  },
  UpgradeWorkbenchV2: {
    component: <UpgradeProvisionedProduct
      translations={i18nWorkbenchUpgrade}
      stepsTranslations={i18nWorkbenchSteps}
      returnPage={RouteNames.MyWorkbenches}
      serviceApi={provisioningAPI} />
  },
  AvailableWorkbenches: {
    component: <AvailableProductsNew
      productType='Workbench'
      i18n={i18nWorkbench}
      availableProductsServiceApi={provisioningAPI} />,
  },
  MyWorkbenches: {
    component: <MyWorkbenches />,
  },
  Programs: {
    component: <Programs />,
  },
  OnboardProjectAccount: {
    component: <OnboardProjectAccount />,
  },
  ProjectUserAssignment: {
    component: <ProjectUserAssignment />,
  },
  ProjectMembers: {
    component: <Members />,
  },
  WorkbenchDetails: {
    component: <WorkbenchDetails />
  },
  Technologies: {
    component: <Technologies />,
  },
  TechnologyDetails: {
    component: <ProjectAccounts />
  },
  AddTechnology: {
    component: <AddTechnology />
  },
  UpdateTechnology: {
    component: <UpdateTechnology />
  },
  HelpPage: {
    component: <HelpPage />
  },
  CreateProgram: {
    component: <CreateProgram />
  },
  UpdateProgram: {
    component: <UpdateProgram />
  },
  CreateProduct: {
    component: <CreateProduct />,
  },
  CreateProductVersion: {
    component: <CreateProductVersion />,
  },
  UpdateProductVersion: {
    component: <UpdateProductVersion />,
  },
  Products: {
    component: <Products />
  },
  Product: {
    component: <ProductOverview />
  },
  ProductVersionDetails: {
    component: <ProductVersionDetails />
  },
  CompareProductVersions: {
    component: <CompareProductVersions />
  },
  Components: {
    component: <Components serviceApi={packagingAPI} />
  },
  CreateComponent: {
    component: <CreateComponent />
  },
  ViewComponent: {
    component: <ViewComponent />
  },
  UpdateComponent: {
    component: <UpdateComponent />
  },
  CreateComponentVersion: {
    component: <CreateComponentVersion />
  },
  UpdateComponentVersion: {
    component: <UpdateComponentVersion />
  },
  ViewComponentVersion: {
    component: <ViewComponentVersion />
  },
  CompareComponentVersions: {
    component: <CompareComponentVersions />
  },
  Recipes: {
    component: <Recipes serviceApi={packagingAPI} />
  },
  CreateRecipe: {
    component: <CreateRecipe />
  },
  ViewRecipe: {
    component: <ViewRecipe />
  },
  CreateRecipeVersion: {
    component: <CreateRecipeVersion />
  },
  UpdateRecipeVersion: {
    component: <UpdateRecipeVersion />
  },
  ViewRecipeVersion: {
    component: <ViewRecipeVersion />
  },
  Images: {
    component: <Images />
  },
  MandatoryComponentsLists: {
    component: <MandatoryComponentsLists />,
  },
  CreateMandatoryComponentsList: {
    component: <CreateMandatoryComponentsList />
  },
  UpdateMandatoryComponentsList: {
    component: <UpdateMandatoryComponentsList />
  },
  ViewMandatoryComponentsList: {
    component: <ViewMandatoryComponentsList />
  },
  ProvisionedProductsAdministration: {
    component: <ProvisionedProductsAdministration />
  },
  MyVirtualTargets: {
    component: <MyVirtualTargets />
  },
  AvailableVirtualTargets: {
    component: <AvailableProductsNew
      productType='VirtualTarget'
      i18n={i18nVirtualTarget}
      availableProductsServiceApi={provisioningAPI} />
  },
  ProvisionVirtualTarget: {
    component: <ProvisionProductNew
      i18n={i18nProvisionVirtualTarget}
      i18nSteps={i18nVirtualTargetSteps}
      baseRouteName={RouteNames.AvailableVirtualTargets}
      completionRouteName={RouteNames.MyVirtualTargets} />,
  },
  UpgradeVirtualTarget: {
    component: <UpgradeProvisionedProduct
      translations={i18nVirtualTargetUpgrade}
      stepsTranslations={i18nVirtualTargetSteps}
      returnPage={RouteNames.MyVirtualTargets}
      serviceApi={provisioningAPI} />
  },
  VirtualTargetDetails: {
    component: <VirtualTargetDetails />
  },
  Pipelines: {
    component: <Pipelines />
  },
  CreatePipeline: {
    component: <CreatePipeline />
  },
  UpdatePipeline: {
    component: <UpdatePipeline />
  },
  NotFoundErrorPage: {
    component: <NotFound />
  },
};
