export const i18nProvisionVirtualTarget = {
  cancelButton: 'Cancel',
  previousButton: 'Previous',
  nextButton: 'Next',
  submitButton: 'Launch instance',
  titleStep1: 'Configure settings',
  titleStep2: 'Set parameters',
  titleStep3: 'Review and create',
  breadcrumbL1: 'Virtual targets: All virtual targets',
  breadcrumbL2: 'Create virtual target',
  helpTitle: 'Create a product instance',
  helpDescription: 'Here you can enter all the required parameters to create the selected product.',
  stepNumberLabel: (stepNumber: number) => `Step ${stepNumber}`,
  collapsedStepsLabel: (stepNumber: number, stepsCount: number) =>`Step ${stepNumber} of ${stepsCount}`,
  cancelPromptHeader: 'Cancel virtual target creation',
  cancelPromptText1: 'You are about to cancel the creation of your virtual target.',
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm',
  productProvisionErrorTitle: 'Virtual target creation failed',
  productProvisionErrorText: 'You can find more details in the Virtual targets screen',
  productProvisionSuccessTitle: 'Virtual target creation started',
  productProvisionSuccessText: 'Virtual target creation may take a few minutes to complete.',
  productVersionsFetchErrorTitle: 'Unable to fetch the virtual targets versions',
  productParametersFetchErrorTitle: 'Unable to fetch the virtual target parameters',
  productProvisionError: 'Unable to create virtual target',
  productType: 'VIRTUAL_TARGET',

  step1InfoPanelHeader: 'Configure settings',
  step1InfoPanelLabel: 'How do I fill this information in?',
  step1InfoPanelMessage1: `Select the region that you would like the virtual target to be hosted
   from. It is advised you select a region close to your place of work as this will reduce latency. `,
  step1InfoPanelMessage2: `Select whether you want this virtual target to be provisioned in DEV
  or QA environment.`,
  step1InfoPanelMessage3: `Select the appropriate version. After selection you will be able to
  see additional information such as the installed tools, main software versions, VVRP user guide,
  and release notes associated
  to the version.`,
  step2InfoPanelHeader: 'Set parameters',
  step2InfoPanelLabel: 'How do I fill this information in?',
  step2InfoPanelMessage1: `Amazon EC2 Instances are defined in various types of size, performance, and
  capabilities. Choose the instance type that will best suit you.`,
  step2InfoPanelMessage2: '',
  step3InfoPanelHeader: 'Review and create',
  step3InfoPanelMessage1: `Review the entered information before creating your virtual target.
  This allows you to ensure that everything is correct. Some of the entered information may not
  be able to be edited after creation.`,
  step1InfoPanelMessageExperimentalInstance: '',

  consentFormHeader: 'Consent Form for Experimental Mode feature',
  consentFormDescription: [
    'Before proceeding with the creation of a product instance with Experimental Mode feature enabled, ',
    'please read and acknowledge the following use policies, responsibilities and risks:'
  ],
  consentFormUsePoliciesHeader: 'Use Policies:',
  consentFormUsePolicies: [
    'Do not use this product instance to develop software for production.',
    'Do not install tools that you are not familiar with or do not have a license for.',
    'Do not install tools from unknown or suspicious sources.',
    'Do not upload software artifacts to Artifactory.'
  ],
  consentFormResponsibilitiesHeader: 'Responsibilities:',
  consentFormResponsibilities1: [
    'You are responsible for all actions taken ',
    'within the product instance.'
  ],
  consentFormResponsibilities2: [
    'You are responsible for ensuring that all artifacts generated in this product instance are not ',
    'transferred or copied out of the instance.'
  ],
  consentFormRisksHeader: 'Risks:',
  consentFormRisks1: [
    'Unauthorized Uploads: Uploads and use of untrusted artifacts in the software integration process ',
    'compromises the software integrity.'
  ],
  consentFormRisks2: [
    'Software Tampering and Safety Risks: The use of untrusted artifacts in software integration can ',
    'lead to software tampering, potentially causing damage to the company\'s reputation, ',
    'financial losses, and introducing vulnerabilities that compromise the safety and security of ',
    'vehicles, leading to accidents or harm to occupants.',
  ],
  consentFormRisks3: [
    `Auditability Issues: The inability to reproduce artifacts once an instance is terminated compromises 
    auditability, making it difficult to verify the steps taken within the instance with Experimental Mode 
    enabled to generate an artifact. This can lead to non-compliance with regulatory standards, resulting in 
    fines and legal penalties.`,
  ],
  consentFormAcknowledgement: [
    `By checking the box below, you acknowledge understanding and acceptance of these terms 
    and agree to comply with all outlined responsibilities and policies. 
    Failure to adhere will result in inability to create a product instance with
    Experimental Mode feature enabled.`
  ],
  consentFormCheckboxLabel: 'I consent to the terms'
};