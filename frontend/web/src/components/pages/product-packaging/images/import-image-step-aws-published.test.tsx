// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// The AWS-published step renders what the backend resolved: one AMI as a
// summary, several as a picker, and a failure as the backend's own message.

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ImportImageStepAwsPublished } from './import-image-step-aws-published';
import { i18n } from './import-image-wizard.translations';
import { ResolveAwsPublishedAmiResponse } from
  '../../../../services/API/aws-published-ami-api';

const x86 = {
  amiId: 'ami-x86',
  amiName: 'Windows_Server-2025-x86',
  ownerId: 'ownerid1234',
  architecture: 'x86_64',
  platformDetails: 'Windows',
  region: 'eu-west-1',
};

const arm = {
  amiId: 'ami-arm',
  amiName: 'Windows_Server-2025-arm',
  ownerId: 'ownerid1234',
  architecture: 'arm64',
  platformDetails: 'Windows',
  region: 'eu-west-1',
};

const resolution: ResolveAwsPublishedAmiResponse = {
  listingId: 'prodview-win2025',
  productId: 'prod-win2025',
  productName: 'Microsoft Windows Server 2025 Base',
  region: 'eu-west-1',
  unambiguous: true,
  resolved: x86,
  candidates: [],
  alreadyImportedAmiIds: [],
};

const renderStep = (props: Partial<
  React.ComponentProps<typeof ImportImageStepAwsPublished>
> = {}) => render(
  <ImportImageStepAwsPublished
    resolution={resolution}
    resolveError={null}
    isResolving={false}
    candidates={[x86]}
    selectedCandidate={x86}
    onSelectCandidate={vi.fn()}
    {...props}
  />,
);

describe('ImportImageStepAwsPublished', () => {
  it('shows what was resolved', () => {
    renderStep();
    expect(screen.getByText('Microsoft Windows Server 2025 Base')).toBeInTheDocument();
    expect(screen.getByText('ami-x86')).toBeInTheDocument();
    expect(screen.getByText('eu-west-1')).toBeInTheDocument();
  });

  it('does not ask the user to choose when only one AMI was resolved', () => {
    renderStep();
    expect(screen.queryByText(i18n.awsPublishedAmbiguous)).toBeNull();
  });

  it('asks the user to choose when several AMIs are offered', () => {
    // The backend only returns several when it cannot tell which is wanted;
    // they differ by architecture.
    renderStep({
      resolution: { ...resolution, unambiguous: false, resolved: undefined, candidates: [x86, arm] },
      candidates: [x86, arm],
      selectedCandidate: null,
    });
    expect(screen.getByText(i18n.awsPublishedAmbiguous)).toBeInTheDocument();
    expect(screen.getByText('ami-x86')).toBeInTheDocument();
    expect(screen.getByText('ami-arm')).toBeInTheDocument();
    expect(screen.getByText('arm64')).toBeInTheDocument();
  });

  it('shows the backend message when the listing could not be resolved', () => {
    renderStep({
      resolution: null,
      resolveError: 'No AMI could be identified for product prod-x.',
      candidates: [],
      selectedCandidate: null,
    });
    expect(screen.getByText('No AMI could be identified for product prod-x.'))
      .toBeInTheDocument();
    expect(screen.getByText(i18n.awsPublishedResolveFailedHeader)).toBeInTheDocument();
    // No picker to interact with when nothing resolved.
    expect(screen.queryByText(i18n.awsPublishedColumnAmiId)).toBeNull();
  });

  it('marks an AMI that is already imported', () => {
    renderStep({
      resolution: { ...resolution, alreadyImportedAmiIds: ['ami-x86'] },
      selectedCandidate: null,
    });
    expect(screen.getByText(i18n.awsPublishedStatusImported)).toBeInTheDocument();
  });

  it('shows progress while the listing is being resolved', () => {
    renderStep({ isResolving: true });
    expect(screen.getByText(i18n.awsPublishedResolving)).toBeInTheDocument();
  });
});
