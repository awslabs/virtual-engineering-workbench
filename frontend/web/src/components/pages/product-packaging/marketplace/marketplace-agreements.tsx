import {
  Badge,
  Box,
  Button,
  Header,
  Link,
  Modal,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
} from '@cloudscape-design/components';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { FC, useState } from 'react';
import {
  ListMarketplaceAgreementsResponse,
  MarketplaceAgreementResponseItem,
} from '../../../../services/API/proserve-wb-packaging-api';
import { useListMarketplaceAgreements } from
  '../../../../hooks/packaging/use-list-marketplace-agreements.logic';
import { useCancelMarketplaceAgreement } from
  '../../../../hooks/packaging/use-cancel-marketplace-agreement.logic';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { BreadcrumbItem } from '../../../layout';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { EmptyGridNotification } from '../../shared';
import { i18n } from './marketplace-agreements.translations';

const PAGE_SIZE = 20;

const MARKETPLACE_PRODUCT_URL = (productId: string) =>
  `https://aws.amazon.com/marketplace/pp/prodview-${encodeURIComponent(productId)}`;

interface ServiceAPI {
  listMarketplaceAgreements: () => Promise<ListMarketplaceAgreementsResponse>,
}

interface MarketplaceAgreementsProps {
  serviceApi: ServiceAPI,
}

/**
 * Map an AWS Marketplace agreement status to a Cloudscape Badge colour.
 *
 * AWS's SearchAgreements can return any of these statuses; keeping the mapping
 * explicit lets us reserve the fallback `grey` for genuinely-unknown values instead of
 * mis-representing an EXPIRED agreement as "unknown state".
 *
 * `severity-medium` is used for ENDING_SOON because Cloudscape's `Badge` component
 * doesn't expose a plain 'yellow' — the severity palette is the closest equivalent.
 */
type AgreementBadgeColor =
  | 'green' | 'blue' | 'red' | 'grey' | 'severity-medium';

const statusColor = (status: string): AgreementBadgeColor => {
  const s = status.toUpperCase();
  switch (s) {
    case 'ACTIVE':
      return 'green';
    case 'RENEWED':
      return 'blue';
    case 'PENDING_ACCEPTANCE':
    case 'RENEWAL_REQUESTED':
      return 'grey';
    case 'ENDING_SOON':
      return 'severity-medium';
    case 'EXPIRED':
    case 'SUPERSEDED':
    case 'TERMINATED':
    case 'CANCELLED':
    case 'CANCELED':
      return 'red';
    default:
      return 'grey';
  }
};

