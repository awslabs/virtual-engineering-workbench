import {
  AvailableVersionDistribution,
  GetAvailableProductVersionsResponse,
  ProvisioningParameter
} from '../../services/API/proserve-wb-provisioning-api';
import { useCallback, useEffect, useState } from 'react';
import { ProductParameterState, visibleParameters } from '.';
import { useNotifications } from '../../components/layout';
import { extractErrorResponseMessage } from '../../utils/api-helpers';


export interface ServiceAPI {
  getAvailableProductVersions: (
    projectId: string,
    productId: string,
    stage: string,
    region: string
  ) => Promise<GetAvailableProductVersionsResponse>,

  upgradeProvisionedProduct: (
    projectId: string,
    provisionedProductId: string,
    provisioningParameters: ProvisioningParameter[],
    versionId: string
  ) => Promise<object>,
}

export interface SelectedVersionForUpgrade {
  versionId: string,
  versionName: string,
  stage: string,
  region: string,
}

interface Props {
  projectId: string,
  productId: string,
  provisionedProductId: string,
  serviceApi: ServiceAPI,
  selectedVersionForUpgrade: SelectedVersionForUpgrade,
  previouslyEnteredParameters?: ProvisioningParameter[],
}

const EMPTY_ARRAY_LENGTH = 0;
const i18n = {
  productVersionsFetchErrorTitle: 'Unable to fetch product version details.',
  upgradeSuccessMessageHeader: 'Upgrade started successfully.',
  upgradeSuccessMessageContent: 'Upgrade process may take a few minutes.',
  upgradeFailMessageHeader: 'Unable to upgrade the provisioned product.',
};


export function upgradeProvisionedProduct({
  serviceApi,
  projectId,
  productId,
  provisionedProductId,
  selectedVersionForUpgrade,
  previouslyEnteredParameters
}: Props) {

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [productVersions, setProductVersions] = useState<AvailableVersionDistribution[]>([]);
  const [productVersionsLoading, setProductVersionsLoading] = useState(false);
  const [startingUpgradeInProcess, setStartingUpgradeInProcess] = useState(false);
  const [productParameterState, setProductParameterState] = useState<ProductParameterState>({});

  const versionForUpgrade = productVersions.find(x => x.versionId === selectedVersionForUpgrade.versionId);

  const previouslyEnteredParameterDict = (previouslyEnteredParameters || []).
    reduce<ProductParameterState>((prev, curr) => {
      if (curr.key) {
        prev[curr.key] = curr.value;
      }
      return prev;
    }, {});

  const dataHasErrors = useCallback(() => {
    return Object.
      values(productParameterState).
      some(val => val === undefined || val === null || val.length === EMPTY_ARRAY_LENGTH);
  }, [productParameterState]);

  useEffect(() => {

    setProductVersionsLoading(true);

    serviceApi.getAvailableProductVersions(
      projectId, productId, selectedVersionForUpgrade.stage, selectedVersionForUpgrade.region
    ).then(d => {
      setProductVersions(d.availableProductVersions || []);
      const versionForUpgrade = d.availableProductVersions?.
        find(x => x.versionId === selectedVersionForUpgrade.versionId);

      setProductParameterState(
        (versionForUpgrade?.parameters || []).
          filter(visibleParameters).reduce<ProductParameterState>((prev, curr) => {
            prev[curr.parameterKey] = previouslyEnteredParameterDict[curr.parameterKey] || curr.defaultValue;
            return prev;
          }, {})
      );
    }).catch(async (e) => {
      showErrorNotification({
        header: i18n.productVersionsFetchErrorTitle,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setProductVersionsLoading(false);
    });
  }, []);

  return {
    productVersionsLoading,
    versionForUpgrade,
    productParameterState,
    handleProductParameterChange,
    dataHasErrors,
    previouslyEnteredParameterNames: new Set(Object.keys(previouslyEnteredParameterDict || {})),
    startingUpgradeInProcess,
    upgrade,
  };

  function handleProductParameterChange(key: string, value?: string) {
    const params = productParameterState;
    params[key] = value;
    setProductParameterState({ ...params });
  }

  function upgrade(): Promise<void> {
    if (!projectId) { return Promise.reject(); }

    setStartingUpgradeInProcess(true);
    return serviceApi.upgradeProvisionedProduct(
      projectId,
      provisionedProductId,
      Object.entries(productParameterState).map(([key, value]) => ({ key, value })),
      selectedVersionForUpgrade.versionId
    )
      .then(() => {
        showSuccessNotification({
          header: i18n.upgradeSuccessMessageHeader,
          content: i18n.upgradeSuccessMessageContent
        });
      })
      .catch(async (e) => {
        showErrorNotification({
          header: i18n.upgradeFailMessageHeader,
          content: await extractErrorResponseMessage(e)
        });
        throw e;
      })
      .finally(() => {
        setStartingUpgradeInProcess(false);
      });
  }

}