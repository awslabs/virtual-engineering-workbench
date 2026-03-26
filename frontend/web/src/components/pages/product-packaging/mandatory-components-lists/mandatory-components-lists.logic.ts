import { selectedProjectState } from '../../../../state';
import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../../layout';
import { i18n } from './mandatory-components-lists.translations';
import useSWR, { useSWRConfig } from 'swr';
import {
  GetMandatoryComponentsListsResponse,
} from '../../../../services/API/proserve-wb-packaging-api';

interface ServiceAPI {
  getMandatoryComponentsLists: (projectId: string,) => Promise<GetMandatoryComponentsListsResponse>,
}

const FETCH_KEY = (projectId?: string,) => {
  if (!projectId) {
    return null;
  }
  return [
    `projects/${projectId}/mandatorycomponentslists`,
    projectId,
  ];
};

export const useMandatoryComponentsLists = ({ serviceApi }:{ serviceApi: ServiceAPI }) => {
  const { showErrorNotification } = useNotifications();
  const { cache } = useSWRConfig();

  const selectedProject = useRecoilValue(selectedProjectState);

  const FETCHER = ([, projectId, ]: [url: string, projectId: string]) => {
    return serviceApi.getMandatoryComponentsLists(projectId);
  };

  const { data, isLoading, mutate } = useSWR(
    FETCH_KEY(selectedProject.projectId),
    FETCHER,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.mandatorycomponentslistsFetchErrorTitle,
          content: err.message,
        });
      }
    }
  );

  const fetchData = () => {
    cache.delete(`projects/${selectedProject.projectId}/mandatorycomponentslists`);
    mutate(undefined);
  };

  return {
    mandatorycomponentslists: data?.mandatoryComponentsLists || [],
    isLoading,
    loadMandatoryComponentsLists: fetchData,
  };
};

