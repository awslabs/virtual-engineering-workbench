// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
//
// After a successful accept the wizard must stay mounted and show its success
// panel. That panel is the only place the agreement ID appears, and its
// primary action, "Import this AMI", is the onward path to what the buyer just
// subscribed to. Navigating to the agreements list on accept would unmount the
// wizard before the panel renders.
//
// SELECTOR NOTE: assertions here are on button accessible names and visible
// text. This repo marks elements with `data-test` and Cloudscape does not
// forward unknown props, so getByTestId cannot match.

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { RecoilRoot, SetRecoilState } from 'recoil';
import { SWRConfig } from 'swr';
import { describe, it, expect, vi } from 'vitest';
import { ProcurementWizard } from './procurement-wizard';
import { i18n } from './procurement-wizard.translations';
import { selectedProjectState } from '../../../../../state';

const NO_DEDUPING = 0;

vi.mock('../../../../../services/API/marketplace-procurement-api', async () => {
  const actual = await vi.importActual<typeof import(
    '../../../../../services/API/marketplace-procurement-api'
  )>('../../../../../services/API/marketplace-procurement-api');
  return {
    ...actual,
    marketplaceProcurementAPI: {
      listPurchaseOptions: vi.fn().mockResolvedValue({ purchaseOptions: [] }),
      getOffer: vi.fn(),
      createAgreementRequest: vi.fn(),
      acceptAgreementRequest: vi.fn(),
      cancelAgreement: vi.fn(),
    },
  };
});

const FREE_OFFER = {
  offerId: 'offer-free',
  pricingModelType: 'FREE',
  // A transactable FREE offer carries a zero-rate pricing term, not an empty
  // term list: AWS requires its mandatory terms to be accepted, and the
  // presence of a pricing term is what distinguishes a subscribable offer
  // from one that is imported directly.
  terms: [
    {
      termId: 'term-usage',
      termType: 'UsageBasedPricingTerm',
      rawTerm: {
        currencyCode: 'USD',
        rateCards: [{ rateCard: [{ dimensionKey: 'd1', price: '0' }] }],
      },
    },
    { termId: 'term-legal', termType: 'LegalTerm', rawTerm: {} },
  ],
  associatedProducts: [{ productId: 'prod-ubuntu', productName: 'Ubuntu Noble' }],
};

/** Reports the current location so a navigate() is observable. */
const LocationSpy = () => {
  const location = useLocation();
  return <div data-loc={`${location.pathname}${location.search}`} />;
};

const currentPath = (container: HTMLElement) =>
  container.querySelector('[data-loc]')?.getAttribute('data-loc');

const button = (container: HTMLElement, label: string) =>
  [...container.querySelectorAll('button')].find((b) => b.textContent === label);

// Stand-ins for the pages the wizard can navigate to. These MUST be separate
// routes rather than a single `path="*"` catch-all.
//
// A catch-all silently destroys this entire test file: React Router keeps the
// matched element mounted across a navigation it still matches, so the wizard
// survives its own `navigate()` with all state intact and renders the success
// panel anyway. Three of the tests below passed against the UNFIXED code for
// exactly that reason — the harness, not the component, was keeping the panel
// alive. The real app routes these paths to different components, so a
// navigate genuinely unmounts the wizard and the panel is never seen.
const AGREEMENTS_PAGE_MARKER = 'agreements-page-stub';
const IMPORT_PAGE_MARKER = 'import-page-stub';

const renderAt = (entry: string) => render(
  <MemoryRouter initialEntries={[entry]}>
    <RecoilRoot initializeState={({ set }: { set: SetRecoilState }) => {
      set(selectedProjectState, { projectId: 'proj-1' });
    }}
    >
      <SWRConfig value={{ provider: () => new Map(), dedupingInterval: NO_DEDUPING }}>
        <Routes>
          <Route
            path="/projects/:projectId/marketplace/agreements"
            element={<><div>{AGREEMENTS_PAGE_MARKER}</div><LocationSpy /></>}
          />
          <Route
            path="/projects/:projectId/images/import"
            element={<><div>{IMPORT_PAGE_MARKER}</div><LocationSpy /></>}
          />
          <Route
            path="/"
            element={<><ProcurementWizard /><LocationSpy /></>}
          />
        </Routes>
      </SWRConfig>
    </RecoilRoot>
  </MemoryRouter>,
);

