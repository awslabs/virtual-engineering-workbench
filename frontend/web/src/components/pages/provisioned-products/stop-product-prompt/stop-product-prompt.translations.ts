export const i18n = {
  stopModalHeader: (productType: string) => `Stop ${productType}?`,
  stopModalOK: 'Confirm',
  stopModalCancel: 'Cancel',
  stopModalText1: 'You are about to stop ',
  stopModalText2: (productType: string) => {
    return `This operation will temporarily shut down the EC2 instance, 
      but all introduced data will be kept, and the ${productType} can be restarted later.`;
  },
  stopModalText3: 'Do you want to proceed?',
};

export const PRODUCT_TYPE_MAP: { [key: string]: string } = {
  virtualTarget: 'virtual target',
  workbench: 'workbench',
};