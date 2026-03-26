import { packagingAPI } from '../../../../services/API/packaging-api';
import { selectedProjectState } from '../../../../state';
import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../../layout';
import { i18n } from './components.translations';
import useSWR, { useSWRConfig } from 'swr';
import { COMPONENT_STATUS_MAP } from './components-status';
import { ComponentState } from './components.static';
import { SelectProps } from '@cloudscape-design/components';
import { useState } from 'react';
import { Component } from '../../../../services/API/proserve-wb-packaging-api';

const FETCHER = ([, projectId, ]: [url: string, projectId: string]) => {
  return packagingAPI.getComponents(projectId);
};
const COMPONENT_FETCH_KEY = (projectId?: string,) => {
  if (!projectId) {
    return null;
  }
  return [
    `projects/${projectId}/components`,
    projectId,
  ];
};

export const useComponents = () => {
  const { cache } = useSWRConfig();
  const { showErrorNotification } = useNotifications();
  const selectedProject = useRecoilValue(selectedProjectState);
  const statusFirstOption = {
    value: i18n.statusFirstOptionValue,
    label: COMPONENT_STATUS_MAP[('CREATED') as ComponentState],
  };
  const [status, setStatus] = useState<SelectProps.Option>(statusFirstOption);
  const { data, isLoading, mutate } = useSWR(
    COMPONENT_FETCH_KEY(selectedProject.projectId),
    FETCHER,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.componentsFetchErrorTitle,
          content: err.message,
        });
      }
    }
  );
  const fetchData = () => {
    cache.delete(`projects/${selectedProject.projectId}/components`);
    mutate(undefined);
  };
  const filteredConfigurations: Component[] = data ?
    data.components.filter(component => component.status === status?.value) : [];
  const statuses = data?.components.map(component => {
    return component.status;
  });
  const statusOptions = [...new Set(statuses)].map((status) => {
    return {
      value: status,
      label: COMPONENT_STATUS_MAP[(status || 'UNKNOWN') as ComponentState]
    } as SelectProps.Option;
  });

  return {
    components: filteredConfigurations ?? [],
    isLoading,
    loadComponents: fetchData,
    setStatus,
    status,
    statusFirstOption,
    statusOptions,
  };
};
