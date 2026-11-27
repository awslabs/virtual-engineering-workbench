// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// Import Image wizard — the AWS_PUBLISHED_AMI source.
//
// Entry is ?source=aws-published&listingId=<id>. The step resolves the
// listing to an AMI, preselects it when the backend identified exactly one,
// waits for the user when several are offered, and blocks progress with the
// backend's own message when nothing resolves. The import itself goes
// through the shared importImage, and must carry
// marketplaceMetadata.listingId or the backend refuses it.

import React from 'react';
import { renderHook, waitFor, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useImportImageWizard } from './import-image-wizard.logic';
import { selectedProjectState } from '../../../../state';
import { ResolveAwsPublishedAmiResponse } from
  '../../../../services/API/aws-published-ami-api';

const NO_DEDUPING = 0;
const STEP_SOURCE = 0;
const STEP_AMI = 1;
const NONE = 0;
const TWO_CANDIDATES = 2;
const FIRST_CALL = 0;
const SECOND_ARG = 1;
const SINGLE_CALL = 1;

const AWS_PUBLISHED_ENTRY =
  '/projects/proj-1/images/import?source=aws-published&listingId=prodview-win2025';

const mockServiceApi = {
  importImage: vi.fn(),
  discoverMarketplaceSubscriptions: vi.fn().mockResolvedValue({ subscriptions: [] }),
  listImportableAmis: vi.fn().mockResolvedValue({ amis: [] }),
};

const x86 = {
  amiId: 'ami-x86',
  amiName: 'Windows_Server-2025-English-Full-Base-x86',
  ownerId: 'ownerid1234',
  architecture: 'x86_64',
  platformDetails: 'Windows',
  region: 'eu-west-1',
};

const arm = {
  amiId: 'ami-arm',
  amiName: 'Windows_Server-2025-English-Full-Base-arm',
  ownerId: 'ownerid1234',
  architecture: 'arm64',
  platformDetails: 'Windows',
  region: 'eu-west-1',
};

const unambiguousResolution: ResolveAwsPublishedAmiResponse = {
  listingId: 'prodview-win2025',
  productId: 'prod-win2025',
  productName: 'Microsoft Windows Server 2025 Base',
  region: 'eu-west-1',
  unambiguous: true,
  resolved: x86,
  candidates: [],
  alreadyImportedAmiIds: [],
};

const ambiguousResolution: ResolveAwsPublishedAmiResponse = {
  ...unambiguousResolution,
  unambiguous: false,
  resolved: undefined,
  candidates: [x86, arm],
};

let awsPublishedApi: {
  resolveAwsPublishedAmi: ReturnType<typeof vi.fn<
    (projectId: string, listingId: string) => Promise<ResolveAwsPublishedAmiResponse>
  >>,
};

beforeEach(() => {
  awsPublishedApi = {
    resolveAwsPublishedAmi: vi.fn().mockResolvedValue(unambiguousResolution),
  };
  // Shared across the file, so reset per test: the import assertions read the
  // first recorded call.
  mockServiceApi.importImage.mockReset();
  mockServiceApi.importImage.mockResolvedValue({ imageId: 'img-1' });
});

const makeWrapper = (initialEntries: string[]) => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId: 'proj-1', projectName: 'Test' });
  };
  return ({ children }: { children: React.ReactNode }) =>
    <MemoryRouter initialEntries={initialEntries}>
      <RecoilRoot initializeState={initializeState}>
        <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
          {children}
        </SWRConfig>
      </RecoilRoot>
    </MemoryRouter>
  ;
};

const renderWizard = (entry = AWS_PUBLISHED_ENTRY) => renderHook(
  () => useImportImageWizard({ serviceApi: mockServiceApi, awsPublishedApi }),
  { wrapper: makeWrapper([entry]) },
);

