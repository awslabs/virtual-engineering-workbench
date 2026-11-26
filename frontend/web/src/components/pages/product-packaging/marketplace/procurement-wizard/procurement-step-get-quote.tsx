import { FC } from 'react';
import {
  Alert,
  Box,
  Button,
  ColumnLayout,
  Container,
  Header,
  SpaceBetween,
  Spinner,
} from '@cloudscape-design/components';
import { CreateAgreementRequestResponse } from '../../../../../services/API/marketplace-procurement-api';
import { i18n } from './procurement-wizard.translations';
import { WizardFlow } from './offer-helpers';
import { formatQuoteCurrency, formatQuoteMoney } from './quote-money';

interface Props {
  quote: CreateAgreementRequestResponse | null,
  isLoading: boolean,
  error: Error | null,
  onRequestQuote: () => void,
  wizardFlow: WizardFlow,
}

export const ProcurementStepGetQuote: FC<Props> = ({
  quote,
  isLoading,
  error,
  onRequestQuote,
  wizardFlow,
}) => {
  if (isLoading) {
    return <Box textAlign="center"><Spinner /></Box>;
  }
  if (error) {
    return (
      <Alert
        type="error"
        action={<Button onClick={onRequestQuote}>{i18n.errorRetry}</Button>}
      >
        {error.message}
      </Alert>
    );
  }

  if (!quote) {
    return (
      <SpaceBetween size="l">
        <Button
          variant="primary"
          onClick={onRequestQuote}
          data-test="request-quote-btn"
        >
          {i18n.requestQuoteButton}
        </Button>
      </SpaceBetween>
    );
  }

  return (
    <SpaceBetween size="l">
      <Container header={<Header variant="h2">{i18n.quoteHeader}</Header>}>
        <ColumnLayout columns={2} variant="text-grid">
          <div>
            <Box variant="awsui-key-label">{i18n.quoteAgreementRequestIdLabel}</Box>
            <div data-test="agreement-request-id">{quote.agreementRequestId}</div>
          </div>
          <div>
            <Box variant="awsui-key-label">{i18n.quoteEstimatedValueLabel}</Box>
            <div data-test="quote-estimated-value">
              {formatQuoteMoney(
                quote.estimatedAgreementValue,
                quote.estimatedCurrencyCode,
                wizardFlow,
              )}
            </div>
          </div>
          <div>
            <Box variant="awsui-key-label">{i18n.quoteEstimatedValueAfterTaxLabel}</Box>
            <div data-test="quote-estimated-value-after-tax">
              {formatQuoteMoney(
                quote.estimatedAgreementValueAfterTax,
                quote.estimatedCurrencyCode,
                wizardFlow,
              )}
            </div>
          </div>
          <div>
            <Box variant="awsui-key-label">{i18n.quoteCurrencyLabel}</Box>
            <div>{formatQuoteCurrency(quote.estimatedCurrencyCode, wizardFlow)}</div>
          </div>
        </ColumnLayout>
      </Container>
    </SpaceBetween>
  );
};
