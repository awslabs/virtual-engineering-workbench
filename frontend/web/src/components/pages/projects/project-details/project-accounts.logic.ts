import { useEffect, useState } from 'react';
import { projectsAPI } from '../../../../services';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers';
import { useNotifications } from '../../../layout';
import useSWR from 'swr';
import { useLocation } from 'react-router-dom';
import { ProjectAccount } from '../../../../services/API/proserve-wb-projects-api';

const FETCH_KEY = 'administration/program/accounts';

const i18n = {
  accountFetchError: 'Unable to fetch project accounts.',
  accountReonboardStartedHeader: 'Success',
  accountReonboardStartedBody: 'Account reonboarding started',
  accountReonboardError: 'Unable to trigger account reonboarding',
};

type ProjectAccountsProps = {
  projectId: string,
};

interface FetcherProps {
  projectId: string,
}

const useProjectAccounts = ({ projectId }: ProjectAccountsProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [reonboardLoading, setReonboardLoading] = useState(false);
  const { state } = useLocation();
  const [technologyAccounts, setTechnologyAccounts] = useState<ProjectAccount[]>([]);

  const fetcher = (key: FetcherProps) => projectsAPI.getProjectAccounts(key.projectId, true);

  const { data, isLoading, mutate } =
    useSWR({ key: FETCH_KEY, projectId }, fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.accountFetchError,
          content: err.message
        });
      }
    });

  useEffect(() => {
    if (state) {
      const accounts = data?.projectAccounts.filter(value => value.technologyId === state.technologyId);
      setTechnologyAccounts(accounts ?? []);
    }
  }, [data?.projectAccounts, isLoading]);

  return {
    projectAccounts: data ? data.projectAccounts : [],
    accountsLoading: isLoading,
    loadProjectAccounts: mutate,
    reonboardProjectAccount,
    reonboardLoading,
    activateProjectAccount,
    deactivateProjectAccount,
    technologyAccounts: technologyAccounts ?? [],
  };

  function activateProjectAccount(projectId: string, accountId: string) {
    projectsAPI.activateProjectAccount(projectId, accountId);
    mutate();
  }

  function deactivateProjectAccount(projectId: string, accountId: string) {
    projectsAPI.deactivateProjectAccount(projectId, accountId);
    mutate();
  }

  function reonboardProjectAccount(projectId: string, accountIds: string[]) {
    setReonboardLoading(true);
    projectsAPI.
      reonboardProjectAccount(projectId, accountIds).
      then(() => {
        showSuccessNotification({
          header: i18n.accountReonboardStartedHeader,
          content: i18n.accountReonboardStartedBody,
        });
      }).
      catch(async e => {
        showErrorNotification({
          header: i18n.accountReonboardError,
          content: await extractErrorResponseMessage(e)
        });
      }).
      finally(() => {
        setReonboardLoading(false);
      });
  }


};

export { useProjectAccounts };
