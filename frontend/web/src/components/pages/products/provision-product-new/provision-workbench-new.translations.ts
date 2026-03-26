export const i18nProvisionWorkbench = {
  cancelButton: 'Cancel',
  previousButton: 'Previous',
  nextButton: 'Next',
  submitButton: 'Launch instance',
  titleStep1: 'Configure settings',
  titleStep2: 'Set parameters',
  titleStep3: 'Review and create',
  breadcrumbL1: 'Workbenches: All workbenches',
  breadcrumbL2: 'Create workbench',
  helpTitle: 'Create a product instance',
  helpDescription: 'Here you can enter all the required parameters to create the selected product.',
  stepNumberLabel: (stepNumber: number) => `Step ${stepNumber}`,
  collapsedStepsLabel: (stepNumber: number, stepsCount: number) =>`Step ${stepNumber} of ${stepsCount}`,
  cancelPromptHeader: 'Cancel workbench creation',
  cancelPromptText1: 'You are about to cancel the creation of your workbench.',
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm',
  productProvisionErrorTitle: 'Product creation failed',
  productProvisionErrorText: 'You can find more details in the Workbenches screen',
  productProvisionSuccessTitle: 'Product creation started',
  productProvisionSuccessText: 'Product creation may take a few minutes to complete.',
  productVersionsFetchErrorTitle: 'Unable to fetch the product versions',
  productParametersFetchErrorTitle: 'Unable to fetch the product parameters',
  productProvisionError: 'Unable to create product',
  productType: 'WORKBENCH',

  step1InfoPanelHeader: 'Configure settings',
  step1InfoPanelLabel: 'How do I fill this information in?',
  step1InfoPanelMessage1: `Select the region that you would like the workbench to be hosted from.
  It is advised you select a region close to your place of work as this will reduce latency.`,
  step2InfoPanelHeader: 'Set parameters',
  step1InfoPanelMessage2: `Select the appropriate version. After selection you will be able to
  see additional information such as the installed tools, release notes, and main software
  versions associated to the version.`,
  step1InfoPanelMessageExperimentalInstance: `Select the whether this instance is experimental or not.
  Experimental enables you to perform experiments by changing an existing tool version,
  installing a new tool, and modifying the operating system configuration.
  There is a limit of 3 experimental instances per program that can be provisioned.`,
  step1InfoPanelMessage3: '',
  step2InfoPanelLabel: 'How do I fill this information in?',
  step2InfoPanelMessage1: `Amazon EC2 provides instances in various types of sizes, performance
  and capabilities. Choose the instance that will best suit you.`,
  step2InfoPanelMessage2: `Select a volume size that is appropriate and realistic. In case you select
  an instance size that your workload does not utilize, VEW will support you in sizing down the
  instance to save cost. Choosing the right volume size is important to keep costs in control. `,
  step3InfoPanelHeader: 'Review and create',
  step3InfoPanelMessage1: `Review the entered information before creating your workbench. This
  allows you to ensure that everything is correct. Some of the entered information may not be
  able to be edited after creation.`,

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