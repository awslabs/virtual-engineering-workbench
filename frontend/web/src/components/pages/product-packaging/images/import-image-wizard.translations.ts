export const i18n = {
  // Wizard steps
  step1Title: 'Select source',
  step2TitleAmi: 'Enter AMI details',
  step2TitleSubscription: 'Select subscription',
  step2TitleAwsPublished: 'Confirm AMI',
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
  sourceAwsPublished: 'AWS-published AMI',
  sourceAwsPublishedDescription:
    'Import an AMI that AWS sells itself. No Marketplace subscription is needed.',

  // AWS-published AMI resolution
  awsPublishedHeader: 'AWS-published AMI',
  awsPublishedAlert:
    'AWS sells this product itself, so there is no Marketplace subscription. '
    + 'The AMI below was looked up from the listing you came from.',
  awsPublishedResolving: 'Looking up the AMI for this listing...',
  awsPublishedResolveFailedHeader: 'This listing could not be resolved to an AMI',
  awsPublishedResolveFailed: 'The AMI for this listing could not be resolved.',
  awsPublishedUnavailable: 'Importing AWS-published AMIs is not available in this deployment.',
  awsPublishedProductLabel: 'Product',
  awsPublishedRegionLabel: 'Region',
  awsPublishedAmbiguous:
    'This product offers more than one AMI. They differ by architecture — '
    + 'select the one you want to import.',
  awsPublishedColumnAmiId: 'AMI ID',
  awsPublishedColumnAmiName: 'AMI Name',
  awsPublishedColumnArchitecture: 'Architecture',
  awsPublishedColumnOwner: 'Owner Account',
  awsPublishedColumnStatus: 'Status',
  awsPublishedStatusImported: 'Already imported',
  awsPublishedStatusAvailable: 'Available',
  awsPublishedEmpty: 'No AMI was found for this listing.',

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
  handoffAlreadyImported: 'This product is already imported in this project.',
  handoffUnavailableHeader: 'Purchased product not listed yet',
  handoffUnavailable:
    'The product you just purchased is not in the list of subscriptions yet. New '
    + 'subscriptions can take a few minutes to appear. Reload the page to check again, '
    + 'or pick another subscription.',
  availableSubscriptionsHeader: 'Available Subscriptions',
  subscriptionsEmptyPrimary: 'No Marketplace subscriptions available yet.',
  subscriptionsEmptyHint:
    'Subscribe to a product from Marketplace → Browse catalog first, or switch the '
    + 'source above to "Existing AMI" and paste an AMI ID directly. '
    + 'Products AWS sells itself (Windows Server, RHEL, SUSE, Ubuntu Pro, Amazon Linux) '
    + 'need no subscription and never appear here — open them from '
    + 'Marketplace → Browse catalog and import them directly.',
  columnProductName: 'Product Name',
  columnVendor: 'Vendor',
  columnProductCode: 'Product Code',
  columnType: 'Type',
  columnStatus: 'Status',
  statusImported: 'Imported',
  statusAvailable: 'Available',
  statusUpdateAvailable: 'Update available',
  updateFlowAlert:
    'This project already has a version of this Marketplace product '
    + 'imported. Completing this wizard will import the newer AMI as an '
    + 'additional entry in the Images list — the existing image is not '
    + 'modified or removed.',

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
  badgeDeprecated: 'Deprecated',
  deprecatedAmiAlert:
    'The newest AMI this subscription publishes is deprecated. '
    + 'You can still import it, but the vendor no longer supports it '
    + 'and new instances may stop being launchable. '
    + 'Check whether the vendor has published a replacement product.',
  loadSubscriptionsFailed: 'Failed to load marketplace subscriptions.',

  // Cancel prompt
  cancelPromptHeader: 'Cancel image import',
  cancelPromptText1: 'You are about to cancel the import of your image.',
  cancelPromptText2: 'Any changes you have made to the form will be lost.',
  cancelPromptText3: 'Do you want to proceed?',
  cancelPromptCancelText: 'Cancel',
  cancelPromptConfirmText: 'Confirm',
};
