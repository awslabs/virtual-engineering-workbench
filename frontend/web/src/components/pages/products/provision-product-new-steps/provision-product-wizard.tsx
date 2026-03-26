import { Wizard, WizardProps } from '@cloudscape-design/components';
import { FC, useState } from 'react';
import {
  CancelPrompt,
  ConfigureSettingsStep,
  ProductVersionMetadata,
  ReviewAndCreateStep,
  SetParametersStep,
  Step1Version,
  Step3SelectedVersion,
} from '.';
import { ConsentForm } from './consent-form';
import { ProductParameter } from '../../../../services/API/proserve-wb-provisioning-api';
import { ProductParameterState } from '../../../../hooks/provisioning';
import { StepsTranslations } from '../../../../hooks/provisioning/provision-product.logic';

interface Translations {
  titleStep1: string,
  titleStep2: string,
  titleStep3: string,
  stepNumberLabel: (stepNumber: number) => string,
  collapsedStepsLabel: (stepNumber: number, stepsCount: number) => string,
  cancelButton: string,
  previousButton: string,
  nextButton: string,
  submitButton: string,
  cancelPromptHeader: string,
  cancelPromptText1: string,
  cancelPromptText2: string,
  cancelPromptText3: string,
  cancelPromptCancelText: string,
  cancelPromptConfirmText: string,
  consentFormHeader: string,
  consentFormDescription: string[],
  consentFormUsePoliciesHeader: string,
  consentFormUsePolicies: string[],
  consentFormResponsibilitiesHeader: string,
  consentFormResponsibilities1: string[],
  consentFormResponsibilities2: string[],
  consentFormRisksHeader: string,
  consentFormRisks1: string[],
  consentFormRisks2: string[],
  consentFormRisks3: string[],
  consentFormAcknowledgement: string[],
  consentFormCheckboxLabel: string,
}

interface Step1Params {
  selectedVersionRegion: string,
  setSelectedVersionRegion?: (region: string) => void,
  selectedVersionStage: string,
  setSelectedVersionStage?: (stage: string) => void,
  selectedVersion?: Step1Version,
  setSelectedVersion?: (version?: Step1Version) => void,
  availableRegions: string[],
  availableStages: string[],
  productVersions: Step1Version[],
  productVersionsLoading: boolean,
  disabled?: boolean,
  productVersionMetadata?: ProductVersionMetadata,
  i18nSteps: StepsTranslations,
  vvJobName?: string,
  vvPlatform?: string,
  vvVersion?: string,
  vvArtifactUpstreamPath?: string,
  productType?: string,
}

interface Step2Params {
  productParametersLoading?: boolean,
  productParameters: ProductParameter[],
  productParameterState: ProductParameterState,
  previouslyEnteredParameterNames?: Set<string>,
  showInfoForNewParameterNames?: boolean,
  handleProductParameterChange: (key: string, value?: string) => void,
  parameterInfoClicked?: () => void,
  i18nSteps: StepsTranslations,
  vvJobName?: string,
  vvPlatform?: string,
  vvVersion?: string,
  vvArtifactUpstreamPath?: string,
  isExperimentalWorkbench?: boolean,
  setIsExperimentalWorkbench?: (value: boolean) => void,
  isExperimentalWorkbenchAvailable?: boolean,
}

interface Step3Params {
  selectedVersionRegion: string,
  selectedVersionStage: string,
  selectedVersion?: Step3SelectedVersion,
  productParameterState: ProductParameterState,
  productParameters: ProductParameter[],
  additionalInfo?: JSX.Element,
  i18nSteps: StepsTranslations,
  vvJobName?: string,
  vvPlatform?: string,
  vvVersion?: string,
  vvArtifactUpstreamPath?: string,
  isExperimentalWorkbench?: boolean,
  isExperimentalWorkbenchAvailable?: boolean,
}

interface Params {
  wizardSubmitInProgress: boolean,
  wizardSubmitAction: () => Promise<void>,
  wizardCancelAction: () => void,
  activeStepChanged?: (step: number) => void,
  step1Params: Step1Params,
  step2Params: Step2Params,
  step3Params: Step3Params,
  i18nStrings: Translations,
  hideMaintenanceWindow?: boolean,
  activeStepIndex: number,
  setActiveStepIndex: (string: number) => any,
}

const STEP_1_CONFIGURE_SETTINGS_INDEX = 1;

export const ProvisionProductWizard: FC<Params> = ({
  wizardSubmitInProgress,
  wizardSubmitAction,
  wizardCancelAction,
  activeStepChanged,
  step1Params,
  step2Params,
  step3Params,
  i18nStrings,
  activeStepIndex,
  setActiveStepIndex
}) => {

  const [showStep1ValidationErrors, setShowStep1ValidationErrors] = useState(false);
  const [cancelConfirmVisible, setCancelConfirmVisible] = useState(false);
  const [showConsentForm, setShowConsentForm] = useState(false);

  const handleSubmit = () => {
    if (step3Params.isExperimentalWorkbench) {
      setShowConsentForm(true);
    } else {
      wizardSubmitAction();
    }
  };

  const handleConsentFormConfirm = () => {
    setShowConsentForm(false);
    wizardSubmitAction();
  };

  return <>
    <CancelPrompt
      cancelConfirmVisible={cancelConfirmVisible}
      setCancelConfirmVisible={setCancelConfirmVisible}
      handleCancelConfirm={wizardCancelAction}
      i18nStrings={i18nStrings}
    />
    {showConsentForm &&
      <ConsentForm
        cancelConfirmVisible={showConsentForm}
        setCancelConfirmVisible={setShowConsentForm}
        handleCancelConfirm={handleConsentFormConfirm}
        i18nStrings={i18nStrings}
      />
    }
    <Wizard
      i18nStrings={i18nStrings}
      onNavigate={({ detail }) => handleOnNavigateClick(detail)}
      onSubmit={handleSubmit}
      onCancel={() => handleCancelAction()}
      activeStepIndex={activeStepIndex}
      allowSkipTo
      isLoadingNextStep={isLoading()}
      steps={[
        {
          title: i18nStrings.titleStep1,
          content: <ConfigureSettingsStep {...step1Params}
            selectedVersionValid={isSelectedVersionValid()}
            showValidationErrors={showStep1ValidationErrors} />
        },
        {
          title: i18nStrings.titleStep2,
          content: <SetParametersStep {...step2Params} />
        },
        {
          title: i18nStrings.titleStep3,
          content: <ReviewAndCreateStep {...step3Params} />
        }
      ]}
    />
  </>;

  function handleCancelAction() {
    setCancelConfirmVisible(true);
  }

  function handleOnNavigateClick(detail: WizardProps.NavigateDetail) {
    if (requiresValidation(detail.reason) && !isStepDataValid(detail.requestedStepIndex)) {
      return;
    }
    setActiveStepIndex(detail.requestedStepIndex);
    activeStepChanged?.(detail.requestedStepIndex);
  }

  function isStepDataValid(requestedStepIndex: number) {
    if (requestedStepIndex === STEP_1_CONFIGURE_SETTINGS_INDEX) {
      return isStep1DataValid();
    }
    return true;
  }

  function isStep1DataValid() {
    setShowStep1ValidationErrors(true);
    return isSelectedVersionValid();
  }

  function isSelectedVersionValid() {
    return step1Params.selectedVersion !== undefined;
  }

  function requiresValidation(reason: string) {
    return reason === 'next';
  }

  function isLoading() {
    return step1Params.productVersionsLoading ||
    wizardSubmitInProgress;
  }
};