import { useState, useMemo, useCallback } from 'react';
import { useRoleAccessToggle } from '../../../hooks/role-access-toggle.ts';
import { selectedProjectState } from '../../../state/index.ts';
import { BreadcrumbItem, useNotifications } from '../../layout/index.ts';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic.ts';
import useSWR from 'swr';
import { useRecoilValue } from 'recoil';
import { useCollection } from '@cloudscape-design/collection-hooks';
import {
  GetProvisionedProductsResponse,
  ProvisionedProduct,
} from '../../../services/API/proserve-wb-provisioning-api/index.ts';
import {
  CardsProps,
  StatusIndicatorProps,
} from '@cloudscape-design/components';
import { extractErrorResponseMessage } from '../../../utils/api-helpers.ts';
import {
  FetcherProps,
  ProvisionedProductHookLogicResult,
  ProvisionedProductsTranslations,
  ProvisionedProductHookProps,
} from './interface.ts';
import { useFeatureToggles } from '../../feature-toggles/feature-toggle.hook.ts';
import { useCommonProvisionedProduct } from './common.logic.ts';
import { ServiceAPI } from '../../../services';
import { CompareDates } from '../shared/compare-dates.tsx';

export const fetchKey = (productType: string) =>
  `provisioning/products/${productType}`;

const DEFAULT_GRID_PAGE_SIZE = 10;

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
  ConfigurationFailed: 'CONFIGURATION_FAILED'
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

export const INTERMEDIATE_PRODUCT_PROVISIONING_STATES = new Set([
  PRODUCT_INSTANCE_STATES.Provisioning,
  PRODUCT_INSTANCE_STATES.Deprovisioning,
  PRODUCT_INSTANCE_STATES.Updating,
  PRODUCT_INSTANCE_STATES.ConfigurationInProgress,
]);

export const INTERMEDIATE_PRODUCT_RUNTIME_STATES = new Set([
  PRODUCT_INSTANCE_STATES.Starting,
  PRODUCT_INSTANCE_STATES.Stopping,
]);

export const INTERMEDIATE_PRODUCT_STATES = new Set([
  ...INTERMEDIATE_PRODUCT_RUNTIME_STATES,
  ...INTERMEDIATE_PRODUCT_PROVISIONING_STATES,
]);

const fetcherFactory =
  (serviceAPI: ServiceAPI) =>
    async ({
      projectId,
      productType,
    }: FetcherProps): Promise<GetProvisionedProductsResponse> => {
      return serviceAPI.getProvisionedProducts(projectId, productType);
    };

function getBreadcrumbItems(translations: ProvisionedProductsTranslations): BreadcrumbItem[] {
  return [{ path: translations.breadCrumbItem1, href: '#' }];
}

