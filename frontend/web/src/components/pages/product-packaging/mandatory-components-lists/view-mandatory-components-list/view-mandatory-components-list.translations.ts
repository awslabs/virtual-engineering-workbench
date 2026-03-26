
export const i18n = {
  breadcrumbLevel1: 'Product management: Mandatory Component Lists',
  breadcrumbLevel2: 'View mandatory components list',
  pageHeader: (platform: string, architecture: string, osVersion: string) =>
    `${platform}-${architecture}-${osVersion}`,
  detailsHeader: 'Overview',
  detailsPlatform: 'Platform',
  detailsArchitecture: 'Architecture',
  detailsOsVersion: 'OS Version',
  mandatoryComponentsListActions: 'Actions',
  mandatoryComponentsListUpdateDetails: 'Update',
  mandatoryComponentsListHeaderDescription: (recipeId:string) => `${recipeId} recipe version`,
  mandatoryComponentListsAlert: 'Please note that mandatory component lists are shared between programs. ' +
    'Make sure to only edit them in the program where their components are defined.',
  headerActionReturn: 'Return',
  headerActionUpdate: 'Update',
  fetchMandatoryComponentsListError: 'Unable to fetch mandatory components list details',
  componentsVersionsHeader: 'Components',
};