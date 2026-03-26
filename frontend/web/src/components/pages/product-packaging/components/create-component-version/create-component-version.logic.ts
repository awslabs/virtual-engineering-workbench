import { useEffect, useState } from 'react';
import { rcompare } from 'semver';
import { packagingAPI } from '../../../../../services';
import { useNotifications } from '../../../../layout';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './create-component-version.translations';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import {
  ComponentVersion, ComponentVersionEntry
} from '../../../../../services/API/proserve-wb-packaging-api';

export function useCreateComponentVersion({
  projectId,
  componentId,
}:{
  projectId: string,
  componentId: string,
}) {
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const { navigateTo } = useNavigationPaths();

  const [versionCreateInProgress, setVersionCreateInProgress] = useState(false);
  const [isLoadingPreviousVersion, setIsLoadingPreviousVersion] = useState(true);
  const [latestComponentVersionYamlDefinition, setLatestComponentVersionYamlDefinition] = useState('');
  const [latestComponentVersion, setLatestComponentVersion] = useState<ComponentVersion>();
  const [releasedVersions, setReleasedVersions] = useState<ComponentVersion[]>([]);

  const decodeYamlB64 = (b64: string): string => {
    const CHAR_CODE_BASE = 0;
    const binaryString = atob(b64);
    const bytes = Uint8Array.from(binaryString, char => char.charCodeAt(CHAR_CODE_BASE));
    return new TextDecoder().decode(bytes);
  };

  useEffect(() => {
    packagingAPI.getComponentVersions(projectId, componentId).
      then((response) => {
        if (response?.componentVersions?.length) {
          const released = response.componentVersions
            .filter(version => version.status === 'RELEASED' || version.status === 'RETIRED')
            .sort((a, b) => rcompare(a.componentVersionName, b.componentVersionName));
          setReleasedVersions(released);
          if (released.length) {
            setLatestComponentVersion(released[0]);
            return;
          }
        }
        setIsLoadingPreviousVersion(false);
      }).catch(async e => {
        setIsLoadingPreviousVersion(false);
        showErrorNotification({
          header: i18n.createFailMessageHeader,
          content: await extractErrorResponseMessage(e)
        });
      });
  }, []);

  useEffect(() => {
    if (!latestComponentVersion) { return; }
    packagingAPI.getComponentVersion(projectId, componentId, latestComponentVersion.componentVersionId).
      then((response) => {
        if (response?.yamlDefinitionB64) {
          setLatestComponentVersionYamlDefinition(decodeYamlB64(response.yamlDefinitionB64));
        }
      }).catch(async e => {
        showErrorNotification({
          header: i18n.createFailMessageHeader,
          content: await extractErrorResponseMessage(e)
        });
      }).finally(() => setIsLoadingPreviousVersion(false));
  }, [latestComponentVersion]);

  const fetchVersionYaml = async (targetVersionId: string): Promise<string> => {
    const res = await packagingAPI.getComponentVersion(projectId, componentId, targetVersionId);
    return res?.yamlDefinitionB64 ? decodeYamlB64(res.yamlDefinitionB64) : '';
  };

  return {
    versionCreateInProgress,
    latestComponentYamlDefinitionIsLoading: isLoadingPreviousVersion,
    latestComponentVersionYamlDefinition,
    latestComponentVersion,
    releasedVersions,
    fetchVersionYaml,
    createVersion,
  };

  function createVersion({
    description,
    softwareVendor,
    softwareVersion,
    licenseDashboard,
    notes,
    versionReleaseType,
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
    setVersionCreateInProgress(true);

    packagingAPI
      .createComponentVersion(projectId, componentId, {
        componentVersionDescription: description,
        softwareVendor: softwareVendor,
        softwareVersion: softwareVersion,
        licenseDashboard: licenseDashboard,
        notes: notes,
        componentVersionYamlDefinition: yamlDefinition,
        componentVersionReleaseType: versionReleaseType,
        componentVersionDependencies: componentVersionDependencies,
      })
      .then(() => {
        showSuccessNotification({
          header: i18n.createSuccessMessageHeader,
          content: i18n.createSuccessMessageContent,
        });
        navigateTo(RouteNames.ViewComponent, { ':componentId': componentId });
      })
      .catch(async (e) => {
        showErrorNotification({
          header: i18n.createFailMessageHeader,
          content: await extractErrorResponseMessage(e),
        });
      })
      .finally(() => {
        setVersionCreateInProgress(false);
      });
  }
}