describe('AWS-published entry point', () => {
  it('opens on the AMI step with the AWS_PUBLISHED_AMI source', () => {
    const { result } = renderWizard();
    expect(result.current.activeStepIndex).toBe(STEP_AMI);
    expect(result.current.imageSource).toBe('AWS_PUBLISHED_AMI');
    expect(result.current.awsListingId).toBe('prodview-win2025');
  });

  it('ignores a malformed listing id instead of resolving it', () => {
    // Nothing from the URL reaches the API unless it is well formed.
    const { result } = renderWizard(
      '/projects/proj-1/images/import?source=aws-published&listingId=not-a-listing',
    );
    expect(result.current.imageSource).toBe('EXISTING_AMI');
    expect(result.current.activeStepIndex).toBe(STEP_SOURCE);
    expect(result.current.awsListingId).toBeNull();
    expect(awsPublishedApi.resolveAwsPublishedAmi).not.toHaveBeenCalled();
  });

  it('leaves the post-purchase Marketplace hand-off working', () => {
    // The two entry points share the `source` param; a marketplace link must
    // still select the subscription picker.
    const { result } = renderWizard(
      '/projects/proj-1/images/import?source=marketplace&productId=prod-abc123',
    );
    expect(result.current.imageSource).toBe('MARKETPLACE_PRODUCT');
    expect(awsPublishedApi.resolveAwsPublishedAmi).not.toHaveBeenCalled();
  });
});

describe('a listing that resolves to one AMI', () => {
  it('resolves the listing and preselects the AMI', async () => {
    const { result } = renderWizard();

    await waitFor(() => {
      expect(result.current.selectedAwsCandidate?.amiId).toBe('ami-x86');
    });
    expect(awsPublishedApi.resolveAwsPublishedAmi)
      .toHaveBeenCalledWith('proj-1', 'prodview-win2025');
    expect(result.current.awsResolution?.productName)
      .toBe('Microsoft Windows Server 2025 Base');
    expect(result.current.awsResolveError).toBeNull();
  });

  it('offers only the resolved AMI and allows the step to proceed', async () => {
    const { result } = renderWizard();
    await waitFor(() => {
      expect(result.current.awsCandidates.length).toBeGreaterThan(NONE);
    });
    expect(result.current.awsCandidates.map((c) => c.amiId)).toEqual(['ami-x86']);
    expect(result.current.canProceedFromStep(STEP_AMI)).toBe(true);
  });

  it('fills in the product name and platform for the later steps', async () => {
    const { result } = renderWizard();
    await waitFor(() => {
      expect(result.current.imageName).toBe('Microsoft Windows Server 2025 Base');
    });
    expect(result.current.platform).toBe('Windows');
  });

  it('does not preselect an AMI that is already imported', async () => {
    awsPublishedApi.resolveAwsPublishedAmi.mockResolvedValue({
      ...unambiguousResolution,
      alreadyImportedAmiIds: ['ami-x86'],
    });
    const { result } = renderWizard();

    await waitFor(() => {
      expect(result.current.awsResolution).not.toBeNull();
    });
    expect(result.current.selectedAwsCandidate).toBeNull();
    expect(result.current.canProceedFromStep(STEP_AMI)).toBe(false);
  });
});

describe('a listing that resolves to several AMIs', () => {
  beforeEach(() => {
    awsPublishedApi.resolveAwsPublishedAmi.mockResolvedValue(ambiguousResolution);
  });

  it('offers every candidate and selects none of them', async () => {
    // The candidates differ by architecture, so guessing would import the
    // wrong image.
    const { result } = renderWizard();

    await waitFor(() => {
      expect(result.current.awsCandidates.length).toBe(TWO_CANDIDATES);
    });
    expect(result.current.awsCandidates.map((c) => c.amiId))
      .toEqual(['ami-x86', 'ami-arm']);
    expect(result.current.selectedAwsCandidate).toBeNull();
  });

  it('blocks the step until the user chooses', async () => {
    const { result } = renderWizard();
    await waitFor(() => {
      expect(result.current.awsCandidates.length).toBe(TWO_CANDIDATES);
    });
    expect(result.current.canProceedFromStep(STEP_AMI)).toBe(false);

    act(() => {
      result.current.handleAwsCandidateSelection(arm);
    });

    await waitFor(() => {
      expect(result.current.selectedAwsCandidate?.amiId).toBe('ami-arm');
    });
    expect(result.current.canProceedFromStep(STEP_AMI)).toBe(true);
  });

  it('names the image after the chosen AMI, which is what distinguishes it', async () => {
    const { result } = renderWizard();
    await waitFor(() => {
      expect(result.current.awsCandidates.length).toBe(TWO_CANDIDATES);
    });
    act(() => {
      result.current.handleAwsCandidateSelection(arm);
    });
    await waitFor(() => {
      expect(result.current.imageName).toBe(arm.amiName);
    });
  });

  it('refuses a candidate that is already imported', async () => {
    awsPublishedApi.resolveAwsPublishedAmi.mockResolvedValue({
      ...ambiguousResolution,
      alreadyImportedAmiIds: ['ami-arm'],
    });
    const { result } = renderWizard();
    await waitFor(() => {
      expect(result.current.awsCandidates.length).toBe(TWO_CANDIDATES);
    });

    act(() => {
      result.current.handleAwsCandidateSelection(arm);
    });

    expect(result.current.selectedAwsCandidate).toBeNull();
    expect(result.current.canProceedFromStep(STEP_AMI)).toBe(false);
  });
});

