import { FC } from 'react';
import {
  Alert,
  Badge,
  Box,
  Button,
  Checkbox,
  ColumnLayout,
  Container,
  Header,
  SpaceBetween,
  Spinner,
} from '@cloudscape-design/components';
import { GetMarketplaceOfferResponse } from '../../../../../services/API/marketplace-procurement-api';
import { i18n } from './procurement-wizard.translations';
import { TermSummary } from './term-summary';
import { isFreeTierOffer, isByolOffer, getFriendlyOfferName } from './offer-helpers';

interface Props {
  offer: GetMarketplaceOfferResponse | null,
  isLoading: boolean,
  error: Error | null,
  agreedToTerms: boolean,
  setAgreedToTerms: (v: boolean) => void,
  onRetry: () => void,
  /** Why the quote for these terms was not requested, if it was refused. */
  quoteBlockedMessage?: string | null,
}

const NO_TERMS = 0;

const OFFER_GRID_COLUMNS = 2;
const NOT_AVAILABLE = '—';

/**
 * Offer identity: name, product(s), seller, pricing model.
 *
 * Extracted from the step body, whose `||` fallback chains pushed it over the
 * repo's complexity limit.
 */
const OfferIdentityGrid: FC<{ offer: GetMarketplaceOfferResponse }> = ({ offer }) => {
  const products = (offer.associatedProducts || [])
    .map((p) => p.productName || p.productId)
    .join(', ');
  return (
    <ColumnLayout columns={OFFER_GRID_COLUMNS} variant="text-grid">
      <div>
        <Box variant="awsui-key-label">{i18n.offerNameLabel}</Box>
        <div>{getFriendlyOfferName(offer)}</div>
      </div>
      <div>
        <Box variant="awsui-key-label">{i18n.productLabel}</Box>
        <div>{products || NOT_AVAILABLE}</div>
      </div>
      <div>
        <Box variant="awsui-key-label">{i18n.sellerLabel}</Box>
        <div>{offer.sellerOfRecordDisplayName || NOT_AVAILABLE}</div>
      </div>
      <div>
        <Box variant="awsui-key-label">{i18n.pricingModelLabel}</Box>
        <div>{offer.pricingModelDisplayName || offer.pricingModelType || NOT_AVAILABLE}</div>
      </div>
    </ColumnLayout>
  );
};


export const ProcurementStepReviewTerms: FC<Props> = ({
  offer,
  isLoading,
  error,
  agreedToTerms,
  setAgreedToTerms,
  onRetry,
  quoteBlockedMessage = null,
}) => {
  if (isLoading) {
    return <Box textAlign="center"><Spinner /></Box>;
  }
  if (error) {
    return (
      <Alert
        type="error"
        action={<Button onClick={onRetry}>{i18n.errorRetry}</Button>}
      >
        {error.message}
      </Alert>
    );
  }
  if (!offer) {
    return <Alert type="warning">{i18n.reviewTermsNoOfferHint}</Alert>;
  }

  const isFree = isFreeTierOffer(offer);
  const isByol = isByolOffer(offer);
  const terms = offer.terms || [];

  return (
    <SpaceBetween size="l">
      <Container header={<Header variant="h2">{i18n.offerHeaderLabel}</Header>}>
        <SpaceBetween size="s">
          {isFree &&
            <Alert
              type="success"
              data-test="free-tier-badge"
              header={(
                <Box>
                  <Badge color="green">{i18n.freeTierBadge}</Badge>{' '}
                  {i18n.freeTierAlertHeader}
                </Box>
              )}
            >
              {i18n.freeTierAlertBody}
            </Alert>
          }
          {isByol &&
            <Alert
              type="info"
              data-test="byol-badge"
              header={(
                <Box>
                  <Badge color="blue">{i18n.byolBadge}</Badge>{' '}
                  {i18n.byolAlertHeader}
                </Box>
              )}
            >
              {i18n.byolAlertBody}
            </Alert>
          }
          <OfferIdentityGrid offer={offer} />
        </SpaceBetween>
      </Container>

      {terms.length > NO_TERMS &&
        <Container header={<Header variant="h2">{i18n.termsLabel}</Header>}>
          <SpaceBetween size="l" data-test="term-summary-list">
            {terms.map((term) =>
              <TermSummary key={term.termId} term={term} />
            )}
          </SpaceBetween>
        </Container>
      }

      <Checkbox
        checked={agreedToTerms}
        onChange={({ detail }) => setAgreedToTerms(detail.checked)}
        data-test="agree-terms-checkbox"
      >
        {i18n.agreeCheckboxLabel}
      </Checkbox>
      {quoteBlockedMessage &&
        <Alert type="error" data-test="quote-blocked">{quoteBlockedMessage}</Alert>
      }
    </SpaceBetween>
  );
};
