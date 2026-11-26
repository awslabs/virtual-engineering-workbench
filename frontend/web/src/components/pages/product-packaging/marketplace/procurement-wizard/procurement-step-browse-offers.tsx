import { FC } from 'react';
import {
  Alert,
  Badge,
  Box,
  Button,
  Header,
  Pagination,
  SpaceBetween,
  StatusIndicator,
  Table,
  TableProps,
  Tabs,
} from '@cloudscape-design/components';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { MarketplacePurchaseOption } from '../../../../../services/API/marketplace-procurement-api';
import { i18n } from './procurement-wizard.translations';
import { ProductTypeTab } from './procurement-wizard.logic';
import { EmptyGridNotification } from '../../../shared';

const PAGE_SIZE = 10;

interface Props {
  productType: ProductTypeTab,
  setProductType: (t: ProductTypeTab) => void,
  purchaseOptions: MarketplacePurchaseOption[],
  isLoading: boolean,
  error: Error | null,
  selectedOption: MarketplacePurchaseOption | null,
  onSelect: (option: MarketplacePurchaseOption) => void,
  onRefresh: () => void,
}

export const ProcurementStepBrowseOffers: FC<Props> = ({
  productType,
  setProductType,
  purchaseOptions,
  isLoading,
  error,
  selectedOption,
  onSelect,
  onRefresh,
}) => {
  const columnDefinitions: TableProps.ColumnDefinition<MarketplacePurchaseOption>[] = [
    {
      id: 'purchaseOptionName',
      header: i18n.columnPurchaseOptionName,
      cell: (item) => item.purchaseOptionName || '—',
      sortingField: 'purchaseOptionName',
    },
    {
      id: 'productName',
      header: i18n.columnProductName,
      cell: (item) => item.productName || '—',
      sortingField: 'productName',
    },
    {
      id: 'seller',
      header: i18n.columnSeller,
      cell: (item) => item.sellerOfRecordDisplayName || '—',
    },
    {
      id: 'purchaseOptionType',
      header: i18n.columnPurchaseOptionType,
      cell: (item) => <Badge>{item.purchaseOptionType}</Badge>,
    },
    {
      id: 'offerId',
      header: i18n.columnOfferId,
      cell: (item) => item.offerId,
    },
    {
      id: 'expires',
      header: i18n.columnExpires,
      cell: (item) => item.expirationTime || '—',
    },
  ];

  const { items, collectionProps, paginationProps } = useCollection(
    purchaseOptions,
    {
      pagination: { pageSize: PAGE_SIZE },
      sorting: {},
    },
  );

  return (
    <SpaceBetween size="l">
      <Tabs
        activeTabId={productType}
        onChange={({ detail }) => {
          if (detail.activeTabId === 'AmiProduct') {
            setProductType('AmiProduct');
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

      {productType !== 'AmiProduct' &&
        <Alert type="info">{i18n.productTypeInfoOthers}</Alert>
      }

      {error &&
        <Alert
          type="error"
          action={<Button onClick={onRefresh}>{i18n.errorRetry}</Button>}
        >
          {error.message}
        </Alert>
      }

      <Table
        data-test="purchase-options-table"
        {...collectionProps}
        trackBy="purchaseOptionId"
        columnDefinitions={columnDefinitions}
        items={items}
        loading={isLoading}
        loadingText="Loading purchase options"
        selectionType="single"
        selectedItems={selectedOption ? [selectedOption] : []}
        onSelectionChange={({ detail }) => {
          const opt = detail.selectedItems[0];
          if (opt) { onSelect(opt); }
        }}
        pagination={<Pagination {...paginationProps} />}
        empty={
          <EmptyGridNotification
            title={i18n.emptyPurchaseOptionsTitle}
            subTitle={i18n.emptyPurchaseOptionsSubtitle}
            actionButtonText={i18n.emptyPurchaseOptionsButton}
            actionButtonOnClick={() => window.open(
              i18n.emptyPurchaseOptionsUrl, '_blank', 'noopener,noreferrer',
            )}
          />
        }
        header={
          <Header
            variant="h2"
            counter={`(${purchaseOptions.length})`}
            actions={
              <Button iconName="refresh" onClick={onRefresh} data-test="refresh-purchase-options">
                Refresh
              </Button>
            }
          >
            {i18n.step1Title}
          </Header>
        }
      />

      {selectedOption &&
        <Box>
          <StatusIndicator type="success">
            Selected:
            {' '}
            {selectedOption.productName || selectedOption.offerId}
          </StatusIndicator>
        </Box>
      }
    </SpaceBetween>
  );
};
