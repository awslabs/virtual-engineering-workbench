import { WizardProps } from '@cloudscape-design/components';

export const i18n = {
  wizardHeader: 'Enter Details',
  step1Title: 'Enter details',
  step1Header: 'Mandatory component details',
  step2Title: 'Select prepended components',
  step2Header: 'Prepended components',
  step2Description: 'These components will be added at the beginning of recipe versions, ' +
    'before any user-selected components.',
  step3Title: 'Select appended components',
  step3Header: 'Appended components',
  step3Description: 'These components will be added at the end of recipe versions, ' +
    'after all user-selected components.',
  step4Title: 'Review and create',
  step4DetailsHeader: 'Mandatory component details',
  step4Step1Header: 'Enter details',
  step4Step2Header: 'Prepended components',
  step4Step3Header: 'Appended components',
  step4ComponentsHeader: 'Versions component',
  step4ButtonEdit: 'Edit',
  step3ButtonEdit: 'Edit',
  fetchComponentsVersionsError: 'Error fetching released component versions.',
  fetchRecipeError: 'Unable to fetch recipe details',
  step2ComponentsVersionsErrorHeader: 'No components found',
  step2ComponentsVersionsErrorContent: 'No released components found compatible with is recipe.',
  step2MainComponentError: 'No main component',
  step2MainComponentErrorDescription: 'At least 1 component version type should be marked as Main',
  duplicateComponentError: 'Duplicate components detected',
  duplicateComponentErrorDescription: 'A component cannot be in both prepended and appended lists. ' +
    'Please remove the duplicate.',
  noComponentsError: 'No components specified',
  noComponentsErrorDescription: 'At least one component must be specified as either prepended or appended.',
  platformLabel: 'Platform',
  platformWindowsLabel: 'Windows',
  platformWindowsDescription: 'Select this option if list will be used for Windows based images.',
  platformLinuxLabel: 'Linux',
  platformLinuxDescription: 'Select this option if list will be used for Linux based images.',
  supportedOsVersionLabel: 'Supported OS version',
  supportedOsVersionPlaceholder: 'Choose supported OS version',
  supportedOsVersionValidationMessage: 'Choose supported OS version',
  supportedArchitectureLabel: 'Supported architecture',
  supportedArchitecturePlaceholder: 'Choose supported architecture',
  supportedArchitectureValidationMessage: 'Choose supported architecture',
  platformValidationMessage: 'Choose platform',
  mandatoryComponentListsAlert: 'Please note that mandatory component lists are shared between programs. ' +
    'Make sure to only edit them in the program where their components are defined.',

};

export const i18nWizard = (isUpdate: boolean) => ({
  stepNumberLabel: (stepNumber: number) =>
    `Step ${stepNumber}`,
  collapsedStepsLabel: (stepNumber: number, stepsCount: number) =>
    `Step ${stepNumber} of ${stepsCount}`,
  skipToButtonLabel: (step: WizardProps.Step) =>
    `Skip to ${step.title}`,
  navigationAriaLabel: 'Steps',
  cancelButton: 'Cancel',
  previousButton: 'Previous',
  nextButton: 'Next',
  submitButton: isUpdate ? 'Update' : 'Create',
  optional: 'optional'
});

export const i18nCancelConfirm = (isUpdate: boolean) => ({
  cancelPromptHeader: `Cancel mandatory component ${isUpdate ? 'update' : 'creation'}`,
  cancelPromptText1: `You are about to cancel the ${isUpdate ?
    'update' : 'creation'} of your mandatory component.`,
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm'
});