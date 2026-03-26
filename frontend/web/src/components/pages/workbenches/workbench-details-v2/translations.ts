import { i18nProvisionedProductDetails } from '../../provisioned-products/provisioned-product-detail';
import { i18n } from '../../provisioned-products';

export const i18nWorkbenchDetails = {
  ...i18nProvisionedProductDetails,
  ...i18n,
  breadcrumbItemLvl1: 'Workbenches: My workbenches',
  errorMessageHeader: 'Unable to fetch workbench',
  noParamsSubtitle: 'Workbench does not have any output parameters',
  warningOverprovisionedBaiseContent: 'Your workbench is not being used to its full capacity.',
  warningUnderprovisionedBaiseContent: 'Your workbench is being used to its full capacity.',
  infoPanelHeader: 'View details',
  infoPanelLabel1: 'What can I accomplish here?',
  infoPanelMessage1: `Workbenches are predefined use case specific environments that come 
  fully equipped with all the tools, integrated development environments (IDEs), and licensing 
  necessary for you to jump start your work. `,
  infoPanelMessage2: 'An overview of the the workbench can be found in the top panel.',
  infoPanelMessage3: `This page also provides information about the general configuration
   of the workbench such as the instance type, volume size, instance ID, private IP, and mapped IP.`,
  costDescription: 'The cost you have incurred by running this workbench.',
  efficiencyInfoSuccess: 'This workbench is being used efficiently.',
  efficiencyInfoWarning: `This workbench is idle 90% and the instance size is too large. 
  Consider reducing the instance size or stopping the workbench to save costs.`,
  actionsButton: 'Actions',
  updateInstanceTypeAction: 'Update instance type',
  updateVersionAction: 'Update version',
  startAction: 'Start workbench',
  stopAction: 'Stop workbench',
  removeWorkbench: 'Remove workbench',
  confirmRemoveLabel: 'Remove provisioned product',
  failedToLoadProvisionedProduct: 'Failed to load provisioned product details.',
  deprovisionModalCancel: 'Cancel',
  deprovisionModalOK: 'Confirm'
};
