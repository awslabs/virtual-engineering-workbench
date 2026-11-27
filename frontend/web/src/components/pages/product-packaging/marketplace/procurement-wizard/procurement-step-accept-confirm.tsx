import { FC } from 'react';
import {
  Alert,
  Badge,
  Box,
  Button,
  ColumnLayout,
  Container,
  Header,
  SpaceBetween,
  Spinner,
  StatusIndicator,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import {
  AcceptAgreementRequestResponse,
  CreateAgreementRequestResponse,
  GetMarketplaceOfferResponse,
} from '../../../../../services/API/marketplace-procurement-api';
import { AcceptAgreementError } from '../../../../../hooks/packaging/use-accept-agreement-request.logic';
import { i18n } from './procurement-wizard.translations';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { WizardFlow, getFriendlyOfferName } from './offer-helpers';
import { buildMarketplaceImportSearch } from '../../images/marketplace-import-handoff';
import { formatQuoteCurrency, formatQuoteMoney, isMissingContractEstimate } from './quote-money';

interface Props {
  acceptance: AcceptAgreementRequestResponse | null,
  isLoading: boolean,
  error: AcceptAgreementError | null,
  onAccept: () => void,
  /**
   * The quote being accepted. Rendered on the pristine (pre-Finish) state so
   * the buyer sees the price immediately before the irreversible action.
   *
   * Required for CONTRACT: that flow replaces step 3's
   * ``ProcurementStepGetQuote`` with ``ProcurementStepConfigurePricing``, so
   * the only component that renders the charge fields never appears. Without
   * this a buyer could commit to a priced annual contract having never been
   * shown the total AWS quoted.
   */
  quote?: CreateAgreementRequestResponse | null,
  /** Called when the user asks for a fresh quote after a 4xx (e.g. expired quote). */
  onRequestNewQuote?: () => void,
  /** The offer being subscribed to. Used to render identity + flow-specific
   * "what Finish does" copy on the pristine state. */
  offer: GetMarketplaceOfferResponse | null,
  /** The resolved wizard flow — drives the pricing-model badge and the
   * commit-step copy so the user knows exactly what clicking Finish will do. */
  wizardFlow: WizardFlow,
}

/**
 * Return a compact pricing-model badge label + color for the given flow.
 * Intentionally terse — the Review Terms step is where pricing detail lives.
 */
const pricingBadge = (flow: WizardFlow): { label: string, color: 'green' | 'blue' | 'grey' } => {
  switch (flow) {
    case 'FREE': return { label: i18n.commitBadgeFree, color: 'green' };
    case 'USAGE': return { label: i18n.commitBadgeUsage, color: 'blue' };
    case 'BYOL': return { label: i18n.commitBadgeByol, color: 'blue' };
    case 'CONTRACT': return { label: i18n.commitBadgeContract, color: 'blue' };
    default: return { label: i18n.commitBadgeGeneric, color: 'grey' };
  }
};

/**
 * Return the "what Finish does" copy tailored to the flow. The user has
 * already reviewed pricing on Step 2 — this step's job is not to repeat
 * the rate card but to make the commit action unambiguous.
 */
const finishDescription = (flow: WizardFlow): string => {
  switch (flow) {
    case 'FREE': return i18n.commitDescriptionFree;
    case 'USAGE': return i18n.commitDescriptionUsage;
    case 'BYOL': return i18n.commitDescriptionByol;
    case 'CONTRACT': return i18n.commitDescriptionContract;
    default: return i18n.commitDescriptionGeneric;
  }
};

/**
 * Acceptance failure. A 4xx from Marketplace typically means the quote is no
 * longer valid — AWS exposes no expiration timestamp on
 * CreateAgreementRequest, so we lean on the server response rather than
 * guarding client-side — and gets a "Get a new quote" action. Anything else is
 * retryable in place.
 *
 * Extracted from the step body to keep it under the repo's complexity limit.
 */
const AcceptError: FC<{
  error: AcceptAgreementError,
  onAccept: () => void,
  onRequestNewQuote?: () => void,
}> = ({ error, onAccept, onRequestNewQuote }) => {
  if (!error.isClientError) {
    return (
      <Alert
        type="error"
        action={<Button onClick={onAccept}>{i18n.errorRetry}</Button>}
      >
        {error.message}
      </Alert>
    );
  }
  return (
    <Alert
      type="warning"
      header={i18n.errorAcceptFailed}
      action={
        onRequestNewQuote &&
          <Button onClick={onRequestNewQuote} data-test="get-new-quote-btn">
            {i18n.getNewQuoteButton}
          </Button>
      }
    >
      <SpaceBetween size="xs">
        <Box variant="p">{i18n.errorQuoteExpiredHint}</Box>
        {error.code &&
          <Box variant="small" data-test="accept-error-code">
            {error.code}
            : {error.message}
          </Box>
        }
      </SpaceBetween>
    </Alert>
  );
};

/**
 * The quoted charge, shown immediately before the irreversible accept. A
 * CONTRACT quote without an estimated value gets a warning, so a missing
 * total is never mistaken for usage-based pricing. Finish is disabled for
 * that quote (`canProceedFromStep`), so the warning offers a new quote.
 */
const CommitQuoteSummary: FC<{
  quote: CreateAgreementRequestResponse,
  wizardFlow: WizardFlow,
  onRequestNewQuote?: () => void,
}> = ({ quote, wizardFlow, onRequestNewQuote }) =>
  <SpaceBetween size="s">
    {isMissingContractEstimate(quote.estimatedAgreementValue, wizardFlow) &&
      <Alert
        type="warning"
        header={i18n.commitEstimateUnavailableHeader}
        data-test="commit-estimate-unavailable"
        action={
          onRequestNewQuote &&
            <Button onClick={onRequestNewQuote} data-test="estimate-get-new-quote-btn">
              {i18n.getNewQuoteButton}
            </Button>
        }
      >
        {i18n.commitEstimateUnavailableBody}
      </Alert>
    }
    <Container
      header={<Header variant="h3">{i18n.commitQuoteHeader}</Header>}
      data-test="commit-quote-summary"
    >
      <ColumnLayout columns={2} variant="text-grid">
        <div>
          <Box variant="awsui-key-label">{i18n.quoteEstimatedValueLabel}</Box>
          <div data-test="commit-estimated-value">
            <Box variant="strong">
              {formatQuoteMoney(
                quote.estimatedAgreementValue,
                quote.estimatedCurrencyCode,
                wizardFlow,
              )}
            </Box>
          </div>
        </div>
        <div>
          <Box variant="awsui-key-label">
            {i18n.quoteEstimatedValueAfterTaxLabel}
          </Box>
          <div data-test="commit-estimated-value-after-tax">
            <Box variant="strong">
              {formatQuoteMoney(
                quote.estimatedAgreementValueAfterTax,
                quote.estimatedCurrencyCode,
                wizardFlow,
              )}
            </Box>
          </div>
        </div>
        <div>
          <Box variant="awsui-key-label">
            {i18n.quoteAgreementRequestIdLabel}
          </Box>
          <div data-test="commit-agreement-request-id">
            {quote.agreementRequestId}
          </div>
        </div>
        <div>
          <Box variant="awsui-key-label">{i18n.quoteCurrencyLabel}</Box>
          <div>{formatQuoteCurrency(quote.estimatedCurrencyCode, wizardFlow)}</div>
        </div>
      </ColumnLayout>
    </Container>
  </SpaceBetween>
;

/**
 * ProcurementStepAcceptConfirm — final wizard step.
 *
 * Purpose: make the "commit" action unambiguous. The user has already
 * reviewed the offer + pricing on Step 2; this step is purely about
 * confirming *what happens when they click Finish*, not re-showing terms.
 *
 *   - pristine: identity line (product + pricing badge) + one paragraph
 *     tailored to the pricing model, explaining what Finish does.
 *   - loading: spinner (while Finish is in flight).
 *   - error: surface it. For 4xx we assume the quote is stale / rejected by
 *     Marketplace and offer a "Get a new quote" action that resets step 3.
 *   - success: durable agreement ID + a link to the agreements page.
 */
export const ProcurementStepAcceptConfirm: FC<Props> = ({
  acceptance,
  isLoading,
  error,
  onAccept,
  onRequestNewQuote,
  offer,
  wizardFlow,
  quote,
}) => {
  const { navigateTo, getPathFor } = useNavigationPaths();
  const navigate = useNavigate();

  if (isLoading) {
    return <Box textAlign="center"><Spinner /></Box>;
  }

  if (error) {
    return (
      <AcceptError
        error={error}
        onAccept={onAccept}
        onRequestNewQuote={onRequestNewQuote}
      />
    );
  }

  if (!acceptance) {
    // Pristine — this is the "confirm before Finish" state. Keep it terse:
    // identity of what's being accepted + a flow-specific description of
    // the commit action. Pricing was reviewed on step 2; not repeated here
    // by design.
    const badge = pricingBadge(wizardFlow);
    const description = finishDescription(wizardFlow);
    const productName = offer?.associatedProducts?.[0]?.productName;
    const offerName = offer ? getFriendlyOfferName(offer) : null;

    return (
      <SpaceBetween size="l">
        <Container header={<Header variant="h2">{i18n.commitHeader}</Header>}>
          <SpaceBetween size="m">
            {offer &&
              <SpaceBetween size="xxs">
                <Box variant="awsui-key-label">{i18n.commitProductLabel}</Box>
                <div data-test="commit-product-identity">
                  <SpaceBetween size="xs" direction="horizontal">
                    <Box variant="strong">{productName || offerName}</Box>
                    <Badge color={badge.color}>{badge.label}</Badge>
                  </SpaceBetween>
                </div>
              </SpaceBetween>
            }
            <Box variant="p" data-test="commit-description">
              {description}
            </Box>
            {quote &&
              <CommitQuoteSummary
                quote={quote}
                wizardFlow={wizardFlow}
                onRequestNewQuote={onRequestNewQuote}
              />
            }
          </SpaceBetween>
        </Container>
      </SpaceBetween>
    );
  }

  return (
    <SpaceBetween size="l">
      <Alert type="success" header={i18n.acceptedSuccessTitle} />
      <Container header={<Header variant="h2">{i18n.acceptHeader}</Header>}>
        <SpaceBetween size="s">
          <div>
            <Box variant="awsui-key-label">{i18n.acceptedAgreementIdLabel}</Box>
            <div data-test="agreement-id">
              <StatusIndicator type="success">{acceptance.agreementId}</StatusIndicator>
            </div>
          </div>
          <Box variant="p" color="text-body-secondary">
            {i18n.acceptedNextStepsHint}
          </Box>
          <SpaceBetween size="xs" direction="horizontal">
            <Button
              variant="primary"
              onClick={() => {
                // Deep-link to the Import AMI wizard on its Marketplace source,
                // carrying the purchased product so the import wizard can
                // preselect its subscription. `navigateTo` does not accept a
                // query string, hence `navigate`. The path keeps its literal
                // `:projectId` segment, like the app's other project-scoped
                // links.
                const importPath = getPathFor(RouteNames.ImportImage);
                const search = buildMarketplaceImportSearch(offer?.associatedProducts?.[0]);
                navigate(`${importPath}${search}`);
              }}
              data-test="import-ami-btn"
            >
              {i18n.importAmiButton}
            </Button>
            <Button
              onClick={() => navigateTo(RouteNames.MarketplaceAgreements)}
              data-test="go-to-agreements-btn"
            >
              {i18n.goToAgreementsButton}
            </Button>
          </SpaceBetween>
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );
};
