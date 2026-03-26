import { i18nProvisionedProductDetails } from '.';
import { CommonProvisionedProductHookProps } from '..';
import { ComponentVersionDetail } from '../../../../services/API/proserve-wb-provisioning-api';
import { RouteNames } from '../../../layout/navigation/navigation.static';

export type ProvisionedProductDetailsTranslations = typeof i18nProvisionedProductDetails;

export type ProvisionedProductParameters = {
  key: string,
  value: string,
  description?: string,
};

export type ProvisionedProductRecommendationWarning = {
  recommendationMessage?: string,
  recommendedInstanceType?: string,
};

export enum RecommendationReason {
  OverProvisioned = 'OVER_PROVISIONED',
  UnderProvisioned = 'UNDER_PROVISIONED',
}

export type ProvisionedProductDetailsHookPorps =
  CommonProvisionedProductHookProps & {
    translations: ProvisionedProductDetailsTranslations,
  };

export interface ProvisionedProductDetailsProps
  extends ProvisionedProductDetailsHookPorps {
  headerActions?: React.ReactNode | null,
  dataTestPrefix?: string,
  translations: ProvisionedProductDetailsTranslations,
  myProvisionedProductRouteName: RouteNames,
}

export interface ProvisionedProductInstalledToolsListProps {
  componentVersionDetails: ComponentVersionDetail[],
  translations: ProvisionedProductDetailsTranslations,
}