import { WizardProps } from '@cloudscape-design/components';

export const i18n = {
  wizardHeader: 'Enter Details',
  step1Title: 'Enter details',
  step1Header: 'Version details',
  step1InputDescription: 'Description',
  step1InputDescriptionPlaceholder: 'Integrated Development Environment recipe version',
  step1InputDescriptionError: 'Please enter a valid description.',
  step1InputReleaseType: 'Release type',
  step1InputReleaseTypeError: 'Please select a release type.',
  step1VolumeSize: 'Volume size (GB)',
  step1VolumeSizePlaceholder: '(8 - 500)',
  step1Integrations: 'Integrations',
  step2Title: 'Define components and order of execution',
  step2Header: 'Version components and order of execution',
  step3Title: 'Review and create',
  step3DetailsHeader: 'Version details',
  step3Step1Header: 'Step 1: Enter details',
  step3Step2Header: 'Step 2: Define components and order of execution',
  step3ComponentsHeader: 'Versions component',
  step3ButtonEdit: 'Edit',
  fetchComponentsVersionsError: 'Error fetching released component versions.',
  fetchRecipeError: 'Unable to fetch recipe details',
  step2ComponentsVersionsErrorHeader: 'No components found',
  step2ComponentsVersionsErrorContent: 'No released components found compatible with is recipe.',
  step2MainComponentError: 'No main component',
  step2MainComponentErrorDescription: 'At least 1 component version type should be marked as Main'
};
export const i18nStep2 = (isCreation: boolean) => ({
  recipeVersionInfo:
  // eslint-disable-next-line @stylistic/max-len
  `The table automatically includes mandatory components and those inherited from the ${isCreation ? 'last released' : 'current'}  recipe version. Mandatory components cannot be modified.
  Please note that these mandatory components might be defined in other projects you don't have access to.`
});

export const i18nWizard = (isUpdate: boolean) => ({
  stepNumberLabel: (stepNumber: number) =>
    `Step ${stepNumber}`,
  collapsedStepsLabel: (stepNumber: number, stepsCount: number) =>
    `Step ${stepNumber} of ${stepsCount}`,
  skipToButtonLabel: (step:WizardProps.Step) =>
    `Skip to ${step.title}`,
  navigationAriaLabel: 'Steps',
  cancelButton: 'Cancel',
  previousButton: 'Previous',
  nextButton: 'Next',
  submitButton: isUpdate ? 'Update version' : 'Create version',
  optional: 'optional'
});

export const i18nCancelConfirm = (isUpdate: boolean) => ({
  cancelPromptHeader: `Cancel recipe version ${isUpdate ? 'update' : 'creation'}`,
  cancelPromptText1: `You are about to cancel the ${isUpdate
    ? 'update' : 'creation'} of your recipe version.`,
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm'
});
