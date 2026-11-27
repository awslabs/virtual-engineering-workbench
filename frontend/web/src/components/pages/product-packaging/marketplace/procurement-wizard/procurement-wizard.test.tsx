// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi } from 'vitest';
import { ProcurementWizard } from './procurement-wizard';
import { i18n } from './procurement-wizard.translations';
import { AWS_SELLER_PROFILE_ID } from './offer-helpers';
import { selectedProjectState } from '../../../../../state';

const NO_DEDUPING = 0;
const TWO = 2;

// Mock the procurement API wrapper so no real network is hit.
vi.mock('../../../../../services/API/marketplace-procurement-api', async () => {
  const actual = await vi.importActual<typeof import(
    '../../../../../services/API/marketplace-procurement-api'
  )>('../../../../../services/API/marketplace-procurement-api');
  return {
    ...actual,
    marketplaceProcurementAPI: {
      listPurchaseOptions: vi.fn().mockResolvedValue({ purchaseOptions: [] }),
      getOffer: vi.fn().mockResolvedValue(null),
      createAgreementRequest: vi.fn(),
      acceptAgreementRequest: vi.fn(),
      cancelAgreement: vi.fn(),
    },
  };
});

const renderWizard = () => {
  const initializeState = ({ set }: { set: SetRecoilState }) => {
    set(selectedProjectState, { projectId: 'proj-1' });
  };
  return render(
    <MemoryRouter>
      <RecoilRoot initializeState={initializeState}>
        <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
          <ProcurementWizard />
        </SWRConfig>
      </RecoilRoot>
    </MemoryRouter>,
  );
};

describe('ProcurementWizard', () => {
  it('renders the browse-offers step with the AMI tab active', () => {
    renderWizard();
    // Tab labels: only AMI is enabled; Container and SaaS have "Coming soon".
    expect(screen.getByText(i18n.productTypeTabAmi)).toBeInTheDocument();
    // "Coming soon" badges appear at least twice (Container + SaaS).
    expect(screen.getAllByText(i18n.comingSoonBadge).length).toBeGreaterThanOrEqual(TWO);
  });

  it('renders the localized cancel-prompt strings, not English literals', () => {
    renderWizard();
    // The cancel prompt must read its strings from i18n, not JSX literals.
    expect(i18n.cancelPromptConfirmText).toBe('Cancel procurement');
    expect(i18n.cancelPromptCancelText).toBe('Keep going');
  });
});

// ---------------------------------------------------------------------------
// Offers with no pricing term. AWS sells these products itself, the licence
// comes with the EC2 billing code, and there is no agreement to create — so
// the wizard offers a direct import of the AMI instead of the subscribe
// steps, carrying the listing the user came from.
// ---------------------------------------------------------------------------
describe('ProcurementWizard — offer with no pricing term', () => {
  const awsSoldOffer = {
    offerId: 'offer-aws-sold',
    offerName: 'Microsoft Windows Server 2025 Base',
    pricingModelType: 'FREE',
    sellerOfRecordProfileId: AWS_SELLER_PROFILE_ID,
    sellerOfRecordDisplayName: 'Amazon Web Services',
    associatedProducts: [{ productId: 'prod-windows-2025', productName: 'Windows Server 2025' }],
    // Only metadata terms: this is what makes it a direct import.
    terms: [
      { termId: 't-legal', termType: 'LegalTerm', rawTerm: {} },
      { termId: 't-support', termType: 'SupportTerm', rawTerm: {} },
    ],
  };

  const renderDirectImport = async (
    entry = '/?offerId=offer-aws-sold&listingId=prodview-win2025',
  ) => {
    const api = await import('../../../../../services/API/marketplace-procurement-api');
    vi.mocked(api.marketplaceProcurementAPI.getOffer).mockResolvedValue(
      awsSoldOffer as never,
    );
    const view = render(
      <MemoryRouter initialEntries={[entry]}>
        <RecoilRoot initializeState={({ set }: { set: SetRecoilState }) => {
          set(selectedProjectState, { projectId: 'proj-1' });
        }}
        >
          <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
            <ProcurementWizard />
          </SWRConfig>
        </RecoilRoot>
      </MemoryRouter>,
    );
    await screen.findByText(i18n.directImportTitle);
    return view;
  };

  it('offers an enabled direct-import action instead of the subscribe steps', async () => {
    await renderDirectImport();
    const importButton = screen.getByRole('button', { name: i18n.directImportButton });
    expect(importButton).toBeEnabled();
  });

  it('tells the user no subscription is needed rather than that import is unsupported', async () => {
    await renderDirectImport();
    expect(i18n.directImportAlertHeader).toMatch(/no subscription needed/iu);
    expect(screen.getByText(i18n.directImportAlertHeader)).toBeInTheDocument();
    // The superseded copy promised nothing could be imported; it must be gone.
    expect(screen.queryByText(/cannot be imported/iu)).toBeNull();
    expect(screen.queryByText(/not yet supported/iu)).toBeNull();
  });

  it('disables the import action when the URL carries no usable listing', async () => {
    // Without a listing there is nothing to resolve, so the action must not
    // navigate into a wizard that would immediately fail.
    await renderDirectImport('/?offerId=offer-aws-sold');
    const importButton = screen.getByRole('button', { name: i18n.directImportButton });
    expect(importButton).toBeDisabled();
    expect(screen.getByText(i18n.directImportNoListing)).toBeInTheDocument();
  });

  it('rejects a malformed listing id rather than passing it on', async () => {
    await renderDirectImport('/?offerId=offer-aws-sold&listingId=not-a-listing');
    expect(screen.getByRole('button', { name: i18n.directImportButton })).toBeDisabled();
    // The raw URL value is never rendered.
    expect(screen.queryByText(/not-a-listing/u)).toBeNull();
  });

  // Calibration: an offer WITH a pricing term must still reach the real
  // wizard, so the assertions above cannot pass by the panel never rendering.
  it('calibration: an offer with a pricing term still renders the procurement wizard', async () => {
    const api = await import('../../../../../services/API/marketplace-procurement-api');
    vi.mocked(api.marketplaceProcurementAPI.getOffer).mockResolvedValue({
      ...awsSoldOffer,
      sellerOfRecordProfileId: 'some-partner-profile-id',
      sellerOfRecordDisplayName: 'Canonical Group Limited',
      terms: [
        { termId: 't-legal', termType: 'LegalTerm', rawTerm: {} },
        {
          termId: 't-usage',
          termType: 'UsageBasedPricingTerm',
          rawTerm: {
            currencyCode: 'USD',
            rateCards: [{ rateCard: [{ dimensionKey: 'd1', price: '0' }] }],
          },
        },
      ],
    } as never);
    render(
      <MemoryRouter initialEntries={['/?offerId=offer-partner']}>
        <RecoilRoot initializeState={({ set }: { set: SetRecoilState }) => {
          set(selectedProjectState, { projectId: 'proj-1' });
        }}
        >
          <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
            <ProcurementWizard />
          </SWRConfig>
        </RecoilRoot>
      </MemoryRouter>,
    );
    // The wizard chrome (Cancel button) renders for a transactable offer; the
    // direct-import panel does not. Asserting on chrome rather than a
    // data-testid: this repo marks elements with `data-test`, and Cloudscape
    // does not reliably forward unknown props to the DOM, so a getByTestId
    // assertion here could never pass regardless of behaviour.
    expect(await screen.findByText(i18n.cancelButton)).toBeInTheDocument();
    expect(screen.queryByText(i18n.directImportTitle)).not.toBeInTheDocument();
  });
});
