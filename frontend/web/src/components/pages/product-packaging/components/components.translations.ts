import { StatusIndicatorProps } from '@cloudscape-design/components';

export const i18n = {
  breadcrumbLevel1: 'Product management: Components',
  navHeader: 'Components',
  navHeaderDescription:
    'View all components that are available in the selected program for product packaging.',
  navHeaderInfo: 'Info',
  createButtonText: 'Create component',
  emptyComponents: 'No components',
  emptyComponentsSubTitle: 'No available components',
  emptyComponentsResolve: 'Create component',
  tableFilterNoResultTitle: 'No components',
  tableFilterNoResultActionText: 'Clear filter',
  tableFilterNoResultSubtitle: 'No components were found using your search criteria.',
  header: 'Overview',
  something: 'Something',
  infoDescription: 'In this screen you can list components.',
  findComponentsPlaceholder: 'Find components',
  componentArchive: 'Archive',
  componentCreate: 'Create',
  componentUpdate: 'Update',
  componentRelease: 'Release',
  componentShare: 'Share',
  componentsFetchErrorTitle: 'Unable to fetch components',
  statusFirstOptionValue: 'CREATED',
  tableHeader: 'Components',
  tableHeaderComponentName: 'Name',
  tableHeaderComponentDescription: 'Description',
  tableHeaderComponentPlatform: 'Platform',
  tableHeaderComponentLastUpdate: 'Last Update',
  tableHeaderStatus: 'Status',
  buttonActions: 'Actions',
  buttonViewComponent: 'View',
  createSuccessMessageHeader: 'Request successful',
  createArchiveSuccessMessageContent: 'Component has been successfully archived',
  createShareSuccessMessageContent: (ids: string[]) =>
    `Your component is now shared with following projects: ${ids.join(', ')}`,
  createFailMessageHeader: 'Sorry, something went wrong!',
  infoPanelHeader: 'Components',
  infoPanelLabel1: 'What is a component?',
  infoPanelMessage1: `A component, also known as Image Builder Component is a building block of a recipe, 
  representing reusable scripts that install, configure, validate, and test a specific software tool on 
  a workbench instance.`,
  infoPanelLabel2: 'What can I accomplish here?',
  infoPanelMessage2: `Component management plays a crucial role in the product packaging process, 
  as it is the starting point to create components and their initial versions 
  (release candidate versions), and release them once they are validated. `,
};

export const COMPONENT_STATUS_COLOR_MAP: { [key: string]: StatusIndicatorProps.Type } = {
  CREATED: 'success',
  FAILED: 'error',
  RETIRED: 'stopped',
  PROCESSING: 'pending',
};