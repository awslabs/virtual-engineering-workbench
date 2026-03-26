import {
  SelectProps,
  StatusIndicatorProps,
} from '@cloudscape-design/components';
import { ServiceAPI } from '../../../services/API/provisioning-api';
import { ProvisionedProduct } from '../../../services/API/proserve-wb-provisioning-api';
import { BreadcrumbItem } from '../../layout';
import { i18n } from './translations';
import { UseCollectionResult } from '@cloudscape-design/collection-hooks';
import { ReactNode } from 'react';

export const PRODUCT_INSTANCE_STATES = {
  Starting: 'STARTING',
  Stopping: 'STOPPING',
  Stopped: 'STOPPED',
  Running: 'RUNNING',
  Terminated: 'TERMINATED',
  ProvisioningError: 'PROVISIONING_ERROR',
  Provisioning: 'PROVISIONING',
  Deprovisioning: 'DEPROVISIONING',
  Updating: 'UPDATING',
  ConfigurationInProgress: 'CONFIGURATION_IN_PROGRESS',
  ConfigurationFailed: 'CONFIGURATION_FAILED',
};

export const PRODUCT_INSTANCE_STATE_INDICATOR_MAP = new Map<
  string,
  StatusIndicatorProps.Type
>()
  .set(PRODUCT_INSTANCE_STATES.Starting, 'in-progress')
  .set(PRODUCT_INSTANCE_STATES.Stopping, 'in-progress')
  .set(PRODUCT_INSTANCE_STATES.Provisioning, 'in-progress')
  .set(PRODUCT_INSTANCE_STATES.Updating, 'in-progress')
  .set(PRODUCT_INSTANCE_STATES.Deprovisioning, 'in-progress')
  .set(PRODUCT_INSTANCE_STATES.Stopped, 'stopped')
  .set(PRODUCT_INSTANCE_STATES.Running, 'success')
  .set(PRODUCT_INSTANCE_STATES.Terminated, 'info')
  .set(PRODUCT_INSTANCE_STATES.ProvisioningError, 'error')
  .set(PRODUCT_INSTANCE_STATES.ConfigurationInProgress, 'in-progress')
  .set(PRODUCT_INSTANCE_STATES.ConfigurationFailed, 'error');

export const PRODUCT_STATE_TRANSLATIONS = new Map<string, string>()
  .set(PRODUCT_INSTANCE_STATES.Starting, 'Starting')
  .set(PRODUCT_INSTANCE_STATES.Stopping, 'Stopping')
  .set(PRODUCT_INSTANCE_STATES.Stopped, 'Stopped')
  .set(PRODUCT_INSTANCE_STATES.Running, 'Running')
  .set(PRODUCT_INSTANCE_STATES.Terminated, 'Terminated')
  .set(PRODUCT_INSTANCE_STATES.ProvisioningError, 'Provisioning error')
  .set(PRODUCT_INSTANCE_STATES.Provisioning, 'Provisioning')
  .set(PRODUCT_INSTANCE_STATES.Deprovisioning, 'Deprovisioning')
  .set(PRODUCT_INSTANCE_STATES.Updating, 'Updating')
  .set(PRODUCT_INSTANCE_STATES.ConfigurationInProgress, 'Configuring')
  .set(PRODUCT_INSTANCE_STATES.ConfigurationFailed, 'Configuration error');

export const PRODUCT_TYPE_MAP: { [key: string]: string } = {
  WORKBENCH: 'Workbench',
  VIRTUAL_TARGET: 'Virtual target',
  UNKNOWN: 'Unknown',
};


export type ProvisionedProductsAdministrationTranslations = typeof i18n;

export type FetcherProps = {
  projectId: string,
};

export interface ProvisionedProductsAdministrationHookProps {
  serviceAPI: ServiceAPI,
  translations: ProvisionedProductsAdministrationTranslations,
}

