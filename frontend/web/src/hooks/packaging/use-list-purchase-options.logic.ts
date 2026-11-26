import useSWR from 'swr';
import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../components/layout';
import {
  marketplaceProcurementAPI,
  ListPurchaseOptionsResponse,
  MarketplacePurchaseOption,
} from '../../services/API/marketplace-procurement-api';
import { selectedProjectState } from '../../state';

interface ServiceAPI {
  listPurchaseOptions: (projectId: string) => Promise<ListPurchaseOptionsResponse>,
}

const PURCHASE_OPTIONS_KEY = (projectId?: string) => {
  if (!projectId) { return null; }
  return [`projects/${projectId}/marketplace/purchase-options`, projectId];
};

export const useListPurchaseOptions = ({
  serviceApi = marketplaceProcurementAPI,
  enabled = true,
}: { serviceApi?: ServiceAPI, enabled?: boolean } = {}) => {
  const { showErrorNotification } = useNotifications();
  const selectedProject = useRecoilValue(selectedProjectState);

  const fetcher = ([, projectId]: [url: string, projectId: string]) =>
    serviceApi.listPurchaseOptions(projectId);

  const { data, isLoading, error, mutate } = useSWR(
    enabled ? PURCHASE_OPTIONS_KEY(selectedProject.projectId) : null,
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: 'Failed to load Marketplace purchase options',
          content: err.message,
        });
      },
    },
  );

  // `mutate(undefined)` invalidates the SWR cache entry for this key tuple and triggers
  // a re-fetch — this is the correct SWR revalidation path. `cache.delete(bareUrl)`
  // would be a no-op: SWR is keyed by the [url, projectId] tuple, not the URL string.
  const run = () => {
    mutate(undefined);
  };

  const purchaseOptions: MarketplacePurchaseOption[] = data?.purchaseOptions || [];
  return { data: purchaseOptions, isLoading, error, run };
};
