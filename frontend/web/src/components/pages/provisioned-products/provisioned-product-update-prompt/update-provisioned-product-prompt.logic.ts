import {
  GetAvailableProductVersionsResponse,
  ProvisioningParameter,
  ProvisionedProduct,
  AvailableVersionDistribution
} from './../../../../services/API/proserve-wb-provisioning-api';
import { useEffect, useState } from 'react';
import { ProductParameterState } from './../../../../hooks/provisioning/provisioning.helpers';
import { useNotifications } from '../../../../components/layout';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers';
import { ProductParameter } from '../../../../services/API/proserve-wb-provisioning-api';


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
  provisionedProduct: ProvisionedProduct,
  serviceApi: ServiceAPI,
  stateActionCompleteHandler?: () => void,
  updateType: string,
}

const i18n = {
  productVersionsFetchErrorTitle: 'Unable to fetch product version details.',
  upgradeSuccessMessageHeader: 'Upgrade started successfully.',
  upgradeSuccessMessageContent: 'Upgrade process may take a few minutes.',
  upgradeFailMessageHeader: 'Unable to upgrade the provisioned product.',
};


export function upgradeProvisionedProduct({
  serviceApi,
  provisionedProduct,
  stateActionCompleteHandler,
  updateType
}: Props) {
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [productVersionsLoading, setProductVersionsLoading] = useState(false);
  const [startingUpgradeInProcess, setStartingUpgradeInProcess] = useState(false);
  const [productParameterState, setProductParameterState] = useState<ProductParameterState>({});
  const [productParameter, setProductParameter] = useState<ProductParameter>();
  const [supportedInstanceTypes, setSupportedInstanceType] = useState<string[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<AvailableVersionDistribution>();
  const [availableVersionsToUpdate, setAvailableVersionsToUpdate] =
    useState<AvailableVersionDistribution[]>();

  useEffect(() => {
    if (!provisionedProduct) {
      return; // Exit early if provisionedProduct is not available
    }

    setProductVersionsLoading(true);
    serviceApi.getAvailableProductVersions(
      provisionedProduct.projectId,
      provisionedProduct.productId,
      provisionedProduct.stage,
      provisionedProduct.region
    ).then(response => {
      if (!response.availableProductVersions) {
        return;
      }
      const currentVersion = response.availableProductVersions.find(
        (v) => v.versionId === provisionedProduct.versionId
      );

      const versionsToUpdate = response.availableProductVersions.filter(
        version => version.versionId !== provisionedProduct.versionId);
      setAvailableVersionsToUpdate(versionsToUpdate);
      setSelectedVersion(versionsToUpdate[0]);

      const versionParameters = currentVersion?.parameters;
      const versionInstanceTypeParam = versionParameters?.find((v) => v.parameterKey === 'InstanceType');
      if (!versionInstanceTypeParam) {
        return;
      }

      setProductParameter(versionInstanceTypeParam);
      setProductParameterState(
        { [versionInstanceTypeParam.parameterKey]: versionInstanceTypeParam.defaultValue }
      );
      const versionSupportedInstanceTypes = versionInstanceTypeParam?.parameterConstraints?.allowedValues;
      if (!versionSupportedInstanceTypes) {
        return;
      }
      setSupportedInstanceType(versionSupportedInstanceTypes);
    }).catch(async (e) => {
      showErrorNotification({
        header: i18n.productVersionsFetchErrorTitle,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setProductVersionsLoading(false);
    });
  }, [provisionedProduct, serviceApi]);

  const handleProductParameterChange = (key: string, value?: string) => {
    setProductParameterState(prev => ({ ...prev, [key]: value }));
  };

  const getProductParametersForUpdate = () => {
    return updateType === 'version' ? [] :
      Object.entries(productParameterState).map(([key, value]) => ({ key, value }));
  };

  const getVersionForUpdate = () => {
    return updateType === 'version' && selectedVersion ?
      selectedVersion.versionId :
      provisionedProduct.versionId;
  };

  const upgrade = async (): Promise<void> => {
    if (!provisionedProduct) {
      throw new Error('Cannot upgrade: provisionedProduct is not available');
    }

    setStartingUpgradeInProcess(true);
    try {
      await serviceApi.upgradeProvisionedProduct(
        provisionedProduct.projectId,
        provisionedProduct.provisionedProductId,
        getProductParametersForUpdate(),
        getVersionForUpdate()
      );
      showSuccessNotification({
        header: i18n.upgradeSuccessMessageHeader,
        content: i18n.upgradeSuccessMessageContent
      });
    } catch (e) {
      showErrorNotification({
        header: i18n.upgradeFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
      throw e;
    } finally {
      setStartingUpgradeInProcess(false);
      stateActionCompleteHandler?.();
    }
  };

  return {
    productParameter,
    supportedInstanceTypes,
    productVersionsLoading,
    productParameterState,
    handleProductParameterChange,
    previouslyEnteredParameterNames: new Set(Object.keys(provisionedProduct?.provisioningParameters || {})),
    startingUpgradeInProcess,
    upgrade,
    selectedVersion,
    setSelectedVersion,
    availableVersionsToUpdate
  };
}