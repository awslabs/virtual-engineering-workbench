import { useEffect, useState } from 'react';
import { i18nProvisionVirtualTarget }
  from '../../components/pages/products/provision-product-new/provision-virtual-target.translations.ts';
import { useRecoilValue } from 'recoil';
import { RoleBasedFeature, selectedProjectState } from '../../state/index.ts';
import { provisioningAPI } from '../../services/index.ts';
import { extractAllErrorMessages, extractErrorResponseMessage, getApis } from '../../utils/api-helpers.ts';
import { useNotifications } from '../../components/layout/index.ts';
import {
  AdditionalConfiguration,
  AdditionalConfigurationParameter,
  AvailableProduct,
  AvailableVersionDistribution,
  ProductParameter,
  ProductParameterMetaData
} from '../../services/API/proserve-wb-provisioning-api/index.ts';
import { ProductParameterState, visibleParameters } from './index.ts';
import { useRoleAccessToggle } from '../role-access-toggle.ts';
import { useUserProfile } from '../../components/user-preferences/user-profile.hook.ts';
import { useFeatureToggles } from '../../components/feature-toggles/feature-toggle.hook.ts';
import { Feature } from '../../components/feature-toggles/feature-toggle.state.ts';
import { i18nWorkbenchSteps } from
  '../../components/pages/products/provision-product-new-steps/provision-workbench-steps.translations.ts';

export type ProvisionProductTranslations = typeof i18nProvisionVirtualTarget;
export type StepsTranslations = typeof i18nWorkbenchSteps;

