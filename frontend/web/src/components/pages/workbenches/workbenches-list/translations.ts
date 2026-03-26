import { i18n as provisionedProductsi18n } from '../../provisioned-products/translations';

export const i18n = {
  ...provisionedProductsi18n,
  ...{
    ariaSelectionGroupLabel: 'Workbench selection',
    noProducts: 'No workbenches',
    noProductsLong: 'You haven\'t added any workbenches yet.',
    noProductsActionButtonText: 'Create a workbench',
    noProductsFound: 'No workbenches found.',
    clearFilter: 'Clear filter',
    loadingProducts: 'Loading workbenches',
    breadCrumbItem1: 'Workbenches: My workbenches',
    splitPanelTitle: 'Workbench details',
    provisionedProductCardProductName: 'Workbench',
    filterPlaceholder: 'Find workbenches or tools',
    headerTitle: 'My workbenches',
    infoHeader: 'Workbenches',
    infoDescription:
      'In this screen you can find all your launched workbenches.',
    loginPromptHeader: 'Log in to the workbench',
    betaUserPromptContent: `
This is a testing environment and not intended for production data.
Please refrain from uploading proprietary intellectual property to the workbenches.
`,
    deprovisionModalHeader: 'Remove workbenches',
    errorDeprovision: 'Unable to remove the selected workbenches',
    errorStart: 'Unable to start the selected workbench',
    errorStop: 'Unable to stop the selected workbench',
  },
};
