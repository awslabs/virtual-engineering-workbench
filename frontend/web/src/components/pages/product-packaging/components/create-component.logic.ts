/* eslint-disable @stylistic/max-len */
import { useState } from 'react';
import { SelectProps } from '@cloudscape-design/components';
import { useNotifications } from '../../../layout';
import { packagingAPI } from '../../../../services/API/packaging-api';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { i18n } from './create-component.translations';
import { PACKAGING_OS_VERSIONS, PACKAGING_SUPPORTED_ARCHITECTURES } from '../shared';

const COMPONENT_NAME_REGEX = /^.{1,100}$/u;
const COMPONENT_DESCRIPTION_REGEX = /^.{0,1024}$/u;

type CreateComponentProps = {
  projectId: string,
};

export const useCreateComponent = ({ projectId }: CreateComponentProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const [componentName, setComponentName] = useState<string>('');
  const [componentDescription, setComponentDescription] = useState<string>('');
  const [componentPlatform, setComponentPlatform] = useState<string>('Windows');
  const [componentSupportedOsVersions, setComponentSupportedOsVersions] = useState<SelectProps.Option[]>([]);
  const [componentSupportedArchitectures, setComponentSupportedArchitectures] = useState<SelectProps.Option[]>([]);
  const availableComponentSupportedOsVersions = PACKAGING_OS_VERSIONS[componentPlatform] || [];
  const availableComponentSupportedArchitectures = PACKAGING_SUPPORTED_ARCHITECTURES[componentPlatform] || [];
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const { navigateTo } = useNavigationPaths();
  const EMPTY = 0;

  // eslint-disable-next-line complexity
  function isFormValid(): boolean {
    return !!componentName.trim() && !!componentPlatform && !!componentSupportedOsVersions && !!componentSupportedArchitectures && isComponentNameValid() && isComponentDescriptionValid();
  }

  function isComponentNameValid(): boolean {
    return COMPONENT_NAME_REGEX.test(componentName);
  }

  function isComponentDescriptionValid(): boolean {
    return COMPONENT_DESCRIPTION_REGEX.test(componentDescription.trim());
  }

  function isComponentArchitecturesValid(): boolean {
    return componentSupportedArchitectures.length !== EMPTY;
  }

  function isComponentOsVersionsValid(): boolean {
    return componentSupportedOsVersions.length !== EMPTY;
  }

  function saveComponent() {
    if (!isFormValid()) {
      setIsSubmitted(true);
      return;
    }
    setIsSaving(true);
    packagingAPI.createComponent(projectId, {
      componentName: componentName.trim(),
      componentDescription: componentDescription.trim(),
      componentPlatform: componentPlatform,
      componentSupportedOsVersions: componentSupportedOsVersions.map((v) => { return v.value!; }),
      componentSupportedArchitectures: componentSupportedArchitectures.map((v) => { return v.value!; }),
    }).then(createComponentResponse => {
      showSuccessNotification({
        header: i18n.createSuccessMessageHeader,
        content: i18n.createSuccessMessageContent
      });
      navigateTo(RouteNames.ViewComponent, { ':componentId': createComponentResponse.componentId });
    }).catch(async e => {
      showErrorNotification({
        header: i18n.createFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setIsSaving(false);
      setIsSubmitted(false);
    });
  }

  return {
    componentName,
    setComponentName,
    componentDescription,
    setComponentDescription,
    componentPlatform,
    setComponentPlatform,
    componentSupportedOsVersions,
    setComponentSupportedOsVersions,
    availableComponentSupportedOsVersions,
    componentSupportedArchitectures,
    setComponentSupportedArchitectures,
    availableComponentSupportedArchitectures,
    isFormValid,
    saveComponent,
    isSaving,
    isSubmitted,
    isComponentNameValid,
    isComponentDescriptionValid,
    isComponentArchitecturesValid,
    isComponentOsVersionsValid
  };
};