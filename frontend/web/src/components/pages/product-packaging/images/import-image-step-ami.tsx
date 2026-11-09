import {
  Alert,
  Badge,
  Container,
  Header,
  SpaceBetween,
  StatusIndicator,
  Table,
} from '@cloudscape-design/components';
import { FC } from 'react';
import {
  DiscoveredMarketplaceSubscription as MarketplaceSubscription,
  ImportableAmi,
} from '../../../../services/API/proserve-wb-packaging-api';
import { ImageSource } from './import-image-wizard.logic';
import { i18n } from './import-image-wizard.translations';

const FIRST_ITEM_INDEX = 0;

interface Props {
  imageSource: ImageSource,
  importableAmis: ImportableAmi[],
  loadingAmis: boolean,
  selectedAmi: ImportableAmi | null,
  setSelectedAmi: (item: ImportableAmi | null) => void,
  subscriptions: MarketplaceSubscription[],
  loadingSubscriptions: boolean,
  selectedSubscription: MarketplaceSubscription | null,
  handleSubscriptionSelection: (item: MarketplaceSubscription) => void,
}

export const ImportImageStepAmi: FC<Props> = ({
  imageSource,
  importableAmis,
  loadingAmis,
  selectedAmi,
  setSelectedAmi,
  subscriptions,
  loadingSubscriptions,
  selectedSubscription,
  handleSubscriptionSelection,
}) => {
  if (imageSource === 'EXISTING_AMI') {
    return (
      <Container header={<Header variant="h2">{i18n.amiDetailsHeader}</Header>}>
        <Table
          data-test="importable-amis-table"
          loading={loadingAmis}
          items={importableAmis}
          selectedItems={selectedAmi ? [selectedAmi] : []}
          onSelectionChange={({ detail }) => setSelectedAmi(detail.selectedItems[FIRST_ITEM_INDEX] || null)}
          selectionType="single"
          trackBy="amiId"
          columnDefinitions={[
            { id: 'amiId', header: 'AMI ID', cell: (item) => item.amiId },
            { id: 'name', header: 'Name', cell: (item) => item.name },
            { id: 'platform', header: 'Platform', cell: (item) => item.platform },
            { id: 'architecture', header: 'Architecture', cell: (item) => item.architecture },
          ]}
          header={
            <Header counter={`(${importableAmis.length})`}>
              Available AMIs from Image Service account
            </Header>
          }
          empty="No importable AMIs found in the Image Service account."
        />
      </Container>
    );
  }

  return (
    <Container header={<Header variant="h2">{i18n.marketplaceSubscriptionsHeader}</Header>}>
      <SpaceBetween size="m">
        <Alert type="info">{i18n.marketplaceAlert}</Alert>
        <Table
          data-test="subscription-table"
          loading={loadingSubscriptions}
          items={subscriptions}
          selectedItems={selectedSubscription ? [selectedSubscription] : []}
          onSelectionChange={({ detail }) => {
            const item = detail.selectedItems[FIRST_ITEM_INDEX];
            handleSubscriptionSelection(item);
          }}
          selectionType="single"
          isItemDisabled={(item) => item.alreadyImported === true}
          columnDefinitions={[
            {
              id: 'productName',
              header: i18n.columnProductName,
              cell: (item) => item.productName,
            },
            {
              id: 'subscriptionOwnership',
              header: i18n.columnType,
              cell: (item) =>
                <Badge color={item.subscriptionOwnership === 'VEW_MANAGED' ? 'green' : 'blue'}>
                  {item.subscriptionOwnership}
                </Badge>
              ,
            },
            {
              id: 'alreadyImported',
              header: i18n.columnStatus,
              cell: (item) =>
                item.alreadyImported
                  ? <StatusIndicator type="success">{i18n.statusImported}</StatusIndicator>
                  : <StatusIndicator type="pending">{i18n.statusAvailable}</StatusIndicator>,
            },
          ]}
          header={
            <Header counter={`(${subscriptions.length})`}>
              {i18n.availableSubscriptionsHeader}
            </Header>
          }
        />
        {selectedSubscription?.subscriptionOwnership === 'EXTERNALLY_MANAGED' &&
          <Alert type="warning" data-test="externally-managed-alert">
            {i18n.externallyManagedAlert}
          </Alert>
        }
      </SpaceBetween>
    </Container>
  );
};
