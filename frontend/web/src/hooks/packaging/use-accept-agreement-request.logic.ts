import { useState } from 'react';
import { useNotifications } from '../../components/layout';
import {
  marketplaceProcurementAPI,
  AcceptAgreementRequestResponse,
  ProcurementApiError,
} from '../../services/API/marketplace-procurement-api';

interface ServiceAPI {
  acceptAgreementRequest: (
    agreementRequestId: string,
  ) => Promise<AcceptAgreementRequestResponse>,
}

export interface AcceptAgreementError extends Error {
  /** HTTP status returned by the backend, if the failure came from a parsed API response. */
  status?: number,
  /** Backend error code (e.g. AWS `ExpiredResourceException`) if surfaced in the response body. */
  code?: string,
  /**
   * True when `status` is a client error (4xx). Callers use this to differentiate
   * user-actionable failures (expired quote, invalid terms) from generic 5xx / network errors.
   */
  isClientError?: boolean,
}

// HTTP status boundaries for the "4xx == user-actionable" heuristic.
const HTTP_CLIENT_ERROR_MIN = 400;
const HTTP_SERVER_ERROR_MIN = 500;

// Account-scoped: accepting a quote commits the buyer ACCOUNT, so this takes
// no projectId.
export const useAcceptAgreementRequest = ({
  serviceApi = marketplaceProcurementAPI,
}: { serviceApi?: ServiceAPI } = {}) => {
  const { showErrorNotification } = useNotifications();
  const [data, setData] = useState<AcceptAgreementRequestResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<AcceptAgreementError | null>(null);

  const run = async (
    agreementRequestId: string,
  ): Promise<AcceptAgreementRequestResponse | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await serviceApi.acceptAgreementRequest(agreementRequestId);
      setData(result);
      return result;
    } catch (e) {
      const baseErr = e instanceof Error ? e : new Error(String(e));
      const err: AcceptAgreementError = baseErr;
      if (e instanceof ProcurementApiError) {
        err.status = e.status;
        err.code = e.code;
        err.isClientError = e.status >= HTTP_CLIENT_ERROR_MIN
          && e.status < HTTP_SERVER_ERROR_MIN;
      }
      setError(err);
      showErrorNotification({
        header: 'Failed to accept Marketplace quote',
        content: err.message,
      });
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const reset = () => {
    setData(null);
    setError(null);
  };

  return { data, isLoading, error, run, reset };
};