export interface ProvisionedProductsAdministrationHookOutput {
  breadcrumbItems: BreadcrumbItem[],
  provisionedProducts: readonly ProvisionedProduct[],
  provisionedProductsTableProps: UseCollectionResult<ProvisionedProduct>,
  selectedProvisionedProductsTableProps: UseCollectionResult<ProvisionedProduct>,
  provisionedProductsLoading: boolean,
  reloadProvisionedProducts: () => void,
  productOptions: SelectProps.Options,
  selectedProductOption: SelectProps.Option,
  setSelectedProductOption: (option: SelectProps.Option) => void,
  productTypeOptions: SelectProps.Options,
  selectedProductTypeOption: SelectProps.Option,
  setSelectedProductTypeOption: (option: SelectProps.Option) => void,
  statusOptions: SelectProps.Options,
  selectedStatusOption: SelectProps.Option,
  setSelectedStatusOption: (option: SelectProps.Option) => void,
  additionalInformationOptions: SelectProps.Options,
  selectedAdditionalInformationOption: SelectProps.Option,
  setSelectedAdditionalInformationOption: (option: SelectProps.Option) => void,
  stopActionDisabled: boolean,
  stopProvisionedProductsPromptOpen: boolean,
  setStopProvisionedProductsPromptOpen: (open: boolean) => void,
  stopProvisionedProductsInProgress: boolean,
  stopProvisionedProducts: () => void,
  terminateActionDisabled: boolean,
  terminateProvisionedProductsPromptOpen: boolean,
  setTerminateProvisionedProductsPromptOpen: (open: boolean) => void,
  terminateProvisionedProductsInProgress: boolean,
  terminateProvisionedProducts: () => void,
  getSelectedProvisionedProducts: () => readonly ProvisionedProduct[],
}

export interface ProvisionedProductsOverviewProps {
  translations: ProvisionedProductsAdministrationTranslations,
  provisionedProducts: readonly ProvisionedProduct[],
  provisionedProductsLoading: boolean,
}

export interface ProvisionedProductStatusProps {
  status: string,
}

export interface ProvisionedProductsListProps {
  translations: ProvisionedProductsAdministrationTranslations,
  tableProps: UseCollectionResult<ProvisionedProduct>,
  tableLoading: boolean,
  tableActions: ReactNode,
  productOptions: SelectProps.Options,
  selectedProductOption: SelectProps.Option,
  setSelectedProductOption: (option: SelectProps.Option) => void,
  productTypeOptions: SelectProps.Options,
  selectedProductTypeOption: SelectProps.Option,
  setSelectedProductTypeOption: (option: SelectProps.Option) => void,
  statusOptions: SelectProps.Options,
  selectedStatusOption: SelectProps.Option,
  setSelectedStatusOption: (option: SelectProps.Option) => void,
  additionalInformationOptions: SelectProps.Options,
  selectedAdditionalInformationOption: SelectProps.Option,
  setSelectedAdditionalInformationOption: (option: SelectProps.Option) => void,
}

export interface ProvisionedProductsListActionsProps {
  translations: ProvisionedProductsAdministrationTranslations,
  reloadProvisionedProducts: () => void,
  selectedProvisionedProductsTableProps: UseCollectionResult<ProvisionedProduct>,
  provisionedProductsLoading: boolean,
  stopActionDisabled: boolean,
  stopProvisionedProductsPromptOpen: boolean,
  setStopProvisionedProductsPromptOpen: (open: boolean) => void,
  stopProvisionedProductsInProgress: boolean,
  stopProvisionedProducts: () => void,
  terminateActionDisabled: boolean,
  terminateProvisionedProductsPromptOpen: boolean,
  setTerminateProvisionedProductsPromptOpen: (open: boolean) => void,
  terminateProvisionedProductsInProgress: boolean,
  terminateProvisionedProducts: () => void,
  getSelectedProvisionedProducts: () => readonly ProvisionedProduct[],
}
