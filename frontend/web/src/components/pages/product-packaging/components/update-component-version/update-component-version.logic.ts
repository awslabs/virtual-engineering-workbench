import { useEffect, useState } from 'react';
import { rcompare } from 'semver';
import { packagingAPI } from '../../../../../services';
import { useNotifications } from '../../../../layout';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './update-component-version.translations';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import {
  ComponentVersion,
  ComponentVersionEntry,
  GetComponentVersionResponse,
} from '../../../../../services/API/proserve-wb-packaging-api';
import useSWR from 'swr';

type UpdateComponentVersionProps = {
  projectId: string,
  componentId: string,
  versionId: string,
};

type ServiceAPI = {
  getComponentVersion: (
    projectId: string,
    componentId: string,
    versionId: string) => Promise<GetComponentVersionResponse>,
};

type FetcherProps = {
  projectId: string,
  componentId: string,
  versionId: string,
};

const fetcherFactory = (serviceAPI: ServiceAPI) => async ({
  projectId,
  componentId,
  versionId
}: FetcherProps) => {
  return serviceAPI.getComponentVersion(projectId, componentId, versionId);
};

const COMPONENT_FETCH_KEY = (projectId: string, componentId: string, versionId: string) => {
  if (!projectId) {
    return null;
  }
  return [
    `components/component/${componentId}/update-component-version/${versionId}`,
    projectId,
    componentId,
    versionId,
  ];
};

const decodeYamlB64 = (b64: string): string => {
  const CHAR_CODE_BASE = 0;
  const binaryString = atob(b64);
  const bytes = Uint8Array.from(binaryString, char => char.charCodeAt(CHAR_CODE_BASE));
  return new TextDecoder().decode(bytes);
};

export const useUpdateComponentVersion = ({
  projectId,
  componentId,
  versionId,
}: UpdateComponentVersionProps) => {
  const { showErrorNotification, showSuccessNotification, showWarningNotification } = useNotifications();
  const { navigateTo } = useNavigationPaths();
  const [versionUpdateInProgress, setVersionUpdateInProgress] = useState(false);
  const [yamlDefinition, setYamlDefinition] = useState('');
  const [componentVersion, setComponentVersion] = useState<ComponentVersion>();
  const [releasedVersions, setReleasedVersions] = useState<ComponentVersion[]>([]);
  const [latestReleasedYamlDefinition, setLatestReleasedYamlDefinition] = useState<string | undefined>();

  const { data, isLoading } = useSWR(
    {
      key: COMPONENT_FETCH_KEY,
      projectId: projectId,
      componentId: componentId,
      versionId: versionId,
    },
    fetcherFactory(packagingAPI),
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showWarningNotification({
          header: i18n.warningFetchVersionYamlDefinition,
          content: err.message,
        });
      },
    }
  );

  const yamlDefinitionDecodedString = data?.yamlDefinitionB64
    ? decodeYamlB64(data.yamlDefinitionB64)
    : '';

  useEffect(() => {
    if (data && !isLoading) {
      setYamlDefinition(yamlDefinitionDecodedString);
      setComponentVersion(data?.componentVersion);
    }
  }, [data, isLoading]);

  useEffect(() => {
    if (!data || isLoading) { return; }
    const currentVersion = data.componentVersion;

    packagingAPI.getComponentVersions(projectId, componentId)
      .then((response) => {
        const nonRetired = (response?.componentVersions || [])
          .filter(v =>
            (v.status === 'RELEASED' || v.status === 'RETIRED')
            && v.componentVersionId !== currentVersion?.componentVersionId
          )
          .sort((a, b) => rcompare(a.componentVersionName, b.componentVersionName));

        const versionsForDropdown = currentVersion ? [currentVersion, ...nonRetired] : nonRetired;
        setReleasedVersions(versionsForDropdown);

        if (currentVersion) {
          packagingAPI.getComponentVersion(projectId, componentId, currentVersion.componentVersionId)
            .then((res) => {
              if (res?.yamlDefinitionB64) {
                setLatestReleasedYamlDefinition(decodeYamlB64(res.yamlDefinitionB64));
              }
            })
            .catch(() => { /* non-critical */ });
        }
      })
      .catch(() => { /* non-critical */ });
  }, [data, isLoading]);

  const fetchVersionYaml = async (targetVersionId: string): Promise<string> => {
    const res = await packagingAPI.getComponentVersion(projectId, componentId, targetVersionId);
    return res?.yamlDefinitionB64 ? decodeYamlB64(res.yamlDefinitionB64) : '';
  };

  return {
    yamlDefinition,
    componentVersion,
    isComponentVersionLoading: isLoading,
    versionUpdateInProgress,
    updateVersion,
    releasedVersions,
    latestReleasedYamlDefinition,
    fetchVersionYaml,
  };

  function updateVersion({
    description,
    softwareVendor,
    softwareVersion,
    licenseDashboard,
    notes,
    yamlDefinition,
    componentVersionDependencies,
  }:{
    description: string,
    softwareVendor: string,
    softwareVersion: string,
    licenseDashboard: string,
    notes: string,
    versionReleaseType: string,
    yamlDefinition: string,
    componentVersionDependencies: ComponentVersionEntry[],
  }) {
    setVersionUpdateInProgress(true);

    packagingAPI.updateComponentVersion(projectId, componentId, versionId, {
      componentVersionDescription: description,
      softwareVendor: softwareVendor,
      softwareVersion: softwareVersion,
      licenseDashboard: licenseDashboard,
      notes: notes,
      componentVersionYamlDefinition: yamlDefinition,
      componentVersionDependencies: componentVersionDependencies,
    }).
      then(() => {
        showSuccessNotification({
          header: i18n.updateSuccessMessageHeader,
          content: i18n.createSuccessMessageContent
        });
        navigateTo(RouteNames.ViewComponent, { ':componentId': componentId });
      }).catch(async e => {
        showErrorNotification({
          header: i18n.updateFailMessageHeader,
          content: await extractErrorResponseMessage(e)
        });
      }).finally(() => {
        setVersionUpdateInProgress(false);
      });
  }
};