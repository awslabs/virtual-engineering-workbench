import { useState, useEffect } from 'react';
import { BreadcrumbItem, useNotifications } from '../../layout';
import {
  PRODUCT_INSTANCE_STATES,
  PRODUCT_STATE_TRANSLATIONS,
  PRODUCT_TYPE_MAP,
  ProvisionedProductsAdministrationHookOutput,
  ProvisionedProductsAdministrationHookProps,
} from './interface';
import {
  ProvisionedProduct,
} from '../../../services/API/proserve-wb-provisioning-api';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../state';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { CompareDates } from '../shared/compare-dates';
import { SelectProps } from '@cloudscape-design/components';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { i18n } from './translations';

export const fetchKey = 'provisioning/products/all';

const PAGE_SIZE = 20;
const SMALL_TABLE_PAGE_SIZE = 5;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;

export const ACTION_DISABLED_STATES = {
  Stop: [
    PRODUCT_INSTANCE_STATES.Starting,
    PRODUCT_INSTANCE_STATES.Stopping,
    PRODUCT_INSTANCE_STATES.Stopped,
    PRODUCT_INSTANCE_STATES.ProvisioningError,
    PRODUCT_INSTANCE_STATES.Provisioning,
    PRODUCT_INSTANCE_STATES.Deprovisioning,
    PRODUCT_INSTANCE_STATES.Updating,
    PRODUCT_INSTANCE_STATES.ConfigurationInProgress,
    PRODUCT_INSTANCE_STATES.ConfigurationFailed,
  ],
  Terminate: [
    PRODUCT_INSTANCE_STATES.Provisioning,
    PRODUCT_INSTANCE_STATES.Deprovisioning,
    PRODUCT_INSTANCE_STATES.Terminated,
    PRODUCT_INSTANCE_STATES.Updating,
  ],
};

