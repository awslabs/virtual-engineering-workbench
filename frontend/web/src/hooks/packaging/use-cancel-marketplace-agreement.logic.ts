import { useState } from 'react';
import { useNotifications } from '../../components/layout';
import {
  marketplaceProcurementAPI,
  CancelAgreementResponse,
} from '../../services/API/marketplace-procurement-api';

interface ServiceAPI {
  cancelAgreement: (
    agreementId: string,
  ) => Promise<CancelAgreementResponse>,
}

// Account-scoped, see `useAcceptAgreementRequest`.
export const useCancelMarketplaceAgreement = ({
  serviceApi = marketplaceProcurementAPI,
}: { serviceApi?: ServiceAPI } = {}) => {
  const { showErrorNotification } = useNotifications();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const run = async (agreementId: string): Promise<CancelAgreementResponse | null> => {
    setIsLoading(true);
    setError(null);
    try {
      return await serviceApi.cancelAgreement(agreementId);
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      setError(err);
      showErrorNotification({
        header: 'Failed to cancel Marketplace agreement',
        content: err.message,
      });
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return { isLoading, error, run };
};
