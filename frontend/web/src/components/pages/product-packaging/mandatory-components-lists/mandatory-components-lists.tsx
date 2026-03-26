import {
  Alert,
  Button,
  Header,
  HelpPanel,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
  TextFilter,
} from '@cloudscape-design/components';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { FC } from 'react';
import { BreadcrumbItem } from '../../../layout';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { EmptyGridNotification, NoMatchTableNotification } from '../../shared';
import { useMandatoryComponentsLists } from './mandatory-components-lists.logic';
import { i18n, } from './mandatory-components-lists.translations';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { MandatoryComponentsList } from '../../../../services/API/proserve-wb-packaging-api';
import { packagingAPI } from '../../../../services';
import { RoleBasedFeature } from '../../../../state';
import { RoleAccessToggle } from '../../shared/role-access-toggle';

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
interface MandatoryComponentsListsProps {
}

const MandatoryComponentsLists: FC<MandatoryComponentsListsProps> = () => {

  const {
    mandatorycomponentslists,
    loadMandatoryComponentsLists,
    isLoading,
  } = useMandatoryComponentsLists({ serviceApi: packagingAPI });

  const { navigateTo } = useNavigationPaths();

  const columnDefinitions: TableProps.ColumnDefinition<MandatoryComponentsList>[] = [
    {
      id: 'platform',
      header: i18n.tableHeaderPlatform,
      cell: e => e.mandatoryComponentsListPlatform,
    },
    {
      id: 'architecture',
      header: i18n.tableHeaderArchitecture,
      cell: e => e.mandatoryComponentsListArchitecture,
    },
    {
      id: 'osVersion',
      header: i18n.tableHeaderOsVersion,
      cell: e => e.mandatoryComponentsListOsVersion,
    },
  ];

  const { items, actions, filterProps, collectionProps, paginationProps } = useCollection(
    mandatorycomponentslists,
    {
      filtering: {
        empty: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => actions.setFiltering('')}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle}
        />,
        noMatch: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => actions.setFiltering('')}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle} />,
      },
      selection: {},
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE }
    }
  );

  return (
    <WorkbenchAppLayout
      breadcrumbItems={getBreadcrumbItems()}
      content={renderContent()}
      contentType="default"
      tools={renderTools()}
      customHeader={renderHeader()}
    />
  );

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadcrumbLevel1, href: '#' },
    ];
  }

  function renderHeader() {
    return <>
      <Header
        variant='h1'
        description={i18n.navHeaderDescription}
        actions={
          <RoleAccessToggle feature={RoleBasedFeature.ManageMandatoryComponents}>
            <Button onClick={() => {
              navigateTo(RouteNames.CreateMandatoryComponentsList);
            }}
            variant='primary'
            data-test='create-mandatory-components-list-btn'
            >
              {i18n.createButtonText}
            </Button>
          </RoleAccessToggle>
        }
      >
        {i18n.navHeader}
      </Header>
    </>;
  }

  function getSelectedItem(): MandatoryComponentsList | undefined {
    if (collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined) {
      return collectionProps.selectedItems[0];
    }
    return undefined;
  }

  function renderContent() {
    return (
      <>
        <SpaceBetween direction="vertical" size="l">
          <Alert type="info">{i18n.mandatoryComponentListsAlert}</Alert>
          <Table
            data-test="table-mandatorycomponentslists"
            {...collectionProps}
            header={
              <Header
                variant="h2"
                counter={`(${mandatorycomponentslists.length})`}
                actions={
                  <SpaceBetween direction="horizontal" size="xs">
                    <Button
                      data-test="button-refresh-table"
                      iconName="refresh"
                      onClick={loadMandatoryComponentsLists}
                      loading={isLoading}
                    />
                    <Button
                      data-test="button-view-table"
                      loading={isLoading}
                      disabled={!getSelectedItem()}
                      onClick={() => navigateTo(RouteNames.ViewMandatoryComponentsList, {
                        ':platform': getSelectedItem()?.mandatoryComponentsListPlatform,
                        ':architecture': getSelectedItem()?.mandatoryComponentsListArchitecture,
                        ':osVersion': getSelectedItem()?.mandatoryComponentsListOsVersion,
                      })}
                    >
                      {i18n.buttonViewMandatoryComponentsList}
                    </Button>
                    <RoleAccessToggle feature={RoleBasedFeature.ManageMandatoryComponents}>
                      <Button
                        data-test="button-update-table"
                        loading={isLoading}
                        disabled={!getSelectedItem()}
                        onClick={() => navigateTo(RouteNames.UpdateMandatoryComponentsList, {
                          ':platform': getSelectedItem()?.mandatoryComponentsListPlatform,
                          ':architecture': getSelectedItem()?.mandatoryComponentsListArchitecture,
                          ':osVersion': getSelectedItem()?.mandatoryComponentsListOsVersion,
                        })}
                      >
                        {i18n.buttonUpdateMandatoryComponentsList}
                      </Button>
                    </RoleAccessToggle>
                  </SpaceBetween>
                }
              >
                {i18n.tableHeader}
              </Header>
            }
            loading={isLoading}
            items={items}
            selectionType="single"
            empty={
              <EmptyGridNotification
                title={i18n.emptyMandatoryComponentsLists}
                subTitle={i18n.emptyMandatoryComponentsListsSubTitle}
                actionButtonText={i18n.emptyMandatoryComponentsListsResolve}
                actionButtonOnClick={emptyMandatoryComponentsListsResolveAction}
              />
            }
            filter={
              <TextFilter
                {...filterProps}
                filteringPlaceholder={i18n.findMandatoryComponentsListsPlaceholder}
                filteringAriaLabel={i18n.findMandatoryComponentsListsPlaceholder}
              />
            }
            pagination={<Pagination {...paginationProps} />}
            columnDefinitions={columnDefinitions}
            contentDensity="compact"
            wrapLines
          />
        </SpaceBetween>
      </>
    );
  }


  function emptyMandatoryComponentsListsResolveAction() {
    navigateTo(RouteNames.CreateMandatoryComponentsList);
  }

  function renderTools() {
    return (
      <HelpPanel
        header={<h2>{i18n.infoHeader}</h2>}
      >
        <p>{i18n.infoDescription}</p>
      </HelpPanel>
    );
  }
};

export { MandatoryComponentsLists };