export function useProvisionedProducts(
  hookProps: ProvisionedProductHookProps
): ProvisionedProductHookLogicResult {
  const {
    serviceAPI,
    productType,
    provisionedProductDetailsRouteName,
    availableProvisionedProductRouteName,
    translations
  } = hookProps;
  const { showErrorNotification } = useNotifications();
  const isFeatureAccessible = useRoleAccessToggle();
  const { isFeatureEnabled } = useFeatureToggles();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { navigateTo } = useNavigationPaths();
  const [selectionType, setSelectionType] = useState<
  CardsProps.SelectionType | undefined
  >(undefined);

  const {
    turnDownInProgress,
    setTurnDownInProgress,
    isInTurnDownMode,
    setTurnDownMode,
    turnDownConfirmVisible,
    setTurnDownConfirmVisible,
    turnDownTimeOutInProgress,
    setTurnDownTimeOutInProgress,
  } = useCommonProvisionedProduct();

  const { data, mutate, isLoading } = useSWR(
    {
      key: fetchKey(productType),
      projectId: selectedProject.projectId!,
      productType,
    },
    fetcherFactory(serviceAPI),
    {
      shouldRetryOnError: false,
    }
  );
  const targets = data ? data.
    provisionedProducts.
    filter((p) => p.status !== PRODUCT_INSTANCE_STATES.Terminated).
    sort((a, b) => CompareDates(a.createDate, b.createDate)) : [];

  const {
    items,
    actions,
    collectionProps,
    paginationProps,
    propertyFilterProps,
  } = useCollection(targets, {
    propertyFiltering: {
      filteringProperties: [
        {
          key: 'status',
          operators: ['=', ':', '!='],
          propertyLabel: translations.propertyFilterStatusProperty,
          groupValuesLabel: translations.propertyFilterStatusPropertyGroup,
        },
        {
          key: 'productName',
          operators: ['=', ':', '!='],
          propertyLabel: translations.propertyFilterNameProperty,
          groupValuesLabel: translations.propertyFilterNamePropertyGroup,
        },
      ],
    },
    pagination: { pageSize: DEFAULT_GRID_PAGE_SIZE },
    selection: {
      trackBy: 'provisionedProductId',
      keepSelection: true,
    },
  });

  const isValidToTurnDown = useMemo(() => {
    const selectedItems = collectionProps.selectedItems ?? [];
    return canTurnDown(selectedItems);
  }, [collectionProps.selectedItems]);

  const isProvisionedProductListLoading = useCallback(
    (target?: ProvisionedProduct) => {
      if (isLoading) {
        return true;
      }
      return (
        target !== undefined && INTERMEDIATE_PRODUCT_STATES.has(target.status)
      );
    },
    [isLoading]
  );

  function handleRemoveClick(): void {
    setTurnDownMode(true);
    setSelectionType('multi');
  }

  function handleRemoveCancel(): void {
    setTurnDownMode(false);
    setSelectionType(undefined);
    actions.setSelectedItems([]);
  }

  function handleRemoveSubmit(): void {
    setTurnDownConfirmVisible(true);
  }

  function handleRemoveConfirmSubmit(): void {
    if (!selectedProject.projectId) {
      return;
    }
    const projectId = selectedProject.projectId;

    setTurnDownInProgress(true);

    Promise.all(
      (collectionProps.selectedItems || []).map((selectedItem) => {
        return serviceAPI.removeProvisionedProduct(
          projectId,
          selectedItem.provisionedProductId
        );
      })
    )
      .catch(async (e) => {
        showErrorNotification({
          header: translations.errorDeprovision,
          content: await extractErrorResponseMessage(e),
        });
      })
      .finally(() => {
        setTurnDownInProgress(false);
      })
      .then(() => {
        refreshWorkbenches();
      });
  }

  function handleRemoveConfirmCancel(): void {
    setTurnDownConfirmVisible(false);
  }

  function handleViewDetail(target: ProvisionedProduct): void {
    navigateTo(provisionedProductDetailsRouteName, {
      ':id': target.provisionedProductId,
    });
  }

  async function refreshWorkbenches(): Promise<void> {
    // commonRefreshWorkbenches();
    setTurnDownTimeOutInProgress(false);
    setTurnDownConfirmVisible(false);
    setTurnDownMode(false);
    actions.setSelectedItems([]);
    setSelectionType(undefined);
    await mutate();
  }

  function canTurnDown(selectedItems: readonly ProvisionedProduct[]): boolean {
    const selectedItemsLengthToTurnDown = 1;
    const UnAcceptableStatesForTurningDown = [
      PRODUCT_INSTANCE_STATES.Provisioning,
      PRODUCT_INSTANCE_STATES.Deprovisioning,
      PRODUCT_INSTANCE_STATES.Terminated,
      PRODUCT_INSTANCE_STATES.Updating,
    ];
    if (
      selectedItems &&
      selectedItems.length >= selectedItemsLengthToTurnDown
    ) {
      return !selectedItems.some((item) =>
        UnAcceptableStatesForTurningDown.includes(item.status)
      );
    }
    return false;
  }

  function isCardDisabled(target: ProvisionedProduct) {
    const UnAcceptableStatesForTurningDown = [
      PRODUCT_INSTANCE_STATES.Provisioning,
      PRODUCT_INSTANCE_STATES.Deprovisioning,
      PRODUCT_INSTANCE_STATES.Terminated,
      PRODUCT_INSTANCE_STATES.Updating,
    ];
    return UnAcceptableStatesForTurningDown.includes(target.status);
  }

  function hideUpgradeButton(target: ProvisionedProduct) {
    return (
      !target.upgradeAvailable ||
      INTERMEDIATE_PRODUCT_PROVISIONING_STATES.has(target.status)
    );
  }

  function disableUpgradeButton(provisionedProduct: ProvisionedProduct) {
    return (
      !!provisionedProduct.upgradeAvailable &&
      INTERMEDIATE_PRODUCT_STATES.has(provisionedProduct.status)
    );
  }

  function navigateToProductsScreen() {
    navigateTo(availableProvisionedProductRouteName);
  }

  function decideStatusIndicatorType(
    status: string
  ): StatusIndicatorProps.Type {
    return PRODUCT_INSTANCE_STATE_INDICATOR_MAP.get(status) || 'warning';
  }

  return {
    productType,
    targets: items,
    crumbs: getBreadcrumbItems(translations),
    isInTurnDownMode,
    isLoading: isLoading,
    isValidToTurnDown: isValidToTurnDown,
    turnDownConfirmVisible,
    propertyFilterProps,
    selectionType: selectionType,
    paginationProps: paginationProps,
    collectionProps: collectionProps,
    turnDownTimeOutInProgress: turnDownTimeOutInProgress,
    turnDownInProgress: turnDownInProgress,
    handleRemoveClick: handleRemoveClick,
    handleRemoveCancel: handleRemoveCancel,
    handleRemoveSubmit: handleRemoveSubmit,
    refreshWorkbenches: refreshWorkbenches,
    navigateToProductsScreen: navigateToProductsScreen,
    handleRemoveConfirmSubmit: handleRemoveConfirmSubmit,
    handleRemoveConfirmCancel: handleRemoveConfirmCancel,
    handleViewDetail: handleViewDetail,
    isFeatureAccessible: isFeatureAccessible,
    isFeatureEnabled,
    isCardDisabled: isCardDisabled,
    isProvisionedProductListLoading: isProvisionedProductListLoading,
    decideStatusIndicatorType: decideStatusIndicatorType,
    decideToHideUpgradeButton: hideUpgradeButton,
    decideToDisableUpgradeButton: disableUpgradeButton,
  };
}
