/* eslint-disable @stylistic/max-len */
import { WizardProps } from '@cloudscape-design/components';

export const i18n = {
  wizardHeader: 'Enter Details',
  step1Title: 'Enter details',
  step1Header: 'Version details',
  step1InputDescription: 'Description',
  step1InputReleaseType: 'Release type',
  step1InputReleaseTypeError: 'Please select a release type.',
  step1InputAmiIdError: 'Please select AMI ID.',
  step1BaseMajorVersionLabel: 'Base major version',
  step1BaseMajorVersionLabelDescription1: 'Chose a major version as the base for the new minor/patch version.',
  step1BaseMajorVersionLabelDescription2: 'Only major versions that have at least one active version are available for selection.',
  step1BaseMajorVersionSelectPlaceholder: 'Choose version',
  step1BaseMajorVersionSelectEmptyPlaceholder: 'No versions available',
  step2Title: 'Define YAML',
  step2Header: 'YAML definition',
  step2InputYamlDefinitionError: 'Please enter a valid YAML definition.',
  step3Title: 'Review and create',
  step3Step1Header: 'Step 1: Enter details',
  step3DetailsHeader: 'Version details',
  step3Step2Header: 'Step 2: Define YAML',
  step3YamlHeader: 'YAML definition',
  step3ShowComparisonToggleLabel: 'Show comparison with another version',
  step3DiffVersionsSameAlert: 'The selected version has the same YAML definition as the current version.',
  step3DiffVersionLabel: 'Compare with version',
  step3DiffVersionPlaceholder: 'Select a released version to compare',
  step3ButtonEdit: 'Edit',
  fetchAmisError: 'Unable to fetch AMIs',
  fetchProductError: 'Unable to fetch product',
  fetchTemplateError: 'Unable to fetch templates',
  fetchLatestMajorVersionsError: 'Unable to fetch base major versions',
  validateVersionFailMessageHeader: 'Failed to validate version',
  productDescLabel: 'Description',
  productVersionDescriptionValidationMessage: 'Product version description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_), hyphen(-)',
  productDescPlaceholder: 'Enter product description',
  amiIdLabel: 'AMI ID',
  amiIdPlaceholder: 'Select AMI ID',
  emptyAmiIdPlaceholder: 'No AMI IDs available',
  releaseTypeHeader: 'Release type',
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
  cancelPromptHeader: `Cancel product version ${isUpdate ? 'update' : 'creation'}`,
  cancelPromptText1: `You are about to cancel the ${isUpdate
    ? 'update' : 'creation'} of your product version.`,
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm'
});
