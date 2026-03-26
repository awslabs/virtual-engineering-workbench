import {
  CardsProps,
  PaginationProps,
  StatusIndicatorProps,
} from '@cloudscape-design/components';
import {
  ProvisionedProduct,
} from '../../../services/API/proserve-wb-provisioning-api';
import { RoleBasedFeature } from '../../../state';
import { BreadcrumbItem } from '../../layout';
import { ProvisionedProductType, ServiceAPI } from '../../../services/API/provisioning-api';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { Feature } from '../../feature-toggles/feature-toggle.state';
import { i18n } from '.';
import {
  PropertyFilterOption,
  PropertyFilterProperty,
  PropertyFilterQuery
} from '@cloudscape-design/collection-hooks';
import { ProvisionedProductLoginTranslations } from './provisioned-product-actions';

export type ProvisionedProductsTranslations = typeof i18n;

export interface ProvisionedProductsToDeleteListProps {
  targets: ProvisionedProduct[],
  translations: ProvisionedProductsTranslations,
}

export interface ProvisionedProductHeaderActionsProps {
  isInTurnDownMode: boolean,
  isLoading: boolean,
  isValidToTurnDown: boolean,
  translations: ProvisionedProductsTranslations,
  onRefreshHandler: () => void,
  onRemoveHandler: () => void,
  onProvisionHandler: () => void,
  onCancelRemoveHandler: () => void,
  onSubmitRemoveHandler: () => void,
}

export interface ProvisionedProductListHeaderProps {
  actions: React.ReactNode,
  translations: ProvisionedProductsTranslations,
}

export interface ProvisionedProductCardHeaderProps {
  target: ProvisionedProduct,
  setUpdatePromptVisible: (value: boolean) => void,
  setSelectedProvisionedProduct: (value: ProvisionedProduct) => void,
}

export interface ProvisionedProductCardVersionProps {
  provisionedProduct: ProvisionedProduct,
  hideUpgradeButton: boolean,
  disableUpgradeButton: boolean,
  translations: ProvisionedProductsTranslations,
  upgradePage: RouteNames,
}

export interface ProvisionedProductCardActionsProps {
  isLoading: boolean,
  isInTurnDownMode: boolean,
  state: string,
  provisionedProduct: ProvisionedProduct,
  onViewDetailsHandler: () => void,
  translations: ProvisionedProductsTranslations,
  loginTranslations: ProvisionedProductLoginTranslations,
  headlessLogin?: boolean,
  stateActionCompleteHandler?: () => void,
  productType?: string,
  renderLoginButton?: boolean,
}

export interface ProvisionedProductCardStatusProps {
  decideStatusIndicatorType: StatusIndicatorProps.Type,
  provisionedProductId: string,
  productStatus: string,
}

interface CustomEventLike<T> {
  detail: T,
}

interface PropertyFilterPropsType {
  query: PropertyFilterQuery,
  onChange(event: CustomEventLike<PropertyFilterQuery>): void,
  filteringProperties: readonly PropertyFilterProperty[],
  filteringOptions: readonly PropertyFilterOption[],
}

export interface ProvisionedProductListProps {
  targets: readonly ProvisionedProduct[],
  isCardDisabled: (item: ProvisionedProduct) => boolean,
  isInTurnDownMode: boolean,
  isLoading: (item?: ProvisionedProduct) => boolean,
  header: React.ReactNode,
  empty: React.ReactNode,
  selectionType?: CardsProps.SelectionType,
  paginationProps: PaginationProps,
  filterProps: PropertyFilterPropsType,
  collectionProps: Partial<CardsProps>,
  additionalCardDefinitionSections?: CardsProps.SectionDefinition<ProvisionedProduct>[],
  decideStatusIndicatorType: (status: string) => StatusIndicatorProps.Type,
  decideToHideUpgradeButton: (item: ProvisionedProduct) => boolean,
  decideToDisableUpgradeButton: (item: ProvisionedProduct) => boolean,
  handleViewDetail: (workbench: ProvisionedProduct) => void,
  translations: ProvisionedProductsTranslations,
  upgradePage: RouteNames,
  loginTranslations: ProvisionedProductLoginTranslations,
  headlessLogin?: boolean,
  stateActionCompleteHandler?: () => void,
  productType?: string,
  disableCardMenu?: boolean,
}

export type FetcherProps = {
  projectId: string,
  productType: ProvisionedProductType,
};

export interface ProvisionedProductHookProps {
  productType: ProvisionedProductType,
  serviceAPI: ServiceAPI,
  provisionedProductDetailsRouteName: RouteNames,
  availableProvisionedProductRouteName: RouteNames,
  translations: ProvisionedProductsTranslations,
}

export interface ProvisionedProductsProps extends ProvisionedProductHookProps {
  additionalCardDefinitionSections?: CardsProps.SectionDefinition<ProvisionedProduct>[],
  upgradePage: RouteNames,
  disableCardMenu?: boolean,
}

export interface ProvisionedProductHookLogicResult {
  targets: readonly ProvisionedProduct[],
  crumbs: BreadcrumbItem[],
  isInTurnDownMode: boolean,
  isLoading: boolean,
  isValidToTurnDown: boolean,
  turnDownConfirmVisible: boolean,
  turnDownTimeOutInProgress: boolean,
  turnDownInProgress: boolean,
  selectionType?: CardsProps.SelectionType,
  propertyFilterProps: PropertyFilterPropsType,
  paginationProps: PaginationProps,
  collectionProps: Partial<CardsProps>,
  productType: ProvisionedProductType,
  handleRemoveClick: () => void,
  handleRemoveCancel: () => void,
  handleRemoveSubmit: () => void,
  refreshWorkbenches: () => void,
  navigateToProductsScreen: () => void,
  handleRemoveConfirmSubmit: () => void,
  handleRemoveConfirmCancel: () => void,
  handleViewDetail: (workbench: ProvisionedProduct) => void,
  isFeatureAccessible: (feature: RoleBasedFeature) => boolean,
  isFeatureEnabled: (feature: Feature) => boolean,
  isCardDisabled: (item: ProvisionedProduct) => boolean,
  decideStatusIndicatorType: (status: string) => StatusIndicatorProps.Type,
  decideToHideUpgradeButton: (item: ProvisionedProduct) => boolean,
  decideToDisableUpgradeButton: (item: ProvisionedProduct) => boolean,
  isProvisionedProductListLoading: (item?: ProvisionedProduct) => boolean,
}

export interface CommonProvisionedProductHookProps {
  productType: ProvisionedProductType,
  serviceAPI: ServiceAPI,
  provisionedProductDetailsRouteName: RouteNames,
  availableProvisionedProductRouteName: RouteNames,
  refreshHandler?: () => void,
  startProvisionProductErrorNotification?: (e: any) => void,
  stopProvisionProductErrorNotification?: (e: any) => void,
}


export interface CommonProvisionedProductStateHookProps {
  provisionedProduct?: ProvisionedProduct,
  stateActionCompleteHandler?: () => void,
  setStopConfirmVisible: (visible: boolean) => void,
}

export interface CommonProvisionedProductStateHookResponse {
  handleStartProduct: () => void,
  handleStopProduct: () => void,
  startInProgress: boolean,
  stopInProgress: boolean,
}