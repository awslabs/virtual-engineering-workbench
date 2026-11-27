import { useState } from 'react';
import { useNotifications } from '../../components/layout';
import {
  marketplaceProcurementAPI,
  GetMarketplaceOfferResponse,
} from '../../services/API/marketplace-procurement-api';

interface ServiceAPI {
  getOffer: (projectId: string, offerId: string) => Promise<GetMarketplaceOfferResponse>,
}

export const useGetMarketplaceOffer = ({
  serviceApi = marketplaceProcurementAPI,
  projectId,
}: { serviceApi?: ServiceAPI, projectId: string }) => {
  const { showErrorNotification } = useNotifications();
  const [data, setData] = useState<GetMarketplaceOfferResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const run = async (offerId: string): Promise<GetMarketplaceOfferResponse | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await serviceApi.getOffer(projectId, offerId);
      setData(result);
      return result;
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      setError(err);
      showErrorNotification({
        header: 'Failed to load Marketplace offer',
        content: err.message,
      });
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  return { data, isLoading, error, run };
};
