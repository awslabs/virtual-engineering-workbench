/* eslint-disable */
import { Component, ComponentVersion, ComponentVersionEntry, GetComponentResponse, ValidateComponentVersionRequest } from '../../../../../../services/API/proserve-wb-packaging-api';
import { COMPONENT_VERSION_RELEASE_TYPE_MAP } from '../component-version-release-type-map';
import { useState } from 'react';
import { WizardProps } from '@cloudscape-design/components';
import { isNullOrEmpty, isUrl } from '../../../../../../utils/form-validation-helper';
import useSwr from 'swr';
import { useNotifications } from '../../../../../layout';
import { extractErrorResponseMessage } from '../../../../../../utils/api-helpers';
import { i18n } from './component-version-wizard.translations';

const STEP_1_INDEX = 1;
const STEP_2_INDEX = 2;
const STEP_3_INDEX = 3;
const MIN_COMPONENT_VERSION_DEPENDENCIES = 0
interface ServiceAPI {
  getComponent: (projectId: string, componentId: string) => Promise<GetComponentResponse>,
  validateComponentVersion: (projectId: string, componentId: string, validateComponentVersionRequest: ValidateComponentVersionRequest) => Promise<object>,
}

const FETCH_KEY = (
  projectId: string,
  componentId: string,
) => {
  if (!projectId || !componentId) {
    return null;
  }
  return [
    `components/${componentId}`,
    projectId,
    componentId,
  ];
};

