/* eslint-disable @typescript-eslint/no-magic-numbers */
import { FC, useEffect } from 'react';
import { UserPrompt } from '../../shared/user-prompt';
import { i18n } from './update-provisioned-product-prompt.translations';
import {
  ProvisionedProduct,
  GetAvailableProductVersionsResponse,
  ProvisioningParameter,
  AvailableVersionDistribution
} from '../../../../services/API/proserve-wb-provisioning-api';
import { upgradeProvisionedProduct } from './update-provisioned-product-prompt.logic';
import { ProductParameterDropdown } from '../../products/product-parameters/product-parameter-dropdown';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../state';
import { FormField, Select, SelectProps, Spinner } from '@cloudscape-design/components';
import { compareSemanticVersions } from '../../../../hooks/provisioning';

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

type Props = {
  provisionedProduct: ProvisionedProduct,
  updateConfirmVisible: boolean,
  setUpdatePromptVisible: (visible: boolean) => void,
  serviceApi: ServiceAPI,
  stateActionCompleteHandler?: () => void,
  updateType: string,
};

export const UpdateProvisionedProductPrompt: FC<Props> = ({
  provisionedProduct,
  updateConfirmVisible,
  setUpdatePromptVisible,
  serviceApi,
  stateActionCompleteHandler,
  updateType,
}) => {
  const selectedProject = useRecoilValue(selectedProjectState);

  const upgradeData = upgradeProvisionedProduct({
    provisionedProduct,
    serviceApi,
    stateActionCompleteHandler,
    updateType
  });

  const {
    productParameter,
    startingUpgradeInProcess,
    upgrade,
    productVersionsLoading,
    handleProductParameterChange,
    supportedInstanceTypes,
    selectedVersion,
    setSelectedVersion,
    availableVersionsToUpdate
  } = upgradeData;

  function mapVersions(versions: AvailableVersionDistribution[]): SelectProps.Option[] {
    return versions.sort(compareSemanticVersions()).map<SelectProps.Option>(mapVersion);
  }

  function mapVersion(version: AvailableVersionDistribution): SelectProps.Option {
    return {
      label: getVersionLabel(version.versionName, version.versionDescription),
      value: version.versionId,
      tags: [version.isRecommendedVersion ? i18n.recommendedVersionTag : '']
    };
  }

  function getVersionLabel(versionName: string, versionDescription?: string) {
    if (!versionDescription) {
      return versionName;
    }
    return versionName + ' - ' + versionDescription;
  }

  useEffect(() => {
    if (!selectedProject.projectId || !provisionedProduct) {
      setUpdatePromptVisible(false);
    }
  }, [selectedProject.projectId, provisionedProduct, setUpdatePromptVisible]);

  // If there's no project ID or provisioned product, don't render anything
  if (!selectedProject.projectId || !provisionedProduct) {
    return null;
  }

  function setRecommendedOptionWarning() {
    if (productParameter) {
      const recommendedInstanceType = productParameter.parameterConstraints?.allowedValues?.find(
        allowedValue => allowedValue === provisionedProduct.recommendedInstanceType
      );
      productParameter.parameterMetaData = {};
      productParameter.parameterMetaData.optionWarnings = productParameter.parameterMetaData?.
        optionWarnings ?? {};

      const optionalWarnings =
        productParameter.parameterMetaData.optionWarnings as { [key: string]: string }
      ;
      if (recommendedInstanceType) {
        optionalWarnings[recommendedInstanceType] = 'Recommended';
      }
      productParameter.parameterMetaData.optionWarnings = optionalWarnings;
    }
  }

  function createUpdateInstanceTypePromptContent() {

    const currentInstanceType = provisionedProduct?.provisioningParameters?.find(
      item => item.key === 'InstanceType'
    )?.value;
    setRecommendedOptionWarning();
    return productParameter && !productVersionsLoading ?
      supportedInstanceTypes.length > 1 ?
        <>
          <p>{i18n.updateModalText(updateType)}</p>
          <ProductParameterDropdown
            parameter={productParameter}
            onChange={(value) => {
              handleProductParameterChange(productParameter.parameterKey, value);
            }}
            showDescription={false}
            removeParameterOption={currentInstanceType}
          />
        </>
        :
        <p>{i18n.noSupportedInstanceTypesText}</p>
      :
      <Spinner></Spinner>;
  }

  // eslint-disable-next-line complexity
  function createUpdateVersionPromptContent() {
    return !productVersionsLoading && availableVersionsToUpdate ?
      availableVersionsToUpdate.length > 0 ?
        <>
          <p>{i18n.updateModalText(updateType)}</p>
          <p>{i18n.updateVersionModalInfo}</p>
          <FormField
            label={i18n.versionLabel}
          >
            <Select
              selectedOption={mapVersion(selectedVersion || {} as AvailableVersionDistribution)}
              onChange={({ detail }) => {
                setSelectedVersion?.(
                  availableVersionsToUpdate.find((v: { versionId: string | undefined }) =>
                    v.versionId === detail.selectedOption.value));
              }}
              options={mapVersions(availableVersionsToUpdate)}
              data-test="select-version"
            />
          </FormField>
        </> : <p>{i18n.noSupportedVersionsText}</p>
      : <Spinner></Spinner>;
  }

  function handleConfirmPrompt() {
    upgrade();
    setUpdatePromptVisible(false);
  }

  const createUpdatePromptContent = () => {
    return updateType === 'version' ?
      createUpdateVersionPromptContent() :
      createUpdateInstanceTypePromptContent();
  };

  const isConfirmButtonDisabled = () => {
    return updateType === 'version' ?
      availableVersionsToUpdate && availableVersionsToUpdate.length < 1 :
      supportedInstanceTypes.length < 2;
  };

  return (
    <UserPrompt
      onConfirm={handleConfirmPrompt}
      onCancel={() => setUpdatePromptVisible(false)}
      headerText={i18n.updateModalHeader(updateType)}
      content={createUpdatePromptContent()}
      cancelText={i18n.updateModalCancel}
      confirmText={i18n.updateModalOK}
      confirmButtonLoading={startingUpgradeInProcess}
      visible={updateConfirmVisible}
      confirmButtonDisabled={isConfirmButtonDisabled()}
      data-test="update-provisioned-product-prompt"
    />
  );
};