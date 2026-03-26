import { useState } from 'react';
import useSwr from 'swr';
import {
  GetComponentVersionsResponse,
  GetComponentVersionResponse,
} from '../../../../../services/API/proserve-wb-packaging-api';
import { useNotifications } from '../../../../layout';
import { i18n } from './compare-component-versions.translations';

interface ServiceAPI {
  getComponentVersions: (
    projectId: string, componentId: string
  ) => Promise<GetComponentVersionsResponse>,
  getComponentVersion: (
    projectId: string, componentId: string, versionId: string
  ) => Promise<GetComponentVersionResponse>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId?: string,
  componentId: string,
  initialVersionIdA?: string | null,
}

const CHAR_CODE_BASE = 0;

function decodeYamlB64(b64?: string): string {
  if (!b64) { return ''; }
  const binary = atob(b64);
  const bytes = Uint8Array.from(
    binary, char => char.charCodeAt(CHAR_CODE_BASE)
  );
  return new TextDecoder().decode(bytes);
}

function useVersionFetch(
  serviceApi: ServiceAPI,
  projectId: string | undefined,
  componentId: string,
  versionId: string | null,
  keyPrefix: string,
  showErrorNotification: ReturnType<
    typeof useNotifications
  >['showErrorNotification'],
) {
  const fetcher = (
    [, pid, cid, vid]: [string, string, string, string]
  ) => serviceApi.getComponentVersion(pid, cid, vid);

  return useSwr(
    projectId && versionId
      ? [`${keyPrefix}/${componentId}/${versionId}`,
        projectId, componentId, versionId]
      : null,
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => showErrorNotification({
        header: i18n.errorLoadingVersion,
        content: err.message,
      }),
    }
  );
}

// eslint-disable-next-line complexity
export function useCompareComponentVersions(
  { serviceApi, projectId, componentId, initialVersionIdA }: Props
) {
  const { showErrorNotification } = useNotifications();
  const [versionIdA, setVersionIdA] =
    useState<string | null>(initialVersionIdA || null);
  const [versionIdB, setVersionIdB] =
    useState<string | null>(null);

  function selectVersionA(id: string | null) {
    setVersionIdA(id);
    setVersionIdB(null);
  }

  function selectVersionB(id: string | null) {
    setVersionIdB(id);
  }

  const versionsFetcher = (
    [, pid, cid]: [string, string, string]
  ) => serviceApi.getComponentVersions(pid, cid);

  const {
    data: versionsData, isLoading: versionsLoading,
  } = useSwr(
    projectId
      ? [`compare-component-versions/${componentId}`,
        projectId, componentId]
      : null,
    versionsFetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => showErrorNotification({
        header: i18n.errorLoadingVersions,
        content: err.message,
      }),
    }
  );

  const { data: dataA, isLoading: loadingA } =
    useVersionFetch(
      serviceApi, projectId, componentId,
      versionIdA, 'compare-cv-a', showErrorNotification,
    );

  const { data: dataB, isLoading: loadingB } =
    useVersionFetch(
      serviceApi, projectId, componentId,
      versionIdB, 'compare-cv-b', showErrorNotification,
    );

  const deps = (data: typeof dataA) =>
    data?.componentVersion
      ?.componentVersionDependencies || [];

  return {
    versions: versionsData?.componentVersions || [],
    versionsLoading,
    versionIdA,
    selectVersionA,
    versionIdB,
    selectVersionB,
    yamlA: decodeYamlB64(dataA?.yamlDefinitionB64),
    yamlB: decodeYamlB64(dataB?.yamlDefinitionB64),
    dependenciesA: deps(dataA),
    dependenciesB: deps(dataB),
    loadingA,
    loadingB,
    isReady: !!(
      versionIdA && versionIdB && !loadingA && !loadingB
    ),
  };
}
