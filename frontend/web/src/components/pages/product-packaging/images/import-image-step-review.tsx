import {
  Alert, Box, Button, ColumnLayout, Container, Header,
  SpaceBetween, Table,
} from '@cloudscape-design/components';
import { FC } from 'react';
import {
  ComponentVersionDetailInput as ComponentVersionDetail,
  DiscoveredMarketplaceSubscription as MarketplaceSubscription,
} from '../../../../services/API/proserve-wb-packaging-api';
import { ImageSource } from './import-image-wizard.logic';
import { i18n } from './import-image-wizard.translations';

interface Props {
  imageSource: ImageSource,
  amiId: string,
  selectedSubscription: MarketplaceSubscription | null,
  imageName: string,
  platform: string,
  osVersion: string,
  componentVersionDetails: ComponentVersionDetail[],
  setActiveStepIndex: (index: number) => void,
}

const STEP_SOURCE = 0;
const STEP_AMI = 1;
const STEP_DETAILS = 2;
const STEP_PLATFORM = 3;
const STEP_SOFTWARE = 4;

export const ImportImageStepReview: FC<Props> = ({
  imageSource, amiId, selectedSubscription, imageName,
  platform, osVersion, componentVersionDetails, setActiveStepIndex,
}) => {
  const editButton = (step: number) =>
    <Button onClick={() => setActiveStepIndex(step)}>Edit</Button>;

  return (
    <SpaceBetween size="l">
      {imageSource === 'MARKETPLACE_PRODUCT'
        && selectedSubscription?.subscriptionOwnership === 'EXTERNALLY_MANAGED' &&
        <Alert type="warning" data-test="externally-managed-alert-review">
          {i18n.externallyManagedAlert}
        </Alert>
      }
      <Container header={
        <Header variant="h3" actions={editButton(STEP_SOURCE)}>
          {`Step 1: ${i18n.step1Title}`}
        </Header>
      }>
        <ColumnLayout columns={2} variant="text-grid">
          <Box variant="awsui-key-label">{i18n.reviewSource}</Box>
          <Box>{imageSource}</Box>
        </ColumnLayout>
      </Container>

      <Container header={
        <Header variant="h3" actions={editButton(STEP_AMI)}>
          {`Step 2: ${i18n.step2TitleAmi}`}
        </Header>
      }>
        <ColumnLayout columns={2} variant="text-grid">
          <Box variant="awsui-key-label">{i18n.reviewAmiId}</Box>
          <Box>
            {imageSource === 'MARKETPLACE_PRODUCT'
              ? selectedSubscription?.hubRegionAmiId : amiId}
          </Box>
        </ColumnLayout>
      </Container>

      <Container header={
        <Header variant="h3" actions={editButton(STEP_DETAILS)}>
          {`Step 3: ${i18n.step3Title}`}
        </Header>
      }>
        <ColumnLayout columns={2} variant="text-grid">
          <Box variant="awsui-key-label">{i18n.reviewImageName}</Box>
          <Box>{imageName}</Box>
        </ColumnLayout>
      </Container>

      <Container header={
        <Header variant="h3" actions={editButton(STEP_PLATFORM)}>
          {`Step 4: ${i18n.step4Title}`}
        </Header>
      }>
        <ColumnLayout columns={2} variant="text-grid">
          <SpaceBetween size="s">
            <Box variant="awsui-key-label">{i18n.reviewPlatform}</Box>
            <Box>{platform}</Box>
          </SpaceBetween>
          <SpaceBetween size="s">
            <Box variant="awsui-key-label">{i18n.reviewOsVersion}</Box>
            <Box>{osVersion}</Box>
          </SpaceBetween>
        </ColumnLayout>
      </Container>

      <Container header={
        <Header variant="h3" actions={editButton(STEP_SOFTWARE)}>
          {`Step 5: ${i18n.step5Title}`}
        </Header>
      }>
        <Table
          items={componentVersionDetails.filter(c => c.softwareName || c.softwareVersion)}
          columnDefinitions={[
            { id: 'name', header: i18n.softwareNameLabel, cell: (c) => c.softwareName },
            { id: 'vendor', header: i18n.softwareVendorLabel, cell: (c) => c.softwareVendor },
            { id: 'version', header: i18n.softwareVersionLabel, cell: (c) => c.softwareVersion },
          ]}
          variant="embedded"
        />
      </Container>
    </SpaceBetween>
  );
};
