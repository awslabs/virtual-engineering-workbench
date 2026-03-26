import { Wizard, WizardProps } from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n, i18nCancelConfirm, i18nWizard } from './component-version-wizard.translations';
import {
  ComponentVersionWizardStep1,
  ComponentVersionWizardStep2,
  ComponentVersionWizardStep3
} from '.';
import {
  ComponentVersion,
  ComponentVersionEntry,
} from '../../../../../../services/API/proserve-wb-packaging-api';
import { useComponentVersionWizard } from './component-version-wizard.logic';
import { CancelPrompt } from '../../../..';
import { packagingAPI } from '../../../../../../services';
import { ComponentVersionWizardStep4 } from './component-version-wizard-step4';
interface ComponentVersionWizardProps {
  projectId: string,
  componentId: string,
  componentVersion?: ComponentVersion,
  componentVersionYamlDefinition?: string,
  originalYamlDefinition?: string,
  releasedVersions?: ComponentVersion[],
  fetchVersionYaml?: (versionId: string) => Promise<string>,
  componentVersionDependenciesList?: ComponentVersionEntry[],
  wizardCancelAction: () => void,
  wizardSubmitAction: ({
    description,
    softwareVendor,
    softwareVersion,
    licenseDashboard,
    notes,
    versionReleaseType,
    yamlDefinition,
    componentVersionDependencies,
  }:{
    description: string,
    softwareVendor: string,
    softwareVersion: string,
    licenseDashboard: string,
    notes: string,
    versionReleaseType: string,
    yamlDefinition: string,
    componentVersionDependencies: ComponentVersionEntry[],
  }) => void,
  wizardSubmitInProgress: boolean,
  activeStepIndex: number,
  setActiveStepIndex: (step: number) => void,
}

// eslint-disable-next-line complexity
export const ComponentVersionWizard: FC<ComponentVersionWizardProps> = ({
  projectId,
  componentId,
  componentVersion,
  componentVersionYamlDefinition,
  originalYamlDefinition,
  releasedVersions,
  fetchVersionYaml,
  componentVersionDependenciesList,
  wizardCancelAction,
  wizardSubmitAction,
  wizardSubmitInProgress,
  activeStepIndex,
  setActiveStepIndex
}) => {
  const {
    component,
    isComponentLoading,
    isUpdate,
    description,
    setDescription,
    isDescriptionValid,
    versionReleaseTypes,
    versionReleaseType,
    setVersionReleaseType,
    isVersionReleaseTypeValid,
    handleOnNavigate,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    softwareVendor,
    setSoftwareVendor,
    isSoftwareVendorValid,
    softwareVersion,
    setSoftwareVersion,
    isSoftwareVersionValid,
    licenseDashboard,
    setLicenseDashboard,
    isLicenseDashboardValid,
    notes,
    setNotes,
    yamlDefinition,
    setYamlDefinition,
    isYamlDefinitionValidationInProgress,
    isYamlDefinitionValid,
    setIsYamlDefinitionValid,
    componentVersionDependencies,
    setComponentVersionDependencies,
    isComponentVersionDependenciesValid,
    minComponentVersionDependencies
  } = useComponentVersionWizard({
    projectId,
    componentId,
    serviceApi: packagingAPI,
    componentVersion: componentVersion || {} as ComponentVersion,
    componentVersionYamlDefinition: componentVersionYamlDefinition || '',
    componentVersionDependenciesList: componentVersionDependenciesList || [],
    activeStepIndex,
    setActiveStepIndex
  });

  const stepDefinitions: WizardProps.Step[] = [
    {
      title: i18n.step1Title,
      content: <ComponentVersionWizardStep1
        isUpdate={isUpdate}
        description={description}
        setDescription={setDescription}
        isDescriptionValid={isDescriptionValid}
        versionReleaseTypes={versionReleaseTypes}
        versionReleaseType={versionReleaseType}
        setVersionReleaseType={setVersionReleaseType}
        isVersionReleaseTypeValid={isVersionReleaseTypeValid}
        softwareVendor={softwareVendor}
        setSoftwareVendor={setSoftwareVendor}
        isSoftwareVendorValid={isSoftwareVendorValid}
        softwareVersion={softwareVersion}
        setSoftwareVersion={setSoftwareVersion}
        isSoftwareVersionValid={isSoftwareVersionValid}
        licenseDashboard={licenseDashboard}
        setLicenseDashboard={setLicenseDashboard}
        isLicenseDashboardValid={isLicenseDashboardValid}
        notes={notes}
        setNotes={setNotes}
      />
    },
    {
      title: i18n.step2Title,
      content: <ComponentVersionWizardStep2
        projectId={projectId}
        componentId={componentId}
        yamlDefinition={yamlDefinition}
        setYamlDefinition={setYamlDefinition}
        isYamlDefinitionValid={isYamlDefinitionValid}
        setIsYamlDefinitionValid={setIsYamlDefinitionValid}
      />
    },
    {
      title: i18n.step3Title,
      content: <ComponentVersionWizardStep3
        projectId={projectId}
        component={component}
        componentVersionDependencies={componentVersionDependencies}
        setComponentVersionDependencies={setComponentVersionDependencies}
        isComponentVersionDependenciesValid={isComponentVersionDependenciesValid}
        minComponentVersionDependencies={minComponentVersionDependencies}
        recipeMandatoriesComponentsVersions={[]} />
    },
    {
      title: i18n.step4Title,
      content: <ComponentVersionWizardStep4
        setActiveStepIndex={setActiveStepIndex}
        description={description}
        softwareVendor={softwareVendor}
        softwareVersion={softwareVersion}
        licenseDashboard={licenseDashboard}
        notes={notes}
        yamlDefinition={yamlDefinition}
        originalYamlDefinition={
          originalYamlDefinition ?? (isUpdate ? componentVersionYamlDefinition : undefined)
        }
        releasedVersions={releasedVersions}
        fetchVersionYaml={fetchVersionYaml}
        versionReleaseType={versionReleaseType}
        componentVersionDependencies={componentVersionDependencies}
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
      isLoadingNextStep={isComponentLoading || isYamlDefinitionValidationInProgress || wizardSubmitInProgress}
      onSubmit={() => wizardSubmitAction(
        {
          description: description.trim(),
          softwareVendor: softwareVendor.trim(),
          softwareVersion: softwareVersion.trim(),
          licenseDashboard: licenseDashboard.trim(),
          notes: notes.trim(),
          versionReleaseType: versionReleaseType.trim(),
          yamlDefinition: yamlDefinition.trim(),
          componentVersionDependencies,
        }
      )}
      onCancel={() => setCancelConfirmVisible(true)}
    />
  </>;
};