describe('a listing that cannot be resolved', () => {
  it('surfaces the backend message and blocks progress', async () => {
    // Listings that need a Marketplace subscription first land here; the
    // backend's message is the only thing that explains why.
    awsPublishedApi.resolveAwsPublishedAmi.mockRejectedValue(
      new Error('No AMI could be identified for product prod-x.'),
    );
    const { result } = renderWizard();

    await waitFor(() => {
      expect(result.current.awsResolveError)
        .toBe('No AMI could be identified for product prod-x.');
    });
    expect(result.current.awsResolution).toBeNull();
    expect(result.current.awsCandidates).toEqual([]);
    expect(result.current.canProceedFromStep(STEP_AMI)).toBe(false);
  });

  it('reports the source as unavailable when no client is wired in', async () => {
    const { result } = renderHook(
      () => useImportImageWizard({ serviceApi: mockServiceApi }),
      { wrapper: makeWrapper([AWS_PUBLISHED_ENTRY]) },
    );
    await waitFor(() => {
      expect(result.current.awsResolveError).toBeTruthy();
    });
    expect(result.current.canProceedFromStep(STEP_AMI)).toBe(false);
  });
});

describe('the import request', () => {
  it('carries marketplaceMetadata.listingId and the chosen AMI id', async () => {
    // The backend resolves the listing again and accepts the AMI id only if
    // that resolution offers it, so both have to be on the request.
    const { result } = renderWizard();
    await waitFor(() => {
      expect(result.current.selectedAwsCandidate?.amiId).toBe('ami-x86');
    });

    await act(async () => {
      await result.current.handleSubmit();
    });

    expect(mockServiceApi.importImage).toHaveBeenCalled();
    const [projectId, body] =
      mockServiceApi.importImage.mock.calls[FIRST_CALL];
    expect(projectId).toBe('proj-1');
    expect(body.marketplaceMetadata.listingId).toBe('prodview-win2025');
    expect(body.amiId).toBe('ami-x86');
    expect(body.imageSource).toBe('AWS_PUBLISHED_AMI');
  });

  it('goes through the same importImage as every other source, once', async () => {
    // There is no separate AWS-published import path any more: the generated
    // serialiser carries listingId, so this source submits like the rest.
    const { result } = renderWizard();
    await waitFor(() => {
      expect(result.current.selectedAwsCandidate?.amiId).toBe('ami-x86');
    });

    await act(async () => {
      await result.current.handleSubmit();
    });

    expect(mockServiceApi.importImage).toHaveBeenCalledTimes(SINGLE_CALL);
  });

  it('sends only the listing and the schema-required product code', async () => {
    // productCode is mandatory in the request schema but derived server-side
    // for this source; the rest of the metadata is never taken from the caller.
    const { result } = renderWizard();
    await waitFor(() => {
      expect(result.current.selectedAwsCandidate?.amiId).toBe('ami-x86');
    });

    await act(async () => {
      await result.current.handleSubmit();
    });

    const body = mockServiceApi.importImage
      .mock.calls[FIRST_CALL][SECOND_ARG];
    expect(body.marketplaceMetadata).toEqual({
      listingId: 'prodview-win2025',
      productCode: '',
    });
  });

  it('refuses to submit when no listing id reached the wizard', async () => {
    // Nothing resolves without one, so the backend would refuse the import.
    const { result } = renderWizard('/projects/proj-1/images/import');
    act(() => {
      result.current.setImageSource('AWS_PUBLISHED_AMI');
    });

    await act(async () => {
      await result.current.handleSubmit();
    });

    expect(mockServiceApi.importImage).not.toHaveBeenCalled();
  });

  it('refuses to submit when no client is wired in', async () => {
    const { result } = renderHook(
      () => useImportImageWizard({ serviceApi: mockServiceApi }),
      { wrapper: makeWrapper([AWS_PUBLISHED_ENTRY]) },
    );

    await act(async () => {
      await result.current.handleSubmit();
    });

    expect(mockServiceApi.importImage).not.toHaveBeenCalled();
  });
});
