import {
  Box,
  Button,
  ColumnLayout,
  Container,
  Header,
  HelpPanel,
  Link,
  Pagination,
  Select,
  SpaceBetween,
  StatusIndicator,
  Table,
  TableProps,
  TextFilter
} from '@cloudscape-design/components';
import { useState, useEffect } from 'react';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { ArchiveProductPrompt } from './user-prompts';
import {
  PRODUCT_STATUS_COLOR_MAP,
  PRODUCT_STATUS_MAP,
  PRODUCT_TYPE_MAP,
  i18n
} from './products.translations';
import { useProducts } from './products.logic';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { NoMatchTableNotification, UserDate } from '../shared';
import { Product } from '../../../services/API/proserve-wb-publishing-api';
import { InfoBox } from '../shared/info-box';
import { useRoleAccessToggle } from '../../../hooks/role-access-toggle';
import { RoleBasedFeature } from '../../../state';
import { CompareDates } from '../shared/compare-dates';
import { useCloudscapeTablePersisentState } from '../../../hooks';


const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;

export const Products = () => {
  const { navigateTo } = useNavigationPaths();
  const { products, isLoading, loadProducts, status, setStatus, statusOptions } = useProducts();
  const [selectedProduct, setSelectedProduct] = useState<Product>();
  const [archiveConfirmVisible, setArchiveConfirmVisible] = useState(false);
  const isFeatureAccessible = useRoleAccessToggle();

  const columnDefinitions: TableProps.ColumnDefinition<Product>[] = [
    {
      id: 'name',
      header: i18n.tableHeaderProductName,
      cell: (e) => {
        return <div>
          <Link onFollow={() => {
            navigateTo(RouteNames.Product, {
              ':id': e.productId,
            });
          }}>{e.productName}</Link>
        </div>;
      },
      sortingField: 'productName',
      isRowHeader: true
    },
    {
      id: 'description',
      header: i18n.tableHeaderProductDescription,
      cell: e => e.productDescription,
    },
    {
      id: 'technology',
      header: i18n.tableHeaderProductTechnology,
      cell: e => e.technologyName,
      sortingField: 'technologyName'
    },
    {
      id: 'type',
      header: i18n.tableHeaderProductType,
      cell: e => PRODUCT_TYPE_MAP[e.productType],
      sortingField: 'productType'
    },
    {
      id: 'createDate',
      header: i18n.tableHeaderProductCreateDate,
      cell: e => {
        if (!e.createDate) {
          return '';
        }

        return <UserDate date={e.createDate}></UserDate>;
      },
      sortingField: 'createDate',
      sortingComparator: (a: Product, b: Product) => CompareDates(a.createDate, b.createDate)
    },
    {
      id: 'status',
      header: i18n.tableHeaderProductStatus,
      cell: e => <StatusIndicator
        type={PRODUCT_STATUS_COLOR_MAP[e.status || 'UNKNOWN'] || 'pending'}
      >
        {PRODUCT_STATUS_MAP[e.status || 'UNKNOWN']}
      </StatusIndicator>,
      sortingField: 'status'
    },

  ];

  const { items, actions, filterProps, collectionProps, paginationProps } = useCollection(
    products,
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
      sorting: {
        defaultState:
        {
          sortingColumn: columnDefinitions[3],
          isDescending: true,
        }
      },
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE }
    }
  );

  const { onSortingChange } = useCloudscapeTablePersisentState<Product>({
    key: 'prod-man-products',
    columnDefinitions,
    setSorting: actions.setSorting,
  });

  useEffect(() => {
    setSelectedProduct?.(collectionProps.selectedItems && collectionProps.selectedItems[0]);
  }, [collectionProps, setSelectedProduct]);

  return (
    <>
      <ArchiveProductPrompt
        projectId={selectedProduct?.projectId}
        productId={selectedProduct?.productId}
        selectedProduct={selectedProduct}
        archiveConfirmVisible={archiveConfirmVisible}
        setArchiveConfirmVisible={setArchiveConfirmVisible}
        loadProductDetails={loadProducts}
      />
      <WorkbenchAppLayout
        content={renderContent()}
        contentType='default'
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: '#' }
        ]}
        customHeader={renderHeader()}
        tools={renderTools()} />
    </>
  );

  function renderHeader() {
    return <Header
      data-test="page-header"
      variant='awsui-h1-sticky'
      actions={
        <SpaceBetween size='xs' direction='horizontal'>
          <Button
            onClick={() => navigateTo(RouteNames.CreateProduct)}
            variant='primary'>{i18n.buttonAddProduct}</Button>
        </SpaceBetween>
      }
    >
      {i18n.header}</Header>;
  }

  function renderContent() {
    return <>
      <SpaceBetween size='l'>
        {renderOverview()}
        {renderTable()}
      </SpaceBetween>
    </>;
  }

  function renderOverview() {
    return <>
      <Container
        header={
          <Header data-test="overview-header" variant='h2'>
            {i18n.overviewHeader}
          </Header>
        }
      >
        {<ColumnLayout columns={3} variant='text-grid'>
          <SpaceBetween size='l'>
            <InfoBox
              data-test="total-products"
              label={i18n.overviewTotal}
              value={products.length}
              loading={isLoading} />
          </SpaceBetween>
          <SpaceBetween size='l'>
            <InfoBox
              data-test="workbench-products"
              label={i18n.overviewWorkbenches}
              value={products.filter(p => p.productType === Object.keys(PRODUCT_TYPE_MAP)[0]).length}
              loading={isLoading} />
          </SpaceBetween>
          <SpaceBetween size='l'>
            <InfoBox
              data-test="other-products"
              label={i18n.overviewOthers}
              value={products.filter(p => p.productType !== Object.keys(PRODUCT_TYPE_MAP)[0]).length}
              loading={isLoading} />
          </SpaceBetween>
        </ColumnLayout>}
      </Container>
    </>;
  }

  function renderTable() {
    return <>
      <Table
        {...collectionProps}
        resizableColumns={true}
        onSortingChange={onSortingChange}
        header={
          <Header
            variant='h2'
            counter={`(${products.length})`}
            actions={
              <SpaceBetween direction='horizontal' size='m'>
                <Button iconName='refresh' loading={isLoading} onClick={loadProducts} />
                {isFeatureAccessible(RoleBasedFeature.ArchiveProducts) &&
                  <Button
                    disabled={
                      collectionProps.selectedItems?.length === ZERO_INDEX ||
                      selectedProduct?.status !== PRODUCT_STATUS_MAP.CREATED.toUpperCase()}
                    onClick={(e) => {
                      e.preventDefault();
                      setArchiveConfirmVisible(true);
                    }}
                    data-test="archive-product-button">
                    {i18n.archiveProductButtonText}
                  </Button>
                }
                <Button disabled={collectionProps.selectedItems?.length === ZERO_INDEX} onClick={(e) => {
                  e.preventDefault();
                  const prodId = selectedProduct?.productId;
                  navigateTo(RouteNames.Product, {
                    ':id': prodId
                  });
                }}
                data-test="view-product-button">
                  {i18n.viewDetailsButtonText}
                </Button>
              </SpaceBetween>
            }
          >
            {i18n.containerHeader}
          </Header>}
        loading={isLoading}
        items={items}
        selectionType='single'
        filter={
          <SpaceBetween size="m" direction="horizontal">
            <TextFilter
              {...filterProps}
              filteringPlaceholder={i18n.findProductsPlaceholder}
              filteringAriaLabel={i18n.findProductsPlaceholder}
            />
            <Select
              options={statusOptions}
              selectedAriaLabel="Selected"
              selectedOption={status}
              onChange={event => {
                setStatus(event.detail.selectedOption);
              }}
              expandToViewport={true}
              data-test="product-status-filter"
            />
          </SpaceBetween>
        }
        pagination={
          <Pagination
            {...paginationProps}
          />
        }
        columnDefinitions={columnDefinitions} />
    </>;
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel2}</Box>
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
          <Box variant="p">{i18n.infoPanelMessage3}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};
