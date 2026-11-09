import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../components/layout';
import useSWR, { useSWRConfig } from 'swr';
import {
  DiscoveredMarketplaceSubscription,
  DiscoverMarketplaceSubscriptionsResponse,
} from '../../services/API/proserve-wb-packaging-api';
import { selectedProjectState } from '../../state';

interface ServiceAPI {
  discoverMarketplaceSubscriptions: (projectId: string) => Promise<DiscoverMarketplaceSubscriptionsResponse>,
}

const SUBSCRIPTIONS_FETCH_KEY = (projectId?: string) => {
  if (!projectId) {
    return null;
  }
  return [
    `projects/${projectId}/marketplace/subscriptions`,
    projectId,
  ];
};

export const useDiscoverMarketplaceSubscriptions = (
  { serviceApi, enabled = true }: { serviceApi: ServiceAPI, enabled?: boolean },
) => {
  const { showErrorNotification } = useNotifications();
  const { cache } = useSWRConfig();
  const selectedProject = useRecoilValue(selectedProjectState);

  const fetcher = ([, projectId]: [url: string, projectId: string]) => {
    return serviceApi.discoverMarketplaceSubscriptions(projectId);
  };

  const { data, isLoading, mutate } = useSWR(
    enabled ? SUBSCRIPTIONS_FETCH_KEY(selectedProject.projectId) : null,
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: 'Failed to load marketplace subscriptions',
          content: err.message,
        });
      },
    },
  );

  const discover = () => {
    cache.delete(`projects/${selectedProject.projectId}/marketplace/subscriptions`);
    mutate(undefined);
  };

  const subscriptions: DiscoveredMarketplaceSubscription[] = data?.subscriptions || [];

  return {
    subscriptions,
    isLoading,
    discover,
  };
};
