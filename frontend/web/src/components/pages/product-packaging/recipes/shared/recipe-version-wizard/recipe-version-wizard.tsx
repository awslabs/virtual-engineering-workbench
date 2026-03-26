/* eslint-disable complexity */
import { Wizard, WizardProps } from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n, i18nCancelConfirm, i18nWizard } from './recipe-version-wizard.translations';
import {
  RecipeVersionWizardStep1,
  RecipeVersionWizardStep2,
  RecipeVersionWizardStep3
} from '.';
import {
  RecipeComponentVersion,
  RecipeVersion
} from '../../../../../../services/API/proserve-wb-packaging-api';
import { useRecipeVersionWizard } from './recipe-version-wizard.logic';
import { packagingAPI } from '../../../../../../services';
import { CancelPrompt } from '../../../..';

interface RecipeVersionWizardProps {
  projectId: string,
  recipeId: string,
  recipeVersion?: RecipeVersion,
  wizardCancelAction: () => void,
  wizardSubmitAction: (
    description: string,
    recipeComponentsVersions: RecipeComponentVersion[],
    volumeSize: string,
    versionReleaseType?: string,
    integrations?: string[],
  ) => void,
  wizardSubmitInProgress: boolean,
  activeStepIndex: number,
  setActiveStepIndex: (step: number) => void,
  recipeVersionMandatories?: RecipeVersion,
}

export const RecipeVersionWizard: FC<RecipeVersionWizardProps> = ({
  projectId,
  recipeId,
  recipeVersion,
  wizardCancelAction,
  wizardSubmitAction,
  wizardSubmitInProgress,
  activeStepIndex,
  setActiveStepIndex,
  recipeVersionMandatories,
}) => {
  const {
    recipe,
    isRecipeLoading,
    isUpdate,
    description,
    setDescription,
    volumeSize,
    setVolumeSize,
    isVolumeSizeValid,
    isDescriptionValid,
    versionReleaseTypes,
    versionReleaseType,
    setVersionReleaseType,
    isVersionReleaseTypeValid,
    recipeComponentsVersions,
    isRecipeComponentsVersionsValid,
    handleOnNavigate,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    minRecipeComponentsVersions,
    minVolumeSize,
    maxVolumeSize,
    updateRecipeComponentsVersions,
    integrations,
    isIntegrationsLoading,
    selectedIntegrations,
    setSelectedIntegrations,
    integrationComponents,
    isLoadingIntegrationComponents,
  } = useRecipeVersionWizard({
    projectId,
    recipeId,
    recipeVersion,
    serviceApi: { ...packagingAPI },
    activeStepIndex,
    setActiveStepIndex
  });




  const stepDefinitions: WizardProps.Step[] = [
    {
      title: i18n.step1Title,
      content: <RecipeVersionWizardStep1
        isUpdate={isUpdate}
        description={description}
        setDescription={setDescription}
        isDescriptionValid={isDescriptionValid}
        volumeSize={volumeSize}
        setVolumeSize={setVolumeSize}
        isVolumeSizeValid={isVolumeSizeValid}
        minVolumeSize={minVolumeSize}
        maxVolumeSize={maxVolumeSize}
        versionReleaseTypes={versionReleaseTypes}
        versionReleaseType={versionReleaseType}
        setVersionReleaseType={setVersionReleaseType}
        isVersionReleaseTypeValid={isVersionReleaseTypeValid}
        availableIntegrations={integrations}
        isIntegrationsLoading={isIntegrationsLoading}
        selectedIntegrations={selectedIntegrations}
        setSelectedIntegrations={setSelectedIntegrations}
      />
    },
    {
      title: i18n.step2Title,
      content: <RecipeVersionWizardStep2
        projectId={projectId}
        recipe={recipe}
        recipeComponentsVersions={recipeComponentsVersions}
        setRecipeComponentsVersions={updateRecipeComponentsVersions}
        isRecipeComponentsVersionsValid={isRecipeComponentsVersionsValid}
        minRecipeComponentsVersions={minRecipeComponentsVersions}
        recipeMandatoriesComponentsVersions={recipeVersionMandatories?.recipeComponentsVersions || []}
        integrationComponentsVersions={integrationComponents}
      />
    },
    {
      title: i18n.step3Title,
      content: <RecipeVersionWizardStep3
        setActiveStepIndex={setActiveStepIndex}
        description={description}
        versionReleaseType={versionReleaseType}
        recipeComponentsVersions={recipeComponentsVersions}
        volumeSize={volumeSize}
        recipeMandatoriesComponentsVersions={recipeVersionMandatories?.recipeComponentsVersions || []}
        integrationComponentsVersions={integrationComponents}
        selectedIntegrations={selectedIntegrations}
        availableIntegrations={integrations}
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
      isLoadingNextStep={isRecipeLoading || wizardSubmitInProgress || isLoadingIntegrationComponents}
      onSubmit={() =>
        wizardSubmitAction(
          description,
          recipeComponentsVersions,
          volumeSize.toString(),
          versionReleaseType,
          selectedIntegrations,
        )
      }
      onCancel={() => setCancelConfirmVisible(true)}
    />
  </>;
};
