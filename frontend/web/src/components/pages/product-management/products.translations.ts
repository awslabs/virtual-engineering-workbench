import { StatusIndicatorProps } from '@cloudscape-design/components';

export const i18n = {
  breadcrumbLevel1: 'Product management: Products',
  header: 'Products',
  containerHeader: 'Products',
  tableHeaderProductName: 'Name',
  tableHeaderProductDescription: 'Description',
  tableHeaderProductTechnology: 'Technology',
  tableHeaderProductType: 'Type',
  tableHeaderProductStatus: 'Status',
  tableHeaderProductCreateDate: 'Create date',
  tableHeaderProductUrl: 'Url',
  buttonAddProduct: 'Create product',
  errorUnableToFetchProducts: 'Unable to fetch products',
  findProductsPlaceholder: 'Find products',
  tableFilterNoResultTitle: 'No products',
  tableFilterNoResultActionText: 'Clear filter',
  tableFilterNoResultSubtitle: 'No products were found using your search criteria.',
  archiveProductButtonText: 'Archive',
  viewDetailsButtonText: 'View',
  overviewHeader: 'Overview',
  overviewTotal: 'Total',
  overviewWorkbenches: 'Workbenches',
  overviewOthers: 'Others',
  infoHeader: 'Product',
  infoDescription: 'In this screen you can list products.',
  statusOptionAny: 'Any status',
  statusOptionCreated: 'Created',
  statusOptionFailed: 'Failed',
  statusOptionArchived: 'Archived',
  infoPanelHeader: 'Products',
  infoPanelLabel1: 'What is a product?',
  infoPanelMessage1: `A product is a set of AWS cloud resources ready to be provisioned and 
  defined by CloudFormation templates. A product is a blueprint for either a VEW workbench or 
  VEW virtual target. `,
  infoPanelLabel2: 'What can I accomplish here?',
  infoPanelMessage2: `This page is a cornerstone of the product publishing process in VEW i.e. 
  distributing the products to use case accounts and making them available for users.`,
  infoPanelMessage3: `You can browse existing products categorized by type and technology, archive 
  a product and create a new one.`,
  statusFirstOptionValue: 'CREATED',
};

export const PRODUCT_STATUS_MAP: { [key: string]: string } = {
  CREATING: 'Creating',
  CREATED: 'Created',
  FAILED: 'Failed',
  PAUSED: 'Paused',
  ARCHIVING: 'Archiving',
  ARCHIVED: 'Archived',
  UNKNOWN: 'Unknown',
  UPDATING: 'Updating',
  RETIRING: 'Retiring',
  RETIRED: 'Retired'
};

export const PRODUCT_STATUS_COLOR_MAP: { [key: string]: StatusIndicatorProps.Type } = {
  CREATING: 'pending',
  CREATED: 'success',
  FAILED: 'error',
  PAUSED: 'stopped',
  ARCHIVING: 'pending',
  ARCHIVED: 'stopped',
  UNKNOWN: 'pending',
};

export const PRODUCT_TYPE_MAP: { [key: string]: string } = {
  WORKBENCH: 'Workbench',
  VIRTUAL_TARGET: 'Virtual target',
};

export const PRODUCT_VERSION_RELEASE_TYPE_MAP: { [key: string]: string } = {
  MAJOR: 'Major',
  MINOR: 'Minor',
  PATCH: 'Patch'
};