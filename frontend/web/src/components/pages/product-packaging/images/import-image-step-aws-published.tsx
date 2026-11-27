// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import {
  Alert,
  Box,
  Container,
  Header,
  SpaceBetween,
  Spinner,
  Table,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { AwsPublishedAmiCandidate, ResolveAwsPublishedAmiResponse } from
  '../../../../services/API/aws-published-ami-api';
import { i18n } from './import-image-wizard.translations';

const SINGLE_CANDIDATE = 1;
const NOT_AVAILABLE = '—';

interface Props {
  resolution: ResolveAwsPublishedAmiResponse | null,
  resolveError: string | null,
  isResolving: boolean,
  candidates: AwsPublishedAmiCandidate[],
  selectedCandidate: AwsPublishedAmiCandidate | null,
  onSelectCandidate: (item: AwsPublishedAmiCandidate) => void,
}

/**
 * What the backend resolved for an AWS-published listing.
 *
 * One AMI is shown as a read-only summary; several are shown as a picker,
 * because the backend only returns several when it cannot tell which the user
 * wants (they differ by architecture). When nothing resolves, the backend's
 * own message is shown and the wizard cannot advance.
 */
export const ImportImageStepAwsPublished: FC<Props> = ({
  resolution,
  resolveError,
  isResolving,
  candidates,
  selectedCandidate,
  onSelectCandidate,
}) => {
  if (isResolving) {
    return (
      <Container header={<Header variant="h2">{i18n.awsPublishedHeader}</Header>}>
        <Box textAlign="center" data-test="aws-published-loading">
          <Spinner /> {i18n.awsPublishedResolving}
        </Box>
      </Container>
    );
  }

  if (resolveError) {
    return (
      <Container header={<Header variant="h2">{i18n.awsPublishedHeader}</Header>}>
        <Alert
          type="error"
          header={i18n.awsPublishedResolveFailedHeader}
          data-test="aws-published-error"
        >
          {resolveError}
        </Alert>
      </Container>
    );
  }

  const alreadyImported = new Set(resolution?.alreadyImportedAmiIds || []);
  const needsChoice = candidates.length > SINGLE_CANDIDATE;

  return (
    <Container header={<Header variant="h2">{i18n.awsPublishedHeader}</Header>}>
      <SpaceBetween size="m">
        <Alert type="info" data-test="aws-published-alert">
          {i18n.awsPublishedAlert}
        </Alert>

        <Box variant="p">
          <strong>{i18n.awsPublishedProductLabel}:</strong>{' '}
          <span data-test="aws-published-product">
            {resolution?.productName || NOT_AVAILABLE}
          </span>
        </Box>
        <Box variant="p">
          <strong>{i18n.awsPublishedRegionLabel}:</strong>{' '}
          {resolution?.region || NOT_AVAILABLE}
        </Box>

        {needsChoice &&
          <Alert type="warning" data-test="aws-published-ambiguous">
            {i18n.awsPublishedAmbiguous}
          </Alert>
        }

        <Table
          data-test="aws-published-candidates-table"
          variant="embedded"
          selectionType="single"
          trackBy="amiId"
          selectedItems={selectedCandidate ? [selectedCandidate] : []}
          onSelectionChange={({ detail }) => {
            const item = detail.selectedItems[0];
            if (item) { onSelectCandidate(item); }
          }}
          isItemDisabled={(item) => alreadyImported.has(item.amiId)}
          items={candidates}
          loadingText={i18n.awsPublishedResolving}
          columnDefinitions={[
            {
              id: 'amiId',
              header: i18n.awsPublishedColumnAmiId,
              cell: (item) => item.amiId,
            },
            {
              id: 'amiName',
              header: i18n.awsPublishedColumnAmiName,
              cell: (item) => item.amiName,
            },
            {
              id: 'architecture',
              header: i18n.awsPublishedColumnArchitecture,
              cell: (item) => item.architecture || NOT_AVAILABLE,
            },
            {
              id: 'ownerId',
              header: i18n.awsPublishedColumnOwner,
              cell: (item) => item.ownerId,
            },
            {
              id: 'status',
              header: i18n.awsPublishedColumnStatus,
              cell: (item) => alreadyImported.has(item.amiId)
                ? i18n.awsPublishedStatusImported
                : i18n.awsPublishedStatusAvailable,
            },
          ]}
          empty={(
            <Box textAlign="center" data-test="aws-published-empty">
              {i18n.awsPublishedEmpty}
            </Box>
          )}
        />
      </SpaceBetween>
    </Container>
  );
};
