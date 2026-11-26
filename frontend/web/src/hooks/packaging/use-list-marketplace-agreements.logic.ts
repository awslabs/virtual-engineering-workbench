import useSWR from 'swr';
import { useNotifications } from '../../components/layout';
import {
  ListMarketplaceAgreementsResponse,
  MarketplaceAgreementResponseItem,
} from '../../services/API/proserve-wb-packaging-api';

interface ServiceAPI {
  listMarketplaceAgreements: () => Promise<ListMarketplaceAgreementsResponse>,
}

// Account-scoped, so the SWR key carries no project: the response is the same
// for every project a user can see, and keying by project would cache N
// identical copies and refetch on every project switch.
const AGREEMENTS_KEY = ['marketplace/agreements'];

export const useListMarketplaceAgreements = ({
  serviceApi,
  enabled = true,
}: { serviceApi: ServiceAPI, enabled?: boolean }) => {
  const { showErrorNotification } = useNotifications();

  const fetcher = () => serviceApi.listMarketplaceAgreements();

  const { data, isLoading, error, mutate } = useSWR(
    enabled ? AGREEMENTS_KEY : null,
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: 'Failed to load Marketplace agreements',
          content: err.message,
        });
      },
    },
  );

  // Same reasoning as `useListPurchaseOptions.run`: SWR is keyed by the tuple, so the
  // previous `cache.delete(bareUrl)` call was a no-op. `mutate(undefined)` does the real
  // revalidation.
  const run = () => {
    mutate(undefined);
  };

  const agreements: MarketplaceAgreementResponseItem[] = data?.agreements || [];
  return { data: agreements, isLoading, error, run };
};
