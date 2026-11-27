import {
  Badge,
  Box,
  Button,
  Header,
  HelpPanel,
  Link,
  Pagination,
  SpaceBetween,
  StatusIndicator,
  Table,
  TableProps,
  Tabs,
  TextFilter,
} from '@cloudscape-design/components';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { FC, useState } from 'react';
import {
  DiscoveredMarketplaceSubscription as MarketplaceSubscription,
  DiscoverMarketplaceSubscriptionsResponse,
} from '../../../../services/API/proserve-wb-packaging-api';
import { useDiscoverMarketplaceSubscriptions } from
  '../../../../hooks/packaging/discover-marketplace-subscriptions.logic';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { BreadcrumbItem } from '../../../layout';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { EmptyGridNotification } from '../../shared';
import { i18n } from './marketplace-subscriptions.translations';
import { useCloudscapeTablePersisentState } from '../../../../hooks';

const MARKETPLACE_URL = 'https://aws.amazon.com/marketplace';
const PAGE_SIZE = 20;

interface ServiceAPI {
  discoverMarketplaceSubscriptions: (projectId: string) => Promise<DiscoverMarketplaceSubscriptionsResponse>,
}

interface MarketplaceSubscriptionsProps {
  serviceApi: ServiceAPI,
}

const MarketplaceSubscriptions: FC<MarketplaceSubscriptionsProps> = ({ serviceApi }) => {
  const { navigateTo } = useNavigationPaths();
  const [productTypeTab, setProductTypeTab] =
    useState<'AmiProduct' | 'ContainerProduct' | 'SaaSProduct'>('AmiProduct');
  const {
    subscriptions,
    isLoading: loading,
    discover: load,
  } = useDiscoverMarketplaceSubscriptions({ serviceApi });

  const columnDefinitions: TableProps.ColumnDefinition<MarketplaceSubscription>[] = [
    {
      id: 'productName',
      header: i18n.columnProductName,
      // A deprecated AMI can still be imported, so this is a warning rather than a
      // blocker. It sits next to the name because that is what a reader scans.
      cell: (item) =>
        <SpaceBetween direction="horizontal" size="xs">
          <span>{item.productName}</span>
          {item.deprecated && <Badge color="red">{i18n.badgeDeprecated}</Badge>}
        </SpaceBetween>
      ,
      sortingField: 'productName',
    },
    {
      id: 'productCode',
      header: i18n.columnProductCode,
      cell: (item) => item.productCode,
    },
    {
      id: 'regions',
      header: i18n.columnRegions,
      cell: (item) =>
        <Badge>{Object.keys(item.regionalAmiIds || {}).length}</Badge>,
    },
    {
      id: 'hubAmiId',
      header: i18n.columnHubAmiId,
      cell: (item) => item.hubRegionAmiId,
    },
    {
      id: 'type',
      header: i18n.columnType,
      cell: (item) =>
        <Badge color={item.subscriptionOwnership === 'VEW_MANAGED' ? 'green' : 'blue'}>
          {item.subscriptionOwnership}
        </Badge>,
      sortingField: 'subscriptionOwnership',
    },
    {
      id: 'status',
      header: i18n.columnStatus,
      cell: (item) => {
        if (item.newerVersionAvailable) {
          return <StatusIndicator type="warning">{i18n.statusUpdateAvailable}</StatusIndicator>;
        }
        return item.alreadyImported
          ? <StatusIndicator type="success">{i18n.statusImported}</StatusIndicator>
          : <StatusIndicator type="pending">{i18n.statusAvailable}</StatusIndicator>;
      },
    },
    {
      id: 'actions',
      header: i18n.columnActions,
      cell: (item) =>
        <SpaceBetween direction="horizontal" size="xs">
          <Button
            // Enable when either (a) fresh subscription, or (b) already
            // imported but a newer AMI is available. Only disable when
            // the project already has the latest AMI for this product.
            disabled={item.alreadyImported && !item.newerVersionAvailable}
            onClick={() => navigateTo(RouteNames.ImportImage)}
            data-test={item.newerVersionAvailable ? 'update-btn' : 'import-btn'}
          >
            {item.newerVersionAvailable ? i18n.updateButton : i18n.importButton}
          </Button>
        </SpaceBetween>,
    },
  ];

  const { items, actions, collectionProps, filterProps, paginationProps } = useCollection(
    subscriptions,
    {
      filtering: {
        empty:
          <EmptyGridNotification
            title="No subscriptions"
            subTitle="No marketplace subscriptions found."
          />
        ,
        noMatch: <EmptyGridNotification
          title="No matches"
          subTitle="No subscriptions match the filter."
          actionButtonText="Clear filter"
          actionButtonOnClick={() => actions.setFiltering('')}
        />,
      },
      sorting: {},
      pagination: { pageSize: PAGE_SIZE },
    },
  );

  const { onSortingChange } = useCloudscapeTablePersisentState<MarketplaceSubscription>({
    key: 'marketplace-subscriptions',
    columnDefinitions,
    setSorting: actions.setSorting,
  });

  const breadcrumbItems: BreadcrumbItem[] = [
    { path: i18n.header, href: '#' },
  ];

  return (
    <WorkbenchAppLayout
      breadcrumbItems={breadcrumbItems}
      contentType="default"
      customHeader={renderHeader()}
      tools={renderTools()}
      content={renderContent()}
    />
  );

  function renderHeader() {
    return <Header variant="h1">{i18n.header}</Header>;
  }

  function renderContent() {
    return (
      <SpaceBetween size="l">
        <Tabs
          activeTabId={productTypeTab}
          onChange={({ detail }) => {
            if (detail.activeTabId === 'AmiProduct') {
              setProductTypeTab('AmiProduct');
            }
          }}
          tabs={[
            { id: 'AmiProduct', label: i18n.productTypeTabAmi },
            {
              id: 'ContainerProduct',
              label:
                <span>
                  {i18n.productTypeTabContainer}
                  {' '}
                  <Badge>{i18n.comingSoonBadge}</Badge>
                </span>
              ,
              disabled: true,
            },
            {
              id: 'SaaSProduct',
              label:
                <span>
                  {i18n.productTypeTabSaas}
                  {' '}
                  <Badge>{i18n.comingSoonBadge}</Badge>
                </span>
              ,
              disabled: true,
            },
          ]}
        />
        <Table
          data-test="marketplace-subscriptions-table"
          {...collectionProps}
          trackBy="productCode"
          loading={loading}
          items={items}
          onSortingChange={onSortingChange}
          empty={
            <EmptyGridNotification title="No subscriptions" subTitle="No marketplace subscriptions found." />
          }
          filter={
            <TextFilter
              data-test="filter-input"
              {...filterProps}
              filteringPlaceholder={i18n.columnProductName}
              filteringAriaLabel="Filter subscriptions"
            />
          }
          pagination={<Pagination {...paginationProps} />}
          columnDefinitions={columnDefinitions}
          header={
            <Header
              variant="h2"
              counter={`(${subscriptions.length})`}
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <Button
                    variant="primary"
                    onClick={() => navigateTo(RouteNames.MarketplaceProcurementWizard)}
                    data-test="procure-btn"
                  >
                    {i18n.procureButton}
                  </Button>
                  <Button onClick={load} iconName="refresh" data-test="refresh-btn">
                    {i18n.refreshButton}
                  </Button>
                  <Link href={MARKETPLACE_URL} external>
                    {i18n.subscribeButton}
                  </Link>
                </SpaceBetween>
              }
            >
              {i18n.header}
            </Header>
          }
        />
      </SpaceBetween>
    );
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.header}</h2>}>
        <SpaceBetween size="s">
          <Box variant="awsui-key-label">{i18n.alertVewManaged}</Box>
          <Box variant="p">{i18n.alertVewManagedDescription}</Box>
          <Box variant="awsui-key-label">{i18n.alertExternalManaged}</Box>
          <Box variant="p">{i18n.alertExternalManagedDescription}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};

export { MarketplaceSubscriptions };