/** Agree to terms, then advance to the Accept & Confirm step. */
const reachAcceptStep = async (container: HTMLElement) => {
  await waitFor(() => {
    expect(container.querySelector('input[type="checkbox"]')).toBeTruthy();
  });
  // FREE is a 2-step flow, so agreeing auto-fires the quote.
  fireEvent.click(container.querySelector('input[type="checkbox"]') as HTMLElement);
  await waitFor(() => expect(button(container, i18n.nextButton)).toBeTruthy());
  fireEvent.click(button(container, i18n.nextButton) as HTMLElement);
  await waitFor(() => expect(button(container, i18n.submitButton)).toBeTruthy());
};

describe('ProcurementWizard — success panel after acceptance', () => {
  /** Drive the wizard to a successful acceptance. */
  const acceptAnOffer = async () => {
    const api = await import('../../../../../services/API/marketplace-procurement-api');
    vi.mocked(api.marketplaceProcurementAPI.getOffer).mockResolvedValue(FREE_OFFER as never);
    vi.mocked(api.marketplaceProcurementAPI.createAgreementRequest)
      .mockResolvedValue({ agreementRequestId: 'ar-1' } as never);
    vi.mocked(api.marketplaceProcurementAPI.acceptAgreementRequest)
      .mockResolvedValue({ agreementId: 'agmt-99' } as never);

    const view = renderAt('/?offerId=offer-free');
    await reachAcceptStep(view.container);
    fireEvent.click(button(view.container, i18n.submitButton) as HTMLElement);
    return view;
  };

  it('stays on the wizard and shows the agreement ID instead of navigating away', async () => {
    const { container } = await acceptAnOffer();

    await waitFor(() => {
      expect(container.textContent).toContain('agmt-99');
    });
    expect(screen.getByText(i18n.acceptedSuccessTitle)).toBeInTheDocument();
    // THE ASSERTION THAT MATTERS: the agreements page did NOT take over, so
    // the panel exists to be seen at all. Asserting the stub's absence (not
    // just the path) is what makes this fail if the wizard navigates here,
    // which swaps the wizard out for that stub.
    expect(screen.queryByText(AGREEMENTS_PAGE_MARKER)).not.toBeInTheDocument();
    expect(currentPath(container)).toBe('/?offerId=offer-free');
  });

  it('makes the Import AMI action reachable', async () => {
    const { container } = await acceptAnOffer();

    await waitFor(() => {
      expect(button(container, i18n.importAmiButton)).toBeTruthy();
    });
    // The reason the panel matters: this is the onward path to the AMI the user
    // just subscribed to, so the agreements page must not replace it.
    expect(screen.queryByText(AGREEMENTS_PAGE_MARKER)).not.toBeInTheDocument();
    expect(button(container, i18n.importAmiButton)).toBeEnabled();
    expect(button(container, i18n.goToAgreementsButton)).toBeTruthy();
  });

  it('deep-links Import into the marketplace source with the purchased product', async () => {
    const { container } = await acceptAnOffer();

    await waitFor(() => expect(button(container, i18n.importAmiButton)).toBeTruthy());
    expect(screen.queryByText(AGREEMENTS_PAGE_MARKER)).not.toBeInTheDocument();
    fireEvent.click(button(container, i18n.importAmiButton) as HTMLElement);

    // `source=marketplace` opens the import wizard on MARKETPLACE_PRODUCT; the
    // product id lets it preselect the subscription just bought.
    await waitFor(() => {
      expect(screen.getByText(IMPORT_PAGE_MARKER)).toBeInTheDocument();
    });
    const location = new URL(currentPath(container) ?? '', 'http://localhost');
    expect(location.pathname).toContain('/images/import');
    expect(location.searchParams.get('source')).toBe('marketplace');
    expect(location.searchParams.get('productId')).toBe('prod-ubuntu');
    expect(location.searchParams.has('productName')).toBe(false);
  });

  it('relabels Finish as Done once the agreement exists', async () => {
    const { container } = await acceptAnOffer();

    await waitFor(() => expect(button(container, i18n.doneButton)).toBeTruthy());
    // "Finish" on a completed agreement invites the user to re-commit
    // something already committed.
    expect(button(container, i18n.submitButton)).toBeUndefined();
  });

  it('leaves for the agreements list when Done is clicked', async () => {
    const { container } = await acceptAnOffer();

    await waitFor(() => expect(button(container, i18n.doneButton)).toBeTruthy());
    fireEvent.click(button(container, i18n.doneButton) as HTMLElement);

    await waitFor(() => {
      expect(screen.getByText(AGREEMENTS_PAGE_MARKER)).toBeInTheDocument();
    });
  });

  it('refuses to step backward once an agreement exists', async () => {
    const { container } = await acceptAnOffer();

    await waitFor(() => expect(container.textContent).toContain('agmt-99'));

    // The wizard stays mounted, so Previous is reachable. Stepping back would
    // reset the quote and let the user accept a SECOND billable agreement for
    // the same subscription.
    const previous = button(container, i18n.previousButton);
    if (previous) { fireEvent.click(previous); }

    expect(container.textContent).toContain('agmt-99');
    expect(screen.getByText(i18n.acceptedSuccessTitle)).toBeInTheDocument();
  });

  it('does not accept twice when Done is clicked after a successful accept', async () => {
    const api = await import('../../../../../services/API/marketplace-procurement-api');
    const { container } = await acceptAnOffer();

    await waitFor(() => expect(button(container, i18n.doneButton)).toBeTruthy());
    const before = vi.mocked(api.marketplaceProcurementAPI.acceptAgreementRequest)
      .mock.calls.length;
    fireEvent.click(button(container, i18n.doneButton) as HTMLElement);

    // Done navigates; it must not re-commit. A second accept on the same quote
    // is a second billable agreement.
    expect(vi.mocked(api.marketplaceProcurementAPI.acceptAgreementRequest).mock.calls.length)
      .toBe(before);
  });

  it('treats Cancel as "leave" once there is nothing left to abandon', async () => {
    const { container } = await acceptAnOffer();

    await waitFor(() => expect(container.textContent).toContain('agmt-99'));
    fireEvent.click(button(container, i18n.cancelButton) as HTMLElement);

    // "Cancel procurement? Progress will be lost." is false here — the
    // agreement is already made and Cancel cannot undo it, so Cancel leaves
    // directly instead of prompting.
    //
    // NOTE: this asserts the NAVIGATION, not the absence of the prompt.
    // Cloudscape's <Modal> renders its content into a body portal in jsdom
    // whether `visible` is true or false — probed both states and they are
    // byte-identical (same dialog node, same header text, same buttons). So
    // "the prompt is not shown" is not expressible as a DOM assertion here;
    // writing it would be a test that cannot fail. The navigation is the
    // observable consequence, and it is enough.
    await waitFor(() => {
      expect(screen.getByText(AGREEMENTS_PAGE_MARKER)).toBeInTheDocument();
    });
  });

  // Calibration: before acceptance the wizard must behave exactly as it did —
  // Cancel does NOT navigate, Finish is still labelled Finish. Without this,
  // "always navigate, never commit" would satisfy everything above.
  it('calibration: does not leave on cancel and says Finish before acceptance', async () => {
    const api = await import('../../../../../services/API/marketplace-procurement-api');
    vi.mocked(api.marketplaceProcurementAPI.getOffer).mockResolvedValue(FREE_OFFER as never);
    vi.mocked(api.marketplaceProcurementAPI.createAgreementRequest)
      .mockResolvedValue({ agreementRequestId: 'ar-1' } as never);

    const { container } = renderAt('/?offerId=offer-free');
    await reachAcceptStep(container);

    // Finish, not Done — no agreement yet.
    expect(button(container, i18n.submitButton)).toBeTruthy();
    expect(button(container, i18n.doneButton)).toBeUndefined();

    fireEvent.click(button(container, i18n.cancelButton) as HTMLElement);

    // Cancel must still route through the confirm prompt rather than leaving,
    // because there IS in-progress work to lose. Asserted as "did not
    // navigate" — the prompt's own visibility is not observable in jsdom (see
    // the note on the Cancel test above).
    expect(currentPath(container)).toBe('/?offerId=offer-free');
  });

  // Calibration: the error path must still keep the user on the step, which was
  // already correct before this change.
  it('calibration: stays on the step and surfaces the error when accept fails', async () => {
    const api = await import('../../../../../services/API/marketplace-procurement-api');
    vi.mocked(api.marketplaceProcurementAPI.getOffer).mockResolvedValue(FREE_OFFER as never);
    vi.mocked(api.marketplaceProcurementAPI.createAgreementRequest)
      .mockResolvedValue({ agreementRequestId: 'ar-1' } as never);
    vi.mocked(api.marketplaceProcurementAPI.acceptAgreementRequest)
      .mockRejectedValue(new Error('accept exploded'));

    const { container } = renderAt('/?offerId=offer-free');
    await reachAcceptStep(container);
    fireEvent.click(button(container, i18n.submitButton) as HTMLElement);

    await waitFor(() => {
      expect(container.textContent).toContain('accept exploded');
    });
    expect(currentPath(container)).toBe('/?offerId=offer-free');
    // No agreement, so the commit action is still offered.
    expect(button(container, i18n.doneButton)).toBeUndefined();
  });
});
