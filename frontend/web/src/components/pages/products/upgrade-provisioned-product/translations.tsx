import { i18nProvisionWorkbench } from '..';

const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

export const i18nWorkbenchUpgrade = {
  ...i18nProvisionWorkbench,
  cancelButton: 'Cancel',
  previousButton: 'Previous',
  nextButton: 'Next',
  submitButton: 'Upgrade',
  titleStep1: 'Configure settings',
  titleStep2: 'Set parameters',
  titleStep3: 'Review and upgrade',
  breadcrumbL1: 'Workbenches: My workbenches',
  breadcrumbL2: 'Upgrade workbench',
  helpTitle: 'Upgrade workbench',
  helpDescription: 'Here you can enter all the required parameters to upgrade the selected workbench.',
  stepNumberLabel: (stepNumber: number) => `Step ${stepNumber}`,
  collapsedStepsLabel: (stepNumber: number, stepsCount: number) =>`Step ${stepNumber} of ${stepsCount}`,
  cancelPromptHeader: 'Cancel workbench upgrade',
  cancelPromptText1: 'You are about to cancel the upgrade of your workbench.',
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm',
  warningHeader: 'Warning!',
  warningContent: 'Upgrade will recreate the workbench and the workbench storage data will be lost.',
};

export const i18nVirtualTargetUpgrade = {
  ...i18nProvisionWorkbench,
  cancelButton: 'Cancel',
  previousButton: 'Previous',
  nextButton: 'Next',
  submitButton: 'Upgrade',
  titleStep1: 'Configure settings',
  titleStep2: 'Set parameters',
  titleStep3: 'Review and upgrade',
  breadcrumbL1: 'Virtual targets: My virtual targets: My workbenches',
  breadcrumbL2: 'Upgrade virtual target',
  helpTitle: 'Upgrade virtual targer',
  helpDescription: 'Here you can enter all the required parameters to upgrade the selected virtual target.',
  stepNumberLabel: (stepNumber: number) => `Step ${stepNumber}`,
  collapsedStepsLabel: (stepNumber: number, stepsCount: number) =>`Step ${stepNumber} of ${stepsCount}`,
  cancelPromptHeader: 'Cancel virtual target upgrade',
  cancelPromptText1: 'You are about to cancel the upgrade of your virtual target.',
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm',
  warningHeader: 'Warning!',
  warningContent:
    'Upgrade will recreate the virtual target and the virtual target storage data will be lost.',
};


export const i18nContainerUpgrade = {
  ...i18nProvisionWorkbench,
  cancelButton: 'Cancel',
  previousButton: 'Previous',
  nextButton: 'Next',
  submitButton: 'Upgrade',
  titleStep1: 'Configure settings',
  titleStep2: 'Set parameters',
  titleStep3: 'Review and upgrade',
  breadcrumbL1: 'Containers: My containers: My containers',
  breadcrumbL2: 'Upgrade container',
  helpTitle: 'Upgrade container',
  helpDescription: 'Here you can enter all the required parameters to upgrade the selected container.',
  stepNumberLabel: (stepNumber: number) => `Step ${stepNumber}`,
  collapsedStepsLabel: (stepNumber: number, stepsCount: number) =>`Step ${stepNumber} of ${stepsCount}`,
  cancelPromptHeader: 'Cancel container upgrade',
  cancelPromptText1: 'You are about to cancel the upgrade of your container.',
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm',
  warningHeader: 'Warning!',
  warningContent:
    'Upgrade will recreate the container and the container storage data will be lost.',
};

export const i18nWorkbenchSteps = {
  settingsContainerHeader: 'Workbench settings',
  dropdownVersionNotSelected: 'Choose a version',
  formFieldRegionHeader: 'Region',
  formFieldRegionDescription:
        'Location where the workbench will be hosted. Default option based on user profile preferences.',
  formFieldStageHeader: 'Stage',
  formFieldStageDescription: 'Stage at which the workbench is available from DEV, QA and PROD.',
  formFieldVersionHeader: 'Version',
  formFieldVersionDescription:
        'Available versions of the product. Only the product versions fulfilling your region and stage requirements are shown.', // eslint-disable-line
  formFieldVersionError: 'Please select an available workbench version.',
  productVersionsLoading: 'Loading versions...',
  recommendedVersionTag: 'Recommended',

  parametersContainerHeader: 'Workbench parameters',
  productAdvancedDetails: `Maintenance window [Time zone: ${userTimeZone}]`,
  productAdvancedDescription: 'Period of time during which patches and security updates will be applied.',
  parameterNew: 'New',
  parameterInfo: 'Info',

  stepOne: 'Step 1: Configure settings',
  stepTwo: 'Step 2: Set parameters',
  region: 'Region',
  stage: 'Stage',
  version: 'Version',
  mainSoftware: 'Main software',
  instanceType: 'Instance type',
  editButton: 'Edit'
};

export const i18nVirtualTargetSteps = {
  settingsContainerHeader: 'Virtual target settings',
  dropdownVersionNotSelected: 'Choose a version',
  formFieldRegionHeader: 'Region',
  formFieldRegionDescription:
        'Location where the virtual target will be hosted. Default option based on user profile preferences.',
  formFieldStageHeader: 'Stage',
  formFieldStageDescription: 'Stage at which the virtual target is available from DEV, QA and PROD.',
  formFieldVersionHeader: 'Version',
  formFieldVersionDescription:
        'Available versions of the product. Only the product versions fulfilling your region and stage requirements are shown.', // eslint-disable-line
  formFieldVersionError: 'Please select an available virtual target version.',
  productVersionsLoading: 'Loading versions...',
  recommendedVersionTag: 'Recommended',

  parametersContainerHeader: 'Virtual target parameters',
  productAdvancedDetails: `Maintenance window [Time zone: ${userTimeZone}]`,
  productAdvancedDescription: 'Period of time during which patches and security updates will be applied.',
  parameterNew: 'New',
  parameterInfo: 'Info',

  stepOne: 'Step 1: Configure settings',
  stepTwo: 'Step 2: Set parameters',
  region: 'Region',
  stage: 'Stage',
  version: 'Version',
  mainSoftware: 'Main software',
  instanceType: 'Instance type',
  editButton: 'Edit'
};

export const i18nContainerSteps = {
  settingsContainerHeader: 'Container settings',
  dropdownVersionNotSelected: 'Choose a version',
  formFieldRegionHeader: 'Region',
  formFieldRegionDescription:
        'Location where the container will be hosted. Default option based on user profile preferences.',
  formFieldStageHeader: 'Stage',
  formFieldStageDescription: 'Stage at which the container is available from DEV, QA and PROD.',
  formFieldVersionHeader: 'Version',
  formFieldVersionDescription:
        'Available versions of the product. Only the product versions fulfilling your region and stage requirements are shown.', // eslint-disable-line
  formFieldVersionError: 'Please select an available container version.',
  productVersionsLoading: 'Loading versions...',
  recommendedVersionTag: 'Recommended',

  parametersContainerHeader: 'Container parameters',
  productAdvancedDetails: `Maintenance window [Time zone: ${userTimeZone}]`,
  productAdvancedDescription: 'Period of time during which patches and security updates will be applied.',
  parameterNew: 'New',
  parameterInfo: 'Info',

  stepOne: 'Step 1: Configure settings',
  stepTwo: 'Step 2: Set parameters',
  region: 'Region',
  stage: 'Stage',
  version: 'Version',
  mainSoftware: 'Main software',
  instanceType: 'Instance type',
  editButton: 'Edit'
};
