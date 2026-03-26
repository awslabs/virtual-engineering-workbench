import { i18nProvisionedProductDetails } from '../../provisioned-products/provisioned-product-detail';

export const i18nVirtualTargetDetails = {
  ...i18nProvisionedProductDetails,
  breadcrumbItemLvl1: 'Virtual targets: My virtual targets',
  errorMessageHeader: 'Unable to fetch virtual target',
  noParamsSubtitle: 'Virtual target does not have any output parameters',
  warningOverprovisionedBaiseContent: 'Your virtual target is not being used to its full capacity.',
  warningUnderprovisionedBaiseContent: 'Your virtual target is being used to its full capacity.',
  infoPanelHeader: 'View details',
  infoPanelLabel1: 'What can I accomplish here?',
  infoPanelMessage1: `Virtual targets are runtime environments that are abstractions 
  of the target hardware at various levels. `,
  infoPanelMessage2: 'An overview of the the virtual target can be found in the top panel.',
  infoPanelMessage3: `This page also provides information about the general configuration 
  of the virtual target such as the instance type, instance ID, private IP, and mapped IP.`,
  costDescription: 'The cost you have incurred by running this virtual target.',
  efficiencyInfoSuccess: 'This virtual target is being used efficiently.',
  efficiencyInfoWarning: `This virtual target is idle 90% and the instance size is too large. 
  Consider reducing the instance size or stopping the virtual target to save costs.`,
  removeVirtualTarget: 'Remove',
};