export const useComponentVersionWizard = ({
  projectId,
  componentId,
  componentVersion,
  componentVersionYamlDefinition,
  componentVersionDependenciesList,
  serviceApi,
  activeStepIndex,
  setActiveStepIndex
}: {
  projectId: string,
  componentId: string,
  componentVersion: ComponentVersion,
  componentVersionYamlDefinition: string,
  componentVersionDependenciesList: ComponentVersionEntry[],
  serviceApi: ServiceAPI,
  activeStepIndex: number,
  setActiveStepIndex: (step: number) => any
}) => {
  const {showErrorNotification} = useNotifications()
  const isUpdate = !!componentVersion && !!componentVersion.componentId;
  const versionReleaseTypes = Object.keys(COMPONENT_VERSION_RELEASE_TYPE_MAP);
  const [description, setDescription] = useState(componentVersion.componentVersionDescription);
  const [isDescriptionValid, setIsDescriptionValid] = useState(true);
  const [softwareVendor, setSoftwareVendor] = useState(componentVersion.softwareVendor);
  const [isSoftwareVendorValid, setIsSoftwareVendorValid] = useState(true);
  const [softwareVersion, setSoftwareVersion] = useState(componentVersion.softwareVersion);
  const [isSoftwareVersionValid, setIsSoftwareVersionValid] = useState(true);
  const [licenseDashboard, setLicenseDashboard] = useState(componentVersion.licenseDashboard || '');
  const [isLicenseDashboardValid, setIsLicenseDashboardValid] = useState(true);
  const [notes, setNotes] = useState(componentVersion.notes || '');
  const [versionReleaseType, setVersionReleaseType] = useState(versionReleaseTypes[0]);
  const [isVersionReleaseTypeValid, setIsVersionReleaseTypeValid] = useState(true);
  const [yamlDefinition, setYamlDefinition] = useState(componentVersionYamlDefinition);
  const [isYamlDefinitionValidationInProgress, setIsYamlDefinitionValidationInProgress] = useState(false);
  const [isYamlDefinitionValid, setIsYamlDefinitionValid] = useState(true);
  const [cancelConfirmVisible, setCancelConfirmVisible] = useState(false);
  const [componentVersionDependencies, setComponentVersionDependencies] = useState<ComponentVersionEntry[]>(
    componentVersionDependenciesList.length > 0 ? componentVersionDependenciesList : componentVersion?.componentVersionDependencies || []
  );
  const [isComponentVersionDependenciesValid, setIsComponentVersionDependenciesValid] = useState(true);
  const fetcher = ([
    ,
    projectId,
    componentId,
  ]: [
      url: string,
      projectId: string,
      componentId: string,
  ]) => {
    return serviceApi.getComponent(projectId, componentId);
  };

  const { data, isLoading } = useSwr(
    FETCH_KEY(projectId, componentId),
    fetcher, {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.fetchComponentError,
          content: err.message
        });
      }
    }
  );

  function isStep1Valid() {
    setIsLicenseDashboardValid(
      isNullOrEmpty(licenseDashboard) || isUrl(licenseDashboard)
    );
    setIsDescriptionValid(!isNullOrEmpty(description));
    setIsVersionReleaseTypeValid(isUpdate || !isNullOrEmpty(versionReleaseType));
    setIsSoftwareVendorValid(!isNullOrEmpty(softwareVendor));
    setIsSoftwareVersionValid(!isNullOrEmpty(softwareVersion));
    return (
      !isNullOrEmpty(description) &&
      !isNullOrEmpty(softwareVendor) &&
      !isNullOrEmpty(softwareVersion) &&
      ( isNullOrEmpty(licenseDashboard) || isUrl(licenseDashboard))
    );
  }

  function isStep2Valid() {
    if (!!yamlDefinition && isYamlDefinitionValid) {
      setIsYamlDefinitionValidationInProgress(true);
      setIsYamlDefinitionValid(false);

      const validateComponentVersionRequest: ValidateComponentVersionRequest = {
        componentVersionYamlDefinition: yamlDefinition,
      };

      serviceApi.
        validateComponentVersion(projectId, componentId, validateComponentVersionRequest)
        .then(() => {
          setIsYamlDefinitionValid(true);
          setActiveStepIndex(STEP_2_INDEX);
        })
        .catch(async (e) => {
          showErrorNotification({
            header: i18n.validateVersionFailMessageHeader,
            content: await extractErrorResponseMessage(e),
          });
        })
        .finally(() => {
          setIsYamlDefinitionValidationInProgress(false);
        });
    }
    return false;
  }

  function isComponentVersionEntriesValid(items: ComponentVersionEntry[]) {
    for (const item of items) {
      if (isNullOrEmpty(item.componentId) || isNullOrEmpty(item.componentVersionId)) {
        setIsComponentVersionDependenciesValid(false);
        return false;
      }
    }
    setIsComponentVersionDependenciesValid(true);
    return true;
  }

  function isStep3Valid(items: ComponentVersionEntry[]) {
    return (
      componentVersionDependencies.length >= MIN_COMPONENT_VERSION_DEPENDENCIES &&
      isComponentVersionEntriesValid(items)
    );
  }

  function isStepValid(index: number) {
    if (index === STEP_1_INDEX) {
      return isStep1Valid();
    }

    if (index === STEP_2_INDEX) {
      return isStep2Valid();
    }

    if (index === STEP_3_INDEX) {
      return isStep3Valid(componentVersionDependencies);
    }
    return true;
  }

  function requiresValidation(reason: string) {
    return reason === 'next';
  }

  function handleOnNavigate(detail: WizardProps.NavigateDetail) {
    if (requiresValidation(detail.reason) && !isStepValid(detail.requestedStepIndex)) {
      return;
    }
    setActiveStepIndex(detail.requestedStepIndex);
  }

  return {
    component: data?.component || {} as Component,
    isComponentLoading: isLoading,
    isUpdate,
    activeStepIndex,
    description,
    setDescription,
    isDescriptionValid,
    versionReleaseTypes,
    versionReleaseType,
    setVersionReleaseType,
    isVersionReleaseTypeValid,
    handleOnNavigate,
    cancelConfirmVisible,
    setCancelConfirmVisible,
    setActiveStepIndex,
    softwareVendor,
    setSoftwareVendor,
    isSoftwareVendorValid,
    softwareVersion,
    setSoftwareVersion,
    isSoftwareVersionValid,
    licenseDashboard,
    setLicenseDashboard,
    isLicenseDashboardValid,
    notes,
    setNotes,
    yamlDefinition,
    setYamlDefinition,
    isYamlDefinitionValidationInProgress,
    isYamlDefinitionValid,
    setIsYamlDefinitionValid,
    componentVersionDependencies,
    setComponentVersionDependencies,
    isComponentVersionDependenciesValid,
    minComponentVersionDependencies: MIN_COMPONENT_VERSION_DEPENDENCIES
  };
};