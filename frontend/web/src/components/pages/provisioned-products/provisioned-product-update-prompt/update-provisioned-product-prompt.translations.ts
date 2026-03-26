export const i18n = {
  updateSuccessMessageHeader: 'Product updating started successfully',
  updateSuccessMessageContent: 'Please refer to the product card for the status',
  updateFailMessageHeader: 'Error while updating product',
  updateModalHeader: (updateType: string) => `Update ${updateType}`,
  updateModalOK: 'Confirm',
  updateModalCancel: 'Cancel',
  updateModalText: (updateType: string) =>
    `You are about to update the ${updateType} of your product.`,
  productVersionsFetchErrorTitle: 'Unable to fetch product version details.',
  upgradeSuccessMessageHeader: 'Upgrade started successfully.',
  upgradeSuccessMessageContent: 'Upgrade process may take a few minutes.',
  upgradeFailMessageHeader: 'Unable to upgrade the provisioned product.',
  recommendedVersionTag: 'Recommended',
  productVersionsLoading: 'Loading versions...',
  noSupportedInstanceTypesText: 'Only one instance type is configured for this version.',
  noSupportedVersionsText: 'Only one version is configured for this product.',
  updateVersionModalInfo: `The selected version may have different instance types available than 
   your current instance type. If this is the case, the instance type will be selected for you. 
   If it is not suitable you may update your instance type at any time.`,
  versionLabel: 'Version',
};