import { i18nProvisionWorkbench, i18nWorkbenchSteps } from '..';
import {
  AvailableVersionDistribution,
  ProvisionedProduct
} from '../../../../services/API/proserve-wb-provisioning-api';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { ServiceAPI } from '../../../../hooks/provisioning/upgrade-provisioned-product.logic';
import { i18nWorkbenchUpgrade } from './translations';
import { ProductParameterState } from '../../../../hooks/provisioning';
import { Steps } from './components';

/* eslint @typescript-eslint/no-unused-vars: "off" */
const i18nUpgradeTexts = {
  ...i18nProvisionWorkbench,
  ...i18nWorkbenchUpgrade
};

export type UpgradeProvisionedProductTranslations = typeof i18nUpgradeTexts;

export type StepsTranslations = typeof i18nWorkbenchSteps;

export interface LocationState {
  provisionedProduct?: ProvisionedProduct,
}

export interface UpgradeProvisionedProductProps {
  translations: UpgradeProvisionedProductTranslations,
  stepsTranslations: StepsTranslations,
  returnPage: RouteNames,
  serviceApi: ServiceAPI,
}

export interface UpgradeProvisionedProductWizardProps {
  translations: UpgradeProvisionedProductTranslations,
  stepsTranslations: StepsTranslations,
  returnPage: RouteNames,
  startingUpgradeInProcess: boolean,
  provisionedProduct: ProvisionedProduct,
  selectedVersion?: AvailableVersionDistribution,
  productParameterState: ProductParameterState,
  productVersionsLoading: boolean,
  handleProductParameterChange: (key: string, value?: string) => void,
  previouslyEnteredParameterNames: Set<string>,
  setActiveHelpPanel: (strep: Steps) => void,
  setToolsOpen: (val: boolean) => void,
  toolsOpen: boolean,
  upgradeWorkbench: () => Promise<void>,
}

export interface UpgradeWarningProps { translations: UpgradeProvisionedProductTranslations }


