import { Alert, Wizard, WizardProps } from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n, i18nCancelConfirm, i18nWizard } from './mandatory-components-list-wizard.translations';
import { useMandatoryComponentsListWizard } from './mandatory-components-list-wizard.logic';
import { CancelPrompt } from '../../..';
import { MandatoryComponentsListWizardStep1 } from './mandatory-components-list-wizard-step1';
import {
  MandatoryComponentsListWizardStep2Prepended
} from './mandatory-components-list-wizard-step2-prepended';
import {
  MandatoryComponentsListWizardStep3Appended
} from './mandatory-components-list-wizard-step3-appended';
import {
  MandatoryComponentsListWizardStep4Review
} from './mandatory-components-list-wizard-step4-review';
import {
  ComponentVersionEntry,
  MandatoryComponentsList
} from '../../../../../services/API/proserve-wb-packaging-api';

interface MandatoryComponentsListWizardProps {
  projectId: string,
  mandatoryComponentsList?: MandatoryComponentsList,
  componentVersions?: ComponentVersionEntry[],
  wizardCancelAction: () => void,
  wizardSubmitAction: (
    mandatoryComponentsListPlatform: string,
    mandatoryComponentsListOsVersion: string,
    mandatoryComponentsListArchitecture: string,
    prependedComponentsVersions: ComponentVersionEntry[],
    appendedComponentsVersions: ComponentVersionEntry[],
  ) => void,
  wizardSubmitInProgress: boolean,
}

/* eslint-disable complexity */
export const MandatoryComponentsListWizard: FC<MandatoryComponentsListWizardProps> = ({
  projectId,
  mandatoryComponentsList,
  wizardCancelAction,
  wizardSubmitAction,
  wizardSubmitInProgress,
}) => {
  const {
    activeStepIndex,
    setActiveStepIndex,
    handleOnNavigate,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    mandatoryComponentsListPlatform,
    setMandatoryComponentsListPlatform,
    mandatoryComponentsListOsVersion,
    setMandatoryComponentsListOsVersion,
    mandatoryComponentsListArchitecture,
    setMandatoryComponentsListArchitecture,
    availableRecipeSupportedArchitectures,
    availableRecipeSupportedOsVersions,
    isSupportedArchitectureValid,
    isSupportedOsVersionValid,
    isPlatformValid,
    isSubmitted,
    prependedComponentVersionEntries,
    setPrependedComponentVersionEntries,
    appendedComponentVersionEntries,
    setAppendedComponentVersionEntries,
    isPrependedComponentsValid,
    isAppendedComponentsValid,
    hasDuplicateComponents,
    isUpdate,
    step1Index,
    step2Index,
    step3Index,
  } = useMandatoryComponentsListWizard({
    mandatoryComponentsList
  });

  const stepDefinitions: WizardProps.Step[] = [
    ... !isUpdate ? [{
      title: i18n.step1Title,
      content: <MandatoryComponentsListWizardStep1
        mandatoryComponentsListPlatform={mandatoryComponentsListPlatform}
        setMandatoryComponentsListPlatform={setMandatoryComponentsListPlatform}
        mandatoryComponentsListOsVersion={mandatoryComponentsListOsVersion!}
        setMandatoryComponentsListOsVersion={setMandatoryComponentsListOsVersion}
        mandatoryComponentsListArchitecture={mandatoryComponentsListArchitecture!}
        setMandatoryComponentsListArchitecture={setMandatoryComponentsListArchitecture}
        availableMandatoryComponentSupportedArchitectures={availableRecipeSupportedArchitectures}
        availableMandatoryComponentSupportedOsVersions={availableRecipeSupportedOsVersions}
        isSupportedArchitectureValid={isSupportedArchitectureValid}
        isSupportedOsVersionValid={isSupportedOsVersionValid}
        isPlatformValid={isPlatformValid}
        isSubmitted={isSubmitted}
        isUpdate={isUpdate} />
    }] : [],
    {
      title: i18n.step2Title,
      content: <MandatoryComponentsListWizardStep2Prepended
        projectId={projectId}
        mandatoryComponentsListPlatform={mandatoryComponentsListPlatform}
        mandatoryComponentsListOsVersion={mandatoryComponentsListOsVersion?.value || ''}
        mandatoryComponentsListArchitecture={mandatoryComponentsListArchitecture?.value || ''}
        prependedComponentVersionEntries={prependedComponentVersionEntries}
        setPrependedComponentVersionEntries={setPrependedComponentVersionEntries}
        isPrependedComponentsValid={isPrependedComponentsValid}
        hasDuplicateComponents={hasDuplicateComponents} />
    },
    {
      title: i18n.step3Title,
      content: <MandatoryComponentsListWizardStep3Appended
        projectId={projectId}
        mandatoryComponentsListPlatform={mandatoryComponentsListPlatform}
        mandatoryComponentsListOsVersion={mandatoryComponentsListOsVersion?.value || ''}
        mandatoryComponentsListArchitecture={mandatoryComponentsListArchitecture?.value || ''}
        appendedComponentVersionEntries={appendedComponentVersionEntries}
        setAppendedComponentVersionEntries={setAppendedComponentVersionEntries}
        isAppendedComponentsValid={isAppendedComponentsValid}
        hasDuplicateComponents={hasDuplicateComponents} />
    },
    {
      title: i18n.step4Title,
      content: <MandatoryComponentsListWizardStep4Review
        mandatoryComponentsListPlatform={mandatoryComponentsListPlatform}
        mandatoryComponentsListOsVersion={mandatoryComponentsListOsVersion?.value || ''}
        mandatoryComponentsListArchitecture={mandatoryComponentsListArchitecture?.value || ''}
        prependedComponentVersionEntries={prependedComponentVersionEntries}
        appendedComponentVersionEntries={appendedComponentVersionEntries}
        isUpdate={isUpdate}
        step1Index={step1Index}
        step2Index={step2Index}
        step3Index={step3Index}
        setActiveStepIndex={setActiveStepIndex} />
    },
  ];

  return <>
    <CancelPrompt
      cancelConfirmVisible={cancelConfirmVisible}
      setCancelConfirmVisible={setCancelConfirmVisible}
      handleCancelConfirm={wizardCancelAction}
      i18nStrings={i18nCancelConfirm(isUpdate)}
    />
    <Alert type="info">{i18n.mandatoryComponentListsAlert}</Alert>
    <Wizard
      steps={stepDefinitions}
      i18nStrings={i18nWizard(isUpdate)}
      activeStepIndex={activeStepIndex}
      onNavigate={({ detail }) => handleOnNavigate(detail)}
      isLoadingNextStep={wizardSubmitInProgress}
      onSubmit={() => wizardSubmitAction(
        mandatoryComponentsListPlatform,
        mandatoryComponentsListOsVersion?.value || '',
        mandatoryComponentsListArchitecture?.value || '',
        prependedComponentVersionEntries,
        appendedComponentVersionEntries
      )}
      onCancel={() => setCancelConfirmVisible(true)}
    />
  </>;
};