interface Props {
  productId: string,
  availableRegions: string[],
  availableStages: string[],
  i18n: ProvisionProductTranslations,
  onProvisioned?: () => void,
  vvJobName?: string,
  vvPlatform?: string,
  vvVersion?: string,
  vvArtifactUpstreamPath?: string,
  productType?: string,
}
export function useProvisionProduct({
  productId,
  availableRegions,
  availableStages,
  i18n,
  onProvisioned,
  vvJobName,
  vvPlatform,
  vvVersion,
  vvArtifactUpstreamPath,
  productType
}: Props) {
  const selectedProject = useRecoilValue(selectedProjectState);
  const { showErrorNotification, clearNotifications, showSuccessNotification } = useNotifications();
  const { userProfile } = useUserProfile({ serviceAPIs: getApis() });
  const { isFeatureEnabled } = useFeatureToggles();
  const [selectedVersionRegion, setSelectedVersionRegion] = useState<string>(defaultSelectedRegion());
  const [selectedVersionStage, setSelectedVersionStage] = useState<string>(availableStages[0]);
  const [selectedVersion, setSelectedVersion] = useState<AvailableVersionDistribution | undefined>();
  const [productVersions, setProductVersions] = useState<AvailableVersionDistribution[]>([]);
  const [productVersionsLoading, setProductVersionsLoading] = useState(false);
  const [productParameters, setProductParameters] = useState<ProductParameter[]>();
  const [productParameterState, setProductParameterState] = useState<ProductParameterState>({});
  const [productProvisionInProgress, setProductProvisionInProgress] = useState(false);
  const productParametersLoading = productVersions === undefined;
  const [isExperimentalWorkbench, setIsExperimentalWorkbench] = useState(false);
  const [isExperimentalWorkbenchAvailable, setIsExperimentalWorkbenchAvailable] = useState(false);
  const [productVersionMetadata, setProductVersionMetadata] = useState<{
    [key: string]: ProductParameterMetaData,
  }>();
  const isFeatureAccessible = useRoleAccessToggle();
  const [selectedAvailableProduct, setSelectedAvailableProduct] = useState<AvailableProduct | undefined>();

  // eslint-disable-next-line complexity
  useEffect(() => {
    if (
      (productType === 'WORKBENCH' || productType === 'VIRTUAL_TARGET') &&
      selectedVersionStage === 'QA' &&
      isFeatureAccessible(RoleBasedFeature.ProvisionExperimentalWorkbench) &&
      isFeatureEnabled(Feature.ExperimentalWorkbench) &&
      productParameters?.some(x=> x.parameterKey === 'Experimental')
    ) {
      setIsExperimentalWorkbenchAvailable(true);
    } else {
      setIsExperimentalWorkbenchAvailable(false);
    }
  }, [productType, selectedVersionStage, productParameters]);

  useEffect(() => {
    if (!isFeatureAccessible(RoleBasedFeature.ChooseStageInProductSelection)) {
      setSelectedVersionStage('PROD');
    }
  }, [isFeatureAccessible]);

  function defaultSelectedRegion() {
    const defaultRegion = availableRegions.some(region => region === userProfile.preferredRegion) ?
      userProfile.preferredRegion : availableRegions[0];

    return defaultRegion;
  }

  useEffect(() => {
    if (!selectedProject.projectId) {
      return;
    }

    clearNotifications();
    setProductVersionsLoading(true);
    provisioningAPI.getAvailableProductVersions(
      selectedProject.projectId,
      productId,
      selectedVersionStage,
      selectedVersionRegion
    ).then(response => {
      setProductVersions(response.availableProductVersions ?? []);
    }).catch(async e => {
      showErrorNotification({
        header: i18n.productVersionsFetchErrorTitle,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setProductVersionsLoading(false);
    });

  }, [selectedVersionRegion, selectedVersionStage]);

  useEffect(() => {
    if (!selectedProject.projectId || !productType) {
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-magic-numbers
    const prepairedProductType = productType.charAt(0) + productType.slice(1).toLowerCase();

    clearNotifications();
    setProductVersionsLoading(true);
    provisioningAPI.getAvailableProducts(
      selectedProject.projectId,
      prepairedProductType
    ).then(response => {
      setSelectedAvailableProduct(response.availableProducts.find(ap => ap.productId === productId));
    }).catch(async e => {
      showErrorNotification({
        header: i18n.productVersionsFetchErrorTitle,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setProductVersionsLoading(false);
    });

  }, [productId]);

  useEffect(() => {
    setProductVersionMetadata(undefined);

    if (selectedVersion && selectedVersion.parameters) {
      setProductParameters(selectedVersion.parameters);
      setProductVersionMetadata(selectedVersion.metadata);
      setProductParameterState(
        selectedVersion.parameters.filter(visibleParameters).reduce<ProductParameterState>((prev, curr) => {
          prev[curr.parameterKey] = curr.defaultValue;
          return prev;
        }, {})
      );
    }

  }, [selectedVersion]);

  const isAdditionalConfiguration = () => {
    return vvJobName || vvPlatform || vvVersion || vvArtifactUpstreamPath;
  };

  // eslint-disable-next-line complexity
  function provisionProduct() {
    if (!selectedProject.projectId || !selectedVersion) {
      return Promise.resolve();
    }

    clearNotifications();
    setProductProvisionInProgress(true);

    if (isExperimentalWorkbench) {
      handleProductParameterChange('Experimental', 'True');
    }

    if (isAdditionalConfiguration()) {
      const additionalConfigurationParameters: AdditionalConfigurationParameter[] = [
        { key: 'jobName', value: vvJobName },
        { key: 'platformType', value: vvPlatform },
        { key: 'version', value: vvVersion },
        { key: 'artifactUpstreamPath', value: vvArtifactUpstreamPath }
      ];

      const additionalConfiguration: AdditionalConfiguration[] = [{
        type: 'VVPL_PROVISIONED_PRODUCT_CONFIGURATION',
        parameters: additionalConfigurationParameters
      }];

      return provisioningAPI.launchProduct(
        selectedProject.projectId,
        productId,
        selectedVersion.versionId,
        Object.entries(productParameterState).map(([key, value]) => ({ key, value })),
        selectedVersionStage,
        selectedVersionRegion,
        additionalConfiguration
      ).then(() => {
        showSuccessNotification({
          header: i18n.productProvisionSuccessTitle,
          content: i18n.productProvisionSuccessText
        });
        onProvisioned?.();
      }).catch(async e => {
        showErrorNotification({
          header: i18n.productProvisionError,
          content: await extractAllErrorMessages(e),
        });
      }).finally(() => {
        setProductProvisionInProgress(false);
      });
    }

    return provisioningAPI.launchProduct(
      selectedProject.projectId,
      productId,
      selectedVersion.versionId,
      Object.entries(productParameterState).map(([key, value]) => ({ key, value })),
      selectedVersionStage,
      selectedVersionRegion,
    ).then(() => {
      showSuccessNotification({
        header: i18n.productProvisionSuccessTitle,
        content: i18n.productProvisionSuccessText
      });
      onProvisioned?.();
    }).catch(async e => {
      showErrorNotification({
        header: i18n.productProvisionError,
        content: await extractAllErrorMessages(e),
      });
    }).finally(() => {
      setProductProvisionInProgress(false);
    });
  }

  function handleProductParameterChange(key: string, value?: string) {
    const params = productParameterState;
    params[key] = value;

    setProductParameterState({ ...params });
  }

  return {
    selectedVersionRegion,
    setSelectedVersionRegion,
    selectedVersionStage,
    setSelectedVersionStage,
    selectedVersion,
    setSelectedVersion,
    productVersions,
    productVersionsLoading,
    productParameters,
    productParameterState,
    handleProductParameterChange,
    provisionProduct,
    productProvisionInProgress,
    productParametersLoading,
    productVersionMetadata,
    isExperimentalWorkbench,
    setIsExperimentalWorkbench,
    isExperimentalWorkbenchAvailable,
    selectedAvailableProduct,
  };
}