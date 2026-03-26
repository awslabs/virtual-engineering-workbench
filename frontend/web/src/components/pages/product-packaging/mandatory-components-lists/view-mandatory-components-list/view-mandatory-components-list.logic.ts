import {
  GetMandatoryComponentsListResponse,
} from '../../../../../services/API/proserve-wb-packaging-api';
import useSwr from 'swr';
import { useNotifications } from '../../../../layout';
import { i18n } from './view-mandatory-components-list.translations';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';

interface ServiceAPI {
  getMandatoryComponentsList: (
    projectId: string,
    platform: string,
    architecture: string,
    osVersion: string,
  ) => Promise<GetMandatoryComponentsListResponse>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId: string,
  platform: string,
  architecture: string,
  osVersion: string,
}

// eslint-disable-next-line complexity
const FETCH_KEY = (
  projectId: string,
  platform: string,
  architecture: string,
  osVersion: string,
) => {
  if (!projectId || !platform || !architecture || !osVersion) {
    return null;
  }
  return [
    `mandatory-components-lists/${platform}/${architecture}/${osVersion}`,
    projectId,
    platform,
    architecture,
    osVersion,
  ];
};

export function useViewMandatoryComponentsList({
  serviceApi,
  projectId,
  platform,
  architecture,
  osVersion,
}: Props) {
  const { navigateTo } = useNavigationPaths();
  const { showErrorNotification } = useNotifications();
  const fetcher = ([, projectId, platform, architecture, osVersion]: [
    url: string,
    projectId: string,
    platform: string,
    architecture: string,
    osVersion: string
  ]) => {
    return serviceApi.getMandatoryComponentsList(
      projectId,
      platform,
      architecture,
      osVersion
    );
  };

  const { data, isLoading } = useSwr(
    FETCH_KEY(projectId, platform, architecture, osVersion),
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchMandatoryComponentsListError,
          content: err.message,
        });
      },
    }
  );

  function navigateToViewMandatoryComponentsLists() {
    navigateTo(RouteNames.MandatoryComponentsLists);
  }

  function navigateToUpdateMandatoryComponentsList() {
    navigateTo(RouteNames.UpdateMandatoryComponentsList, {
      ':platform': platform,
      ':architecture': architecture,
      ':osVersion': osVersion,
    });
  }

  return {
    mandatoryComponentsList: data?.mandatoryComponentsList,
    mandatoryComponentsListLoading: isLoading,
    viewMandatoryComponentsLists: navigateToViewMandatoryComponentsLists,
    updateMandatoryComponentsList: navigateToUpdateMandatoryComponentsList,
  };
}