import { useState, useEffect } from 'react';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { useNotifications } from '../../../../layout';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './update-component.translations';
import {
  GetComponentResponse,
  UpdateComponentRequest
} from '../../../../../services/API/proserve-wb-packaging-api';
import useSwr from 'swr';

interface ServiceAPI {
  getComponent: (
    projectId: string,
    componentId: string
  ) => Promise<GetComponentResponse>,
  updateComponent: (
    projectId: string,
    componentId: string,
    updateComponentRequest: UpdateComponentRequest
  ) => Promise<object>,
}

interface Props {
  serviceApi: ServiceAPI,
  projectId: string,
  componentId: string,
}

interface FormData {
  componentDescription: string,
}

interface FormErrors {
  componentDescription?: string,
}

const FETCH_KEY = (projectId?: string, componentId?: string) => {
  if (!projectId || !componentId) {
    return null;
  }
  return [`components/${componentId}`, projectId, componentId];
};

export function useUpdateComponent({ serviceApi, projectId, componentId }: Props) {
  const { navigateTo } = useNavigationPaths();
  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const [formData, setFormData] = useState<FormData>({
    componentDescription: '',
  });

  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetcher = ([, projectId, componentId]: [
    url: string,
    projectId: string,
    componentId: string
  ]) => {
    return serviceApi.getComponent(projectId, componentId);
  };

  const { data, isLoading } = useSwr(
    FETCH_KEY(projectId, componentId),
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err: Error) => {
        showErrorNotification({
          header: i18n.fetchErrorHeader,
          content: err.message,
        });
      },
    }
  );

  useEffect(() => {
    if (data?.component) {
      setFormData({
        componentDescription: data.component.componentDescription || '',
      });
    }
  }, [data]);


  function validateComponentDescription(description: string): string | undefined {
    const maxComponentDescriptionLength = 1024;

    if (description.length > maxComponentDescriptionLength) {
      return i18n.componentDescriptionMaxLength;
    }

    return undefined;
  }

  function validateForm(): boolean {
    const errors: FormErrors = {};

    const descError = validateComponentDescription(formData.componentDescription);
    if (descError) {
      errors.componentDescription = descError;
    }

    setFormErrors(errors);
    return !Object.keys(errors).length;
  }

  function handleInputChange(field: keyof FormData, value: string) {
    setFormData((prev: FormData) => ({ ...prev, [field]: value }));

    if (formErrors[field]) {
      setFormErrors((prev: FormErrors) => ({ ...prev, [field]: undefined }));
    }
  }

  async function handleSubmit() {
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await serviceApi.updateComponent(projectId, componentId, {
        componentDescription: formData.componentDescription,
      });

      showSuccessNotification({
        header: i18n.updateSuccessHeader,
        content: i18n.updateSuccessContent,
      });

      navigateTo(RouteNames.ViewComponent, { ':componentId': componentId });
    } catch (error) {
      showErrorNotification({
        header: i18n.updateErrorHeader,
        content: await extractErrorResponseMessage(error),
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleCancel() {
    navigateTo(RouteNames.ViewComponent, { ':componentId': componentId });
  }

  return {
    component: data?.component,
    componentLoading: isLoading,
    formData,
    formErrors,
    isSubmitting,
    handleInputChange,
    handleSubmit,
    handleCancel,
  };
}
