import { WizardProps } from '@cloudscape-design/components';

export const i18n = {
  wizardHeader: 'Enter Details',
  step1Title: 'Enter details',
  step1Header: 'Version details',
  step1InputDescription: 'Description',
  step1InputDescriptionPlaceholder: 'Description of the changes included in this component version',
  step1InputDescriptionError: 'Please enter a valid description.',
  step1InputSoftwareVendor: 'Software vendor',
  step1InputSoftwareVendorPlaceholder: 'Vendor that develops the software included in this component',
  step1InputSoftwareVendorError: 'Please enter a valid software vendor.',
  step1InputSoftwareVersion: 'Software version',
  step1InputSoftwareVersionPlaceholder: 'Version of the software included in this component (e.g. 1.0.0)',
  step1InputSoftwareVersionError: 'Please enter a valid software version.',
  step1InputLicenseDashboard: 'License dashboard',
  step1InputLicenseDashboardPlaceholder: 'Link to the internal license dashboard URL (if applicable)',
  step1InputLicenseDashboardError: 'Please enter a valid license dashboard URL.',
  step1InputNotes: 'Notes',
  step1InputNotesPlaceholder: 'Additional notes regarding this component version',
  step1InputReleaseType: 'Release type',
  step1InputReleaseTypeError: 'Please select a release type.',
  step2Title: 'Define YAML',
  step2Header: 'YAML definition',
  step2InputYamlDefinitionError: 'Please enter a valid YAML definition.',
  step3Title: 'Define component dependencies and order of execution',
  step3Header: 'Component dependencies and order of execution',
  step4Title: 'Review and create',
  step4Step1Header: 'Step 1: Enter details',
  step4DetailsHeader: 'Version details',
  step4Step2Header: 'Step 2: Define YAML',
  step4YamlHeader: 'YAML definition',
  step4ShowComparisonToggleLabel: 'Show comparison with another version',
  step4DiffVersionsSameAlert: 'The selected version has the same YAML definition as the current version.',
  step4DiffVersionLabel: 'Compare with version',
  step4DiffVersionPlaceholder: 'Select a released version to compare',
  step4DiffCurrentLabel: 'Current changes',
  step4Step3Header: 'Step 3: Define component dependencies and order of execution',
  step4ComponentDependenciesHeader: 'Component dependencies',
  step4ButtonEdit: 'Edit',
  fetchComponentError: 'Unable to fetch component details',
  validateVersionFailMessageHeader: 'Failed to validate version',
};

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
  cancelPromptHeader: `Cancel component version ${isUpdate ? 'update' : 'creation'}`,
  cancelPromptText1: `You are about to cancel the ${isUpdate
    ? 'update' : 'creation'} of your component version.`,
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm'
});