export const i18n = {
  // Wizard steps
  step1Title: 'Select source',
  step2TitleAmi: 'Enter AMI details',
  step2TitleSubscription: 'Select subscription',
  step3Title: 'Enter image details',
  step3Header: 'Image details',
  step4Title: 'Select platform and architecture',
  step4Header: 'Platform and architecture',
  step5Title: 'Included software',
  step5Header: 'Included software',
  step5Description: 'List the software included in this image. At least one entry is required.',
  step6Title: 'Review and create',

  // Source selection
  imageSourceHeader: 'Image Source',
  sourceExistingAmi: 'Existing AMI',
  sourceExistingAmiDescription: 'Import an AMI from the Image Service account.',
  sourceMarketplace: 'Marketplace Product',
  sourceMarketplaceDescription: 'Import an AWS Marketplace AMI using an active subscription.',

  // AMI details
  amiDetailsHeader: 'AMI Details',
  amiIdLabel: 'AMI ID',
  amiIdDescription: 'Enter the AMI ID from the Image Service account.',
  amiIdPlaceholder: 'ami-xxxxxxxxxxxxxxxxx',

  // Marketplace subscriptions
  marketplaceSubscriptionsHeader: 'Marketplace Subscriptions',
  marketplaceAlert:
    'Select an active Marketplace subscription to import. '
    + 'Subscriptions marked as already imported cannot be selected again.',
  externallyManagedAlert:
    'Externally Managed subscription: VEW cannot automatically distribute this product. '
    + 'Ensure every target spoke account has its own active Marketplace subscription, '
    + 'or that an Org admin has distributed an active License Manager grant, before publishing. '
    + 'The version will fail at publish time if neither is present.',
  availableSubscriptionsHeader: 'Available Subscriptions',
  columnProductName: 'Product Name',
  columnVendor: 'Vendor',
  columnProductCode: 'Product Code',
  columnType: 'Type',
  columnStatus: 'Status',
  statusImported: 'Imported',
  statusAvailable: 'Available',

  // Details
  imageNameLabel: 'Image Name',
  imageNameConstraint: 'Max 100 characters',
  imageDescriptionLabel: 'Image Description',
  imageDescriptionConstraint: 'Optional, max 500 characters',

  // Platform
  platformLabel: 'Platform',
  architectureLabel: 'Architecture',
  osVersionLabel: 'OS Version',
  osVersionPlaceholder: 'e.g. Ubuntu 25.04',

  // Software
  includedSoftwareLabel: 'Included software',
  addSoftwareButton: 'Add software',
  softwareVendorLabel: 'Vendor',
  softwareNameLabel: 'Name',
  softwareVersionLabel: 'Version',

  // Review
  reviewHeader: 'Review and create',
  reviewSource: 'Source',
  reviewAmiId: 'AMI ID',
  reviewImageName: 'Image Name',
  reviewPlatform: 'Platform',
  reviewArchitecture: 'Architecture',
  reviewOsVersion: 'OS Version',

  // Wizard i18n strings
  stepNumberLabel: (stepNumber: number) => `Step ${stepNumber}`,
  collapsedStepsLabel: (stepNumber: number, stepsCount: number) => `Step ${stepNumber} of ${stepsCount}`,
  cancelButton: 'Cancel',
  previousButton: 'Previous',
  nextButton: 'Next',
  submitButton: 'Create image',

  // Messages
  importSuccess: (imageId: string) => `Image imported successfully: ${imageId}`,
  importFailed: 'Import failed',
  loadSubscriptionsFailed: 'Failed to load marketplace subscriptions.',

  // Cancel prompt
  cancelPromptHeader: 'Cancel image import',
  cancelPromptText1: 'You are about to cancel the import of your image.',
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm',
};
