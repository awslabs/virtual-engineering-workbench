import {
  Alert,
  Box,
  Button,
  Container,
  HelpPanel,
  Header,
  SpaceBetween,
  Spinner,
  Wizard,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { i18n } from './procurement-wizard.translations';
import {
  useProcurementWizard,
  STEP_BROWSE_OFFERS,
  STEP_REVIEW_TERMS,
  STEP_GET_QUOTE,
  STEP_ACCEPT_CONFIRM,
} from './procurement-wizard.logic';
import {
  GetMarketplaceOfferResponse,
} from '../../../../../services/API/marketplace-procurement-api';
import { ProcurementStepBrowseOffers } from './procurement-step-browse-offers';
import { ProcurementStepReviewTerms } from './procurement-step-review-terms';
import { ProcurementStepGetQuote } from './procurement-step-get-quote';
import { ProcurementStepConfigurePricing } from './procurement-step-configure-pricing';
import { ProcurementStepAcceptConfirm } from './procurement-step-accept-confirm';
import { WorkbenchAppLayout } from '../../../../layout/workbench-app-layout/workbench-app-layout';
import { BreadcrumbItem } from '../../../../layout';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { CancelPrompt } from '../../../products/provision-product-new-steps/cancel-prompt';
import {
  AWS_PUBLISHED_LISTING_ID_PARAM,
  buildAwsPublishedImportSearch,
} from '../../images/aws-published-import-handoff';

/**
 * Breadcrumbs. Entering from the listing-detail page adds a Browse crumb,
 * because the user came through the public catalog.
 */
const buildBreadcrumbs = (startedFromInitialOffer: boolean): BreadcrumbItem[] =>
  startedFromInitialOffer
    ? [
      { path: i18n.breadcrumbMarketplace, href: '#' },
      { path: i18n.breadcrumbBrowse, href: '#' },
      { path: i18n.breadcrumbProcure, href: '#' },
    ]
    : [
      { path: i18n.breadcrumbMarketplace, href: '#' },
      { path: i18n.breadcrumbProcure, href: '#' },
    ];

/**
 * May the user move from one logical step to another?
 *
 * Pure predicate extracted from `onNavigate` to keep the wizard under the
 * repo's complexity limit. The guard order is unchanged.
 */
const canNavigateBetween = ({
  hasAgreement,
  startedFromInitialOffer,
  fromLogical,
  toLogical,
  canProceedFromStep,
}: {
  hasAgreement: boolean,
  startedFromInitialOffer: boolean,
  fromLogical: number,
  toLogical: number,
  canProceedFromStep: (step: number) => boolean,
}): boolean => {
  // Once an agreement exists the wizard is read-only: stepping back
  // would reset the quote and allow a SECOND billable agreement for the same
  // subscription, and the agreement cannot be un-made from here.
  if (hasAgreement) { return false; }
  // Entered from a chosen public listing: never drop the user back into the
  // private-offer inbox at step 1.
  if (startedFromInitialOffer && toLogical < STEP_REVIEW_TERMS) { return false; }
  // Forward moves require the current step to be complete.
  if (toLogical > fromLogical && !canProceedFromStep(fromLogical)) { return false; }
  return true;
};

const FIRST_ITEM_INDEX = 0;
const INDEX_STEP = 1;

/**
 * Map a logical STEP_* constant to the Wizard's own gap-free visible index.
 *
 * When the logical step isn't currently visible (e.g. mid-transition from a
 * paid offer to free-tier, where Get Quote disappears), fall back to the last
 * visible step at or before it — returning an out-of-range index would make
 * the Wizard's activeStepIndex disagree with its steps array.
 */
const toVisibleIndexIn = (visibleLogicalSteps: number[], logical: number): number => {
  const idx = visibleLogicalSteps.indexOf(logical);
  if (idx >= FIRST_ITEM_INDEX) { return idx; }
  for (let i = visibleLogicalSteps.length - INDEX_STEP; i >= FIRST_ITEM_INDEX; i--) {
    if (visibleLogicalSteps[i] <= logical) { return i; }
  }
  return FIRST_ITEM_INDEX;
};

/** Inverse of `toVisibleIndexIn`, clamped to the visible range. */
const toLogicalIndexIn = (visibleLogicalSteps: number[], visible: number): number =>
  visibleLogicalSteps[Math.max(
    FIRST_ITEM_INDEX,
    Math.min(visible, visibleLogicalSteps.length - INDEX_STEP),
  )] ?? STEP_REVIEW_TERMS;

interface DirectImportPanelProps {
  breadcrumbItems: BreadcrumbItem[],
  offer: GetMarketplaceOfferResponse | null,
  isLoading: boolean,
  importSearch: string | null,
  onImport: () => void,
  onBack: () => void,
}

/**
 * Offer with no pricing term: AWS sells the product itself, the licence is
 * granted by the EC2 billing code at launch, and there is no agreement to
 * create. The AMI is imported directly instead of being subscribed to.
 *
 * Extracted from the wizard body, which exceeded the repo's complexity limit.
 */
const DirectImportPanel: FC<DirectImportPanelProps> = ({
  breadcrumbItems,
  offer,
  isLoading,
  importSearch,
  onImport,
  onBack,
}) =>
  <div data-test="procurement-wizard-direct-import">
    <WorkbenchAppLayout
      breadcrumbItems={breadcrumbItems}
      contentType="default"
      tools={(
        <HelpPanel header={<h2>{i18n.wizardTitle}</h2>}>
          <Box variant="p">{i18n.wizardDescription}</Box>
          <Box variant="p">{i18n.directImportInfoHelp}</Box>
        </HelpPanel>
      )}
      content={(
        <SpaceBetween size="l">
          <Container header={<Header variant="h2">{i18n.directImportTitle}</Header>}>
            <SpaceBetween size="m">
              <Alert
                type="info"
                header={i18n.directImportAlertHeader}
                data-test="direct-import-alert"
              >
                {i18n.directImportAlertBody}
              </Alert>
              <Box variant="p">
                <strong>{i18n.offerNameLabel}:</strong>{' '}
                {offer?.offerName || offer?.offerId}
              </Box>
              <Box variant="p">
                <strong>{i18n.sellerLabel}:</strong>{' '}
                {offer?.sellerOfRecordDisplayName || i18n.directImportDefaultSeller}
              </Box>
              {!importSearch &&
                <Alert type="warning" data-test="direct-import-no-listing">
                  {i18n.directImportNoListing}
                </Alert>
              }
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="primary"
                  disabled={!importSearch}
                  onClick={onImport}
                  data-test="direct-import-btn"
                >
                  {i18n.directImportButton}
                </Button>
                <Button
                  variant="link"
                  onClick={onBack}
                >
                  {i18n.directImportBackButton}
                </Button>
              </SpaceBetween>
            </SpaceBetween>
          </Container>
          {isLoading && <Box textAlign="center"><Spinner /></Box>}
        </SpaceBetween>
      )}
    />
  </div>
;

export const ProcurementWizard: FC = () => {
  const [searchParams] = useSearchParams();
  // Listing-detail hand-off: that page navigates here with ?offerId=<id>.
  // When set, the wizard starts on step 2 (Review terms) with the offer
  // already resolved via `useEffect` inside `useProcurementWizard`.
  const initialOfferId = searchParams.get('offerId') || null;
  // The listing the user came from. Needed only by the direct-import path:
  // resolving an AWS-published AMI starts from the listing, not the offer.
  // Validated before use, and never rendered.
  const importSearch = buildAwsPublishedImportSearch({
    listingId: searchParams.get(AWS_PUBLISHED_LISTING_ID_PARAM),
  });

  const logic = useProcurementWizard({ initialOfferId });
  const { navigateTo, getPathFor } = useNavigationPaths();
  // `navigateTo` does not accept a query string, hence `navigate` — same as
  // the post-purchase Import AMI link on the Accept & confirm step.
  const navigate = useNavigate();

  const breadcrumbItems = buildBreadcrumbs(logic.startedFromInitialOffer);

  // When the wizard is entered from the listing-detail page, step 1
  // (Browse offers) is skipped — the user has already picked a product
  // from the public catalog. For 2-step flows (FREE / USAGE / BYOL per
  // pricing model) step 3 (Get Quote) is also skipped — the offer either has
  // no cost (FREE / BYOL) or AWS returns no concrete estimate (USAGE),
  // so a middle step is pointless. The logic hook auto-fires the quote
  // in the background so Accept & Confirm still has a valid quote in
  // state.
  //
  // We track which logical step indices are visible and build a
  // bidirectional mapping to translate between the wizard's own visible
  // index (0-based, gap-free) and our internal logical index (fixed
  // STEP_*_ constants).
  const visibleLogicalSteps: number[] = [];
  if (!logic.startedFromInitialOffer) { visibleLogicalSteps.push(STEP_BROWSE_OFFERS); }
  visibleLogicalSteps.push(STEP_REVIEW_TERMS);
  if (!logic.twoStep) { visibleLogicalSteps.push(STEP_GET_QUOTE); }
  visibleLogicalSteps.push(STEP_ACCEPT_CONFIRM);

  const toVisibleIndex = (logical: number): number =>
    toVisibleIndexIn(visibleLogicalSteps, logical);
  const toLogicalIndex = (visible: number): number =>
    toLogicalIndexIn(visibleLogicalSteps, visible);

  // The agreement id, read once. It gates navigation, Finish's behaviour and
  // Finish's label, and each inline `?.` chain counted toward this component's
  // complexity budget.
  const agreementId = logic.acceptance.data?.agreementId;
  // Any in-flight request blocks the Next/Finish button.
  const isBusy = logic.offer.isLoading || logic.quote.isLoading || logic.acceptance.isLoading;

  // CONTRACT is the only 3-step flow: its middle step is Configure & Confirm
  // Pricing rather than Get Quote. Hoisted so the three ternaries below read
  // off one value (and to keep this component under the complexity limit).
  const isContract = logic.wizardFlow === 'CONTRACT';

  const allSteps = [
    {
      title: i18n.step1Title,
      description: i18n.step1Description,
      content:
        <ProcurementStepBrowseOffers
          productType={logic.productType}
          setProductType={logic.setProductType}
          purchaseOptions={logic.purchaseOptions.data}
          isLoading={logic.purchaseOptions.isLoading}
          error={logic.purchaseOptions.error as Error | null}
          selectedOption={logic.selectedOption}
          onSelect={logic.handleSelectPurchaseOption}
          onRefresh={logic.purchaseOptions.run}
        />
      ,
    }, {
      title: i18n.step2Title,
      description: i18n.step2Description,
      content:
        <ProcurementStepReviewTerms
          offer={logic.offer.data}
          isLoading={logic.offer.isLoading}
          error={logic.offer.error}
          agreedToTerms={logic.agreedToTerms}
          setAgreedToTerms={logic.setAgreedToTerms}
          quoteBlockedMessage={logic.quoteBlockedMessage}
          onRetry={() => {
            if (logic.selectedOption) {
              logic.offer.run(logic.selectedOption.offerId);
            }
          }}
        />
      ,
    },
    {
      title: isContract ? i18n.configurePricingHeader : i18n.step3Title,
      description: isContract ? i18n.configurePricingDescription : i18n.step3Description,
      content: isContract
        ?
        <ProcurementStepConfigurePricing
          offer={logic.offer.data}
          isLoading={logic.offer.isLoading}
          onConfigChange={logic.setContractConfig}
          config={logic.contractConfig}
        />

        :
        <ProcurementStepGetQuote
          quote={logic.quote.data}
          isLoading={logic.quote.isLoading}
          error={logic.quoteStepError}
          onRequestQuote={logic.handleRequestQuote}
          wizardFlow={logic.wizardFlow}
        />
      ,
    },
    {
      title: i18n.step4Title,
      description: i18n.step4Description,
      content:
        <ProcurementStepAcceptConfirm
          acceptance={logic.acceptance.data}
          isLoading={logic.acceptance.isLoading}
          error={logic.acceptance.error}
          onAccept={logic.handleAcceptQuote}
          offer={logic.offer.data}
          wizardFlow={logic.wizardFlow}
          quote={logic.quote.data}
          onRequestNewQuote={logic.handleRequestNewQuote}
        />
      ,
    },
  ];

  // Filter allSteps by the logical steps that are currently visible.
  const steps = visibleLogicalSteps.map((logical) => allSteps[logical]);

  // Offer with no pricing term: don't render the subscribe steps. AWS sells
  // these products itself, the licence comes with the EC2 billing code, and
  // `CreateAgreementRequest` refuses them — there is no subscription flow to
  // run. Offer a direct import of the AMI instead, which the import wizard
  // resolves from the listing.
  //
  // This branch runs only AFTER the offer has resolved: `directImportAvailable`
  // is false while the offer loads, so the wizard renders its normal step 2
  // (Review Terms) with a spinner rather than flashing the wrong screen.
  if (logic.directImportAvailable) {
    return (
      <DirectImportPanel
        breadcrumbItems={breadcrumbItems}
        offer={logic.offer.data}
        isLoading={logic.offer.isLoading}
        importSearch={importSearch}
        onImport={() => {
          if (importSearch) {
            navigate(`${getPathFor(RouteNames.ImportImage)}${importSearch}`);
          }
        }}
        onBack={() => navigateTo(RouteNames.MarketplaceBrowse)}
      />
    );
  }

  return (
    <div data-test="procurement-wizard">
      <CancelPrompt
        cancelConfirmVisible={logic.cancelConfirmVisible}
        setCancelConfirmVisible={logic.setCancelConfirmVisible}
        handleCancelConfirm={() => navigateTo(RouteNames.MarketplaceSubscriptions)}
        i18nStrings={{
          cancelPromptHeader: i18n.cancelPromptHeader,
          cancelPromptText1: i18n.cancelPromptText1,
          cancelPromptText2: '',
          cancelPromptText3: '',
          cancelPromptCancelText: i18n.cancelPromptCancelText,
          cancelPromptConfirmText: i18n.cancelPromptConfirmText,
        }}
      />
      <WorkbenchAppLayout
        breadcrumbItems={breadcrumbItems}
        contentType="default"
        tools={(
          <HelpPanel header={<h2>{i18n.wizardTitle}</h2>}>
            <Box variant="p">{i18n.wizardDescription}</Box>
            <Box variant="p">{i18n.productTypeInfoAmi}</Box>
          </HelpPanel>
        )}
        content={(
          <Wizard
            steps={steps}
            activeStepIndex={toVisibleIndex(logic.activeStepIndex)}
            onNavigate={({ detail }) => {
              const fromLogical = logic.activeStepIndex;
              const toLogical = toLogicalIndex(detail.requestedStepIndex);
              if (!canNavigateBetween({
                hasAgreement: !!agreementId,
                startedFromInitialOffer: logic.startedFromInitialOffer,
                fromLogical,
                toLogical,
                canProceedFromStep: logic.canProceedFromStep,
              })) { return; }
              // Reset stale quote/acceptance state when stepping back past step 3.
              logic.handleBackwardNavigation(fromLogical, toLogical);
              logic.setActiveStepIndex(toLogical);
            }}
            onSubmit={async () => {
              // Finish drives the accept call itself, so the wizard cannot end
              // without a Marketplace agreement having been created. Finish is
              // also blocked for other invalid states via `canProceedFromStep`.
              if (!logic.canProceedFromStep(STEP_ACCEPT_CONFIRM)) { return; }
              // Second Finish after a successful accept is the user's "done"
              // action — the success panel has been seen, so leave for the
              // agreements list.
              if (agreementId) {
                navigateTo(RouteNames.MarketplaceAgreements);
                return;
              }
              // Deliberately NO navigate on success. Navigating to the
              // agreements list here would unmount the wizard before its
              // success panel renders. That panel is the only place the
              // agreement ID is shown, and its primary action, "Import this
              // AMI", is the onward path to what the buyer just subscribed to.
              //
              // `acceptance.data` is what advances the UI: the step re-renders
              // as the success panel, and the user chooses where to go next.
              await logic.handleAcceptQuote();
              // On failure the error is surfaced inside `ProcurementStepAcceptConfirm`
              // (with a "Get a new quote" action for 4xx). We stay on step 4 either way.
            }}
            onCancel={() => {
              // After an agreement exists there is no in-progress work to
              // abandon, and the prompt's "Progress will be lost" would imply
              // the agreement itself gets undone — it does not, and Cancel
              // cannot cancel it. Treat Cancel as "leave this page".
              if (agreementId) {
                navigateTo(RouteNames.MarketplaceAgreements);
                return;
              }
              logic.setCancelConfirmVisible(true);
            }}
            isLoadingNextStep={isBusy}
            i18nStrings={{
              stepNumberLabel: i18n.stepNumberLabel,
              collapsedStepsLabel: i18n.collapsedStepsLabel,
              cancelButton: i18n.cancelButton,
              previousButton: i18n.previousButton,
              nextButton: i18n.nextButton,
              // Once the agreement exists, "Finish" would invite the user to
              // re-commit something already committed. Relabel it as the
              // leave-the-page action it now is.
              submitButton: agreementId
                ? i18n.doneButton
                : i18n.submitButton,
            }}
          />
        )}
      />
    </div>
  );
};