export const useProvisionedProductsAdministration = (
  hookProps: ProvisionedProductsAdministrationHookProps
): ProvisionedProductsAdministrationHookOutput => {
  const { serviceAPI, translations } = hookProps;
  const selectedProject = useRecoilValue(selectedProjectState);
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [ isLoading, setIsLoading ] = useState(false);
  const [ provisionedProducts, setProvisionedProducts ] = useState<ProvisionedProduct[]>([]);
  const [pagingToken, setPagingToken] = useState<string | undefined>();


  const PRODUCT_DEFAULT_OPTION = {
    label: translations.anyProductNameOption,
    value: '',
  };
  const PRODUCT_TYPE_DEFAULT_OPTION = {
    label: translations.anyProductTypeOption,
    value: '',
  };
  const STATUS_DEFAULT_OPTION = {
    label: translations.anyStatusOption,
    value: '',
  };
  const ADDITIONAL_INFORMATION_OPTION = {
    label: translations.anyAdditionalInformationOption,
    value: '',
  };

  const [
    stopProvisionedProductsPromptOpen,
    setStopProvisionedProductsPromptOpen,
  ] = useState(false);
  const [
    stopProvisionedProductsInProgress,
    setStopProvisionedProductsInProgress,
  ] = useState(false);
  const [
    terminateProvisionedProductsPromptOpen,
    setTerminateProvisionedProductsPromptOpen,
  ] = useState(false);
  const [
    terminateProvisionedProductsInProgress,
    setTerminateProvisionedProductsInProgress,
  ] = useState(false);
  const [selectedProductOption, setSelectedProductOption] =
    useState<SelectProps.Option>(PRODUCT_DEFAULT_OPTION);
  const [selectedProductTypeOption, setSelectedProductTypeOption] =
    useState<SelectProps.Option>(PRODUCT_TYPE_DEFAULT_OPTION);
  const [selectedStatusOption, setSelectedStatusOption] =
    useState<SelectProps.Option>(STATUS_DEFAULT_OPTION);
  const [selectedAdditionalInformationOption, setSelectedAdditionalInformationOption] =
    useState<SelectProps.Option>(ADDITIONAL_INFORMATION_OPTION);

  const loadrovisionedProducts = (pagingToken?: string) => {
    if (!selectedProject.projectId) {
      return;
    }

    setIsLoading(true);

    serviceAPI.getPaginatedProvisionedProducts(
      selectedProject.projectId,
      pagingToken,
    )
      .then((response) => {
        if (pagingToken) {
          setProvisionedProducts([...provisionedProducts, ...response.provisionedProducts]);
        } else {
          setProvisionedProducts(response.provisionedProducts ?? []);
        }

        if (response.pagingKey) {
          setPagingToken(response.pagingKey);
        }
      }).catch(async e => {
        showErrorNotification({
          header: i18n.provisionedProductsFetchError,
          content: await extractErrorResponseMessage(e)
        });
      }).finally(() => {
        setIsLoading(false);
      });

  };

  useEffect(() => {
    loadrovisionedProducts();
  }, [selectedProject]);

  useEffect(() => {
    if (pagingToken) {
      loadrovisionedProducts(pagingToken);
    }
  }, [pagingToken]);

  const matchProductOption = (provisionedProduct: ProvisionedProduct) => {
    return (
      !selectedProductOption.value ||
      provisionedProduct.productName === selectedProductOption.value
    );
  };

  const matchProductTypeOption = (provisionedProduct: ProvisionedProduct) => {
    return (
      !selectedProductTypeOption.value ||
      provisionedProduct.provisionedProductType ===
        selectedProductTypeOption.value
    );
  };

  const matchStatusOption = (provisionedProduct: ProvisionedProduct) => {
    return (
      !selectedStatusOption.value ||
      provisionedProduct.status === selectedStatusOption.value
    );
  };

  const matchAdditionalInformationOption = (provisionedProduct: ProvisionedProduct) => {
    if (!selectedAdditionalInformationOption.value) { return true; }
    switch (selectedAdditionalInformationOption.value) {
      case translations.experimentalProductBanner:
        return provisionedProduct?.experimental ? true : false;
      default:
        return false;
    }
  };

  const getFilteredProvisionedProducts = () => {
    return (provisionedProducts || [])
      .filter(
        (x) =>
          matchProductOption(x) &&
          matchProductTypeOption(x) &&
          matchStatusOption(x) &&
          matchAdditionalInformationOption(x)
      )
      .sort((a, b) => CompareDates(a.lastUpdateDate, b.lastUpdateDate));
  };

  const provisionedProductsTableProps = useCollection(
    getFilteredProvisionedProducts(),
    {
      filtering: {},
      selection: { trackBy: 'provisionedProductId' },
      sorting: {
        defaultState: {
          sortingColumn: { sortingField: 'lastUpdateDate' },
          isDescending: true,
        },
      },
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE },
    }
  );

  const { collectionProps } = provisionedProductsTableProps;

  const selectedProvisionedProductsTableProps = useCollection(
    collectionProps.selectedItems || [],
    {
      filtering: {},
      selection: { trackBy: 'provisionedProductId' },
      sorting: {
        defaultState: {
          sortingColumn: { sortingField: 'lastUpdateDate' },
          isDescending: true,
        },
      },
      pagination: { defaultPage: PAGE_INDEX, pageSize: SMALL_TABLE_PAGE_SIZE },
    }
  );

  const sortOptions = (options: SelectProps.Option[]) => {
    return options.sort((a, b) => (a.label || '').localeCompare(b.label || ''));
  };

  const getProductOptions = () => {
    const options: SelectProps.Option[] = [PRODUCT_DEFAULT_OPTION];
    const productNames = Array.from(
      new Set(provisionedProducts.map((x) => x.productName) || [])
    );
    productNames.forEach((productName) => {
      options.push({ label: productName, value: productName });
    });
    return sortOptions(options);
  };

  const getProductTypeOptions = () => {
    const options: SelectProps.Option[] = [PRODUCT_TYPE_DEFAULT_OPTION];
    const productTypes = Array.from(
      new Set(
        provisionedProducts.map((x) => x.provisionedProductType) || []
      )
    );
    productTypes.forEach((productType) => {
      options.push({
        label: PRODUCT_TYPE_MAP[productType || 'UNKNOWN'],
        value: productType,
      });
    });
    return sortOptions(options);
  };

  const getStatusOptions = () => {
    const options: SelectProps.Option[] = [STATUS_DEFAULT_OPTION];
    const statuses = Array.from(
      new Set(provisionedProducts.map((x) => x.status) || [])
    );
    statuses.forEach((status) => {
      options.push({ label: PRODUCT_STATE_TRANSLATIONS.get(status) || status, value: status });
    });
    return sortOptions(options);
  };

  const getAdditionalInformationOptions = () => {
    const options: SelectProps.Option[] = [ADDITIONAL_INFORMATION_OPTION];
    for (const provisionedProduct of provisionedProducts || []) {
      if (provisionedProduct?.experimental) {
        options.push(
          {
            label: translations.experimentalProductBanner,
            value: translations.experimentalProductBanner
          }
        );
        break;
      }
    }
    return sortOptions(options);
  };

  const reloadProvisionedProducts = () => {
    setPagingToken(undefined);
    loadrovisionedProducts();
  };

  const getBreadcrumbItems = (): BreadcrumbItem[] => {
    return [{ path: translations.breadCrumbItem1, href: '#' }];
  };

  const getSelectedProvisionedProductIds = () => {
    return (collectionProps.selectedItems || []).map(
      (x) => x.provisionedProductId
    );
  };

  const getSelectedProvisionedProducts = () => collectionProps.selectedItems || [];

  const stopProvisionedProducts = () => {
    if (
      selectedProject?.projectId &&
      !preventAction(ACTION_DISABLED_STATES.Stop)
    ) {
      setStopProvisionedProductsInProgress(true);
      serviceAPI
        .stopProvisionedProducts(
          selectedProject.projectId,
          getSelectedProvisionedProductIds()
        )
        .then(() => {
          showSuccessNotification({
            header: translations.stopSuccessMessageHeader,
            content: translations.stopSuccessMessageContent,
          });
          setStopProvisionedProductsPromptOpen(false);
          reloadProvisionedProducts();
        })
        .catch(async (e) => {
          showErrorNotification({
            header: translations.stopFailedMessageHeader,
            content: await extractErrorResponseMessage(e),
          });
        })
        .finally(() => setStopProvisionedProductsInProgress(false));
    }
  };

  const terminateProvisionedProducts = () => {
    if (
      selectedProject?.projectId &&
      !preventAction(ACTION_DISABLED_STATES.Terminate)
    ) {
      setTerminateProvisionedProductsInProgress(true);
      serviceAPI
        .removeProvisionedProducts(
          selectedProject.projectId,
          getSelectedProvisionedProductIds()
        )
        .then(() => {
          showSuccessNotification({
            header: translations.terminateSuccessMessageHeader,
            content: translations.terminateSuccessMessageContent,
          });
          setTerminateProvisionedProductsPromptOpen(false);
          reloadProvisionedProducts();
        })
        .catch(async (e) => {
          showErrorNotification({
            header: translations.terminateFailedMessageHeader,
            content: await extractErrorResponseMessage(e),
          });
        })
        .finally(() => setTerminateProvisionedProductsInProgress(false));
    }
  };

  // eslint-disable-next-line complexity
  function isItemSelected(
    predicate?: (provisionedProduct: ProvisionedProduct) => boolean
  ) {
    return (
      collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined &&
      (!predicate ||
        collectionProps.selectedItems.every((provisionedProduct) =>
          predicate(provisionedProduct)
        ))
    );
  }

  function preventAction(actionDisabledStates: string[]) {
    return (
      !isItemSelected() ||
      isItemSelected((provisioneProduct) =>
        actionDisabledStates.includes(provisioneProduct.status)
      )
    );
  }

  return {
    breadcrumbItems: getBreadcrumbItems(),
    provisionedProducts: provisionedProducts || [],
    provisionedProductsLoading: isLoading,
    provisionedProductsTableProps,
    selectedProvisionedProductsTableProps,
    productOptions: getProductOptions(),
    selectedProductOption,
    setSelectedProductOption,
    productTypeOptions: getProductTypeOptions(),
    selectedProductTypeOption,
    setSelectedProductTypeOption,
    statusOptions: getStatusOptions(),
    selectedStatusOption,
    setSelectedStatusOption,
    additionalInformationOptions: getAdditionalInformationOptions(),
    selectedAdditionalInformationOption,
    setSelectedAdditionalInformationOption,
    reloadProvisionedProducts,
    stopActionDisabled: preventAction(ACTION_DISABLED_STATES.Stop),
    stopProvisionedProductsPromptOpen,
    setStopProvisionedProductsPromptOpen,
    stopProvisionedProductsInProgress,
    stopProvisionedProducts,
    terminateActionDisabled: preventAction(ACTION_DISABLED_STATES.Terminate),
    terminateProvisionedProductsPromptOpen,
    setTerminateProvisionedProductsPromptOpen,
    terminateProvisionedProductsInProgress,
    terminateProvisionedProducts,
    getSelectedProvisionedProducts,
  };
};