const MarketplaceAgreements: FC<MarketplaceAgreementsProps> = ({ serviceApi }) => {
  const { navigateTo } = useNavigationPaths();

  // No project in scope here: Marketplace agreements are account-level AWS
  // resources, so this page lists the buyer account's agreements regardless of
  // which project is selected.
  const { data: agreements, isLoading, run: refresh } = useListMarketplaceAgreements({
    serviceApi,
  });

  const cancelMutation = useCancelMarketplaceAgreement();

  const [confirmTarget, setConfirmTarget] = useState<MarketplaceAgreementResponseItem | null>(null);

  const doCancel = async () => {
    if (!confirmTarget) { return; }
    // `cancelMutation.run` catches its own errors (and surfaces them via a notification),
    // then returns null on failure. If we always closed the modal + refreshed we'd
    // signal success to the user even when nothing was cancelled — hence the guard.
    const result = await cancelMutation.run(confirmTarget.agreementId);
    if (result !== null) {
      setConfirmTarget(null);
      refresh();
    }
  };

  const columnDefinitions: TableProps.ColumnDefinition<MarketplaceAgreementResponseItem>[] = [
    {
      id: 'agreementId',
      header: i18n.columnAgreementId,
      cell: (item) => item.agreementId,
      sortingField: 'agreementId',
    },
    {
      id: 'product',
      header: i18n.columnProduct,
      // Prefer the human-readable productName if the server enriched it;
      // fall back to the raw productId (still a Marketplace product link)
      // when enrichment failed. Show the raw id underneath as small text
      // so support / debugging keeps its handle even in the happy path.
      cell: (item) =>
        <SpaceBetween size="xxs">
          <Link external href={MARKETPLACE_PRODUCT_URL(item.productId)}>
            {item.productName || item.productId}
          </Link>
          {item.productName ?
            <Box variant="small" color="text-body-secondary">{item.productId}</Box>
            : null}
        </SpaceBetween>
      ,
      sortingField: 'productName',
    },
    {
      id: 'offer',
      header: i18n.columnOffer,
      cell: (item) =>
        <SpaceBetween size="xxs">
          <Box variant="span">{item.offerName || item.offerId}</Box>
          {item.offerName ?
            <Box variant="small" color="text-body-secondary">{item.offerId}</Box>
            : null}
        </SpaceBetween>
      ,
      sortingField: 'offerName',
    },
    {
      id: 'pricing',
      header: i18n.columnPricing,
      cell: (item) =>
        item.pricingModelType
          ? <Badge color="blue">{item.pricingModelType}</Badge>
          : <Box variant="span" color="text-body-secondary">—</Box>
      ,
      sortingField: 'pricingModelType',
    },
    {
      id: 'status',
      header: i18n.columnStatus,
      cell: (item) =>
        <Badge color={statusColor(item.status)}>{item.status}</Badge>
      ,
      sortingField: 'status',
    },
    {
      id: 'acceptanceDate',
      header: i18n.columnAcceptanceDate,
      cell: (item) => item.acceptanceDate || '—',
      sortingField: 'acceptanceDate',
    },
    {
      id: 'actions',
      header: i18n.columnActions,
      cell: (item) =>
        <Button
          onClick={() => setConfirmTarget(item)}
          data-test={`cancel-btn-${item.agreementId}`}
          disabled={item.status.toUpperCase() !== 'ACTIVE'}
        >
          {i18n.cancelButton}
        </Button>
      ,
    },
  ];

  const { items, collectionProps, paginationProps } = useCollection(
    agreements,
    {
      sorting: {},
      pagination: { pageSize: PAGE_SIZE },
    },
  );

  const breadcrumbItems: BreadcrumbItem[] = [
    { path: 'Marketplace', href: '#' },
    { path: i18n.header, href: '#' },
  ];

  return (
    <WorkbenchAppLayout
      breadcrumbItems={breadcrumbItems}
      contentType="default"
      content={
        <>
          <Modal
            visible={confirmTarget !== null}
            onDismiss={() => setConfirmTarget(null)}
            header={i18n.cancelModalHeader}
            footer={
              <Box float="right">
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={() => setConfirmTarget(null)}>{i18n.cancelModalDismiss}</Button>
                  <Button
                    variant="primary"
                    onClick={doCancel}
                    loading={cancelMutation.isLoading}
                    data-test="confirm-cancel-agreement"
                  >
                    {i18n.cancelModalConfirm}
                  </Button>
                </SpaceBetween>
              </Box>
            }
          >
            <Box variant="p">{i18n.cancelModalBody}</Box>
            {confirmTarget &&
              <Box variant="code">{confirmTarget.agreementId}</Box>
            }
          </Modal>

          <Table
            data-test="marketplace-agreements-table"
            {...collectionProps}
            trackBy="agreementId"
            columnDefinitions={columnDefinitions}
            items={items}
            loading={isLoading}
            loadingText="Loading agreements"
            pagination={<Pagination {...paginationProps} />}
            empty={
              <EmptyGridNotification
                title={i18n.emptyTitle}
                subTitle={i18n.emptySubtitle}
              />
            }
            header={
              <Header
                variant="h1"
                counter={`(${agreements.length})`}
                description={i18n.description}
                actions={
                  <SpaceBetween direction="horizontal" size="xs">
                    <Button
                      iconName="refresh"
                      onClick={refresh}
                      data-test="refresh-agreements-btn"
                    >
                      {i18n.refreshButton}
                    </Button>
                    <Button
                      variant="primary"
                      onClick={() => navigateTo(RouteNames.MarketplaceProcurementWizard)}
                      data-test="procure-agreement-btn"
                    >
                      {i18n.procureButton}
                    </Button>
                  </SpaceBetween>
                }
              >
                {i18n.header}
              </Header>
            }
          />
        </>
      }
    />
  );
};

export { MarketplaceAgreements };
