import { Wizard, WizardProps } from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n, i18nCancelConfirm, i18nWizard } from './product-version-wizard.translations';
import {
  ProductVersionWizardStep1,
  ProductVersionWizardStep2,
  ProductVersionWizardStep3
} from '.';
import {
  VersionSummary,
} from '../../../../../services/API/proserve-wb-publishing-api';
import { useProductVersionWizard } from './product-version-wizard.logic';
import { CancelPrompt } from '../../..';
import { publishingAPI } from '../../../../../services';

interface ProductVersionWizardProps {
  projectId: string,
  productId: string,
  productVersion?: VersionSummary,
  productVersionYamlDefinition?: string,
  wizardCancelAction: () => void,
  wizardSubmitAction: ({
    productVersionDescription,
    versionReleaseType,
    amiId,
    versionTemplateDefinition,
    baseMajorVersion,
  }:{
    productVersionDescription: string,
    versionReleaseType: string,
    amiId?: string,
    versionTemplateDefinition: string,
    baseMajorVersion?: number,
  }) => void,
  wizardSubmitInProgress: boolean,
  activeStepIndex: number,
  setActiveStepIndex: (step: number) => any,
}


// eslint-disable-next-line complexity
export const ProductVersionWizard: FC<ProductVersionWizardProps> = ({
  projectId,
  productId,
  productVersion,
  wizardCancelAction,
  wizardSubmitAction,
  wizardSubmitInProgress,
  activeStepIndex,
  setActiveStepIndex
}) => {
  const {
    isUpdate,
    isVersionReleaseTypeValid,
    isAmiSelectValid,
    handleOnNavigate,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    yamlDefinition,
    setYamlDefinition,
    originalYamlDefinition,
    isYamlDefinitionValidationInProgress,
    isYamlDefinitionValid,
    setIsYamlDefinitionValid,
    productVersionDescription,
    setProductVersionDescription,
    isProductVersionDescriptionValid,
    amis,
    selectedAmi,
    setSelectedAmi,
    amisLoading,
    versionReleaseTypes,
    versionReleaseType,
    setVersionReleaseType,
    yamlDefinitionLoading,
    baseMajorVersions,
    isBaseMajorVersionsLoading,
    selectedBaseMajorVersion,
    setSelectedBaseMajorVersion,
    releasedVersions,
    fetchVersionYaml,
  } = useProductVersionWizard({
    projectId,
    productId,
    productVersion: productVersion || {} as VersionSummary,
    serviceApi: publishingAPI,
    activeStepIndex,
    setActiveStepIndex
  });
  const stepDefinitions: WizardProps.Step[] = [
    {
      title: i18n.step1Title,
      content: <ProductVersionWizardStep1
        isUpdate={isUpdate}
        productVersionDescription={productVersionDescription}
        setProductVersionDescription={setProductVersionDescription}
        isProductVersionDescriptionValid={isProductVersionDescriptionValid(productVersionDescription)}
        versionReleaseTypes={versionReleaseTypes}
        versionReleaseType={versionReleaseType}
        setVersionReleaseType={setVersionReleaseType}
        isVersionReleaseTypeValid={isVersionReleaseTypeValid}
        isAmiSelectValid={isAmiSelectValid}
        amis={amis ?? []}
        selectedAmi={selectedAmi}
        setSelectedAmi={setSelectedAmi}
        isAmisLoading={amisLoading}
        baseMajorVersions={baseMajorVersions ?? []}
        isBaseMajorVersionsLoading={isBaseMajorVersionsLoading}
        selectedBaseMajorVersion={selectedBaseMajorVersion!}
        setSelectedBaseMajorVersion={setSelectedBaseMajorVersion}
      />
    },
    {
      title: i18n.step2Title,
      content: <ProductVersionWizardStep2
        yamlDefinition={yamlDefinition}
        setYamlDefinition={setYamlDefinition}
        isYamlDefinitionValid={isYamlDefinitionValid}
        setIsYamlDefinitionValid={setIsYamlDefinitionValid}
        isYamlDefinitionLoading={yamlDefinitionLoading}
      />
    },
    {
      title: i18n.step3Title,
      content: <ProductVersionWizardStep3
        setActiveStepIndex={setActiveStepIndex}
        productVersionDescription={productVersionDescription}
        yamlDefinition={yamlDefinition}
        originalYamlDefinition={originalYamlDefinition || undefined}
        releasedVersions={releasedVersions}
        fetchVersionYaml={fetchVersionYaml}
        versionReleaseType={versionReleaseType}
      />
    },
  ];

  return <>
    <CancelPrompt
      cancelConfirmVisible={cancelConfirmVisible}
      setCancelConfirmVisible={setCancelConfirmVisible}
      handleCancelConfirm={wizardCancelAction}
      i18nStrings={i18nCancelConfirm(isUpdate)}
    />
    <Wizard
      steps={stepDefinitions}
      activeStepIndex={activeStepIndex}
      i18nStrings={i18nWizard(isUpdate)}
      onNavigate={({ detail }) => handleOnNavigate(detail)}
      isLoadingNextStep={isYamlDefinitionValidationInProgress || wizardSubmitInProgress}
      onSubmit={() =>
        wizardSubmitAction(
          {
            productVersionDescription: productVersionDescription.trim(),
            versionReleaseType: versionReleaseType.trim(),
            amiId: selectedAmi?.amiId,
            versionTemplateDefinition: yamlDefinition,
            baseMajorVersion: Number(selectedBaseMajorVersion?.name.split('.')[0])
          }
        )
      }
      onCancel={() => setCancelConfirmVisible(true)}
    />
  </>;
};