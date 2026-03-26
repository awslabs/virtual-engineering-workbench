import { useState } from 'react';
import { projectsAPI } from '../../../services';
import { useNotifications } from '../../layout';

const i18n = {
  technologyCreationSucessHeader: 'The technology has been successfully created',
  technologyCreationSuccessContent: 'Please refer to the table below to view details.',
  technologyCreationSuccessError: 'Unable to create technology.'
};

type AddTechnologyProps = {
  projectId: string,
};

const TECHNOLOGY_NAME = /^[A-Za-z0-9_ -]{1,50}$/u;

const useAddTechnology = ({ projectId }: AddTechnologyProps) => {
  const [technologyName, setTechnologyName] = useState<string>('');
  const [technologyDescription, setTechnologyDescription] = useState<string>('');
  const [technologyCreationInProgress, setTechnologyCreationInProgress] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  return {
    technologyName,
    setTechnologyName,
    technologyDescription,
    setTechnologyDescription,
    isFormValid,
    technologyCreationInProgress,
    addTechnology,
    showErrorNotification,
    isSubmitted,
    isTechnologyNameValid
  };


  function isFormValid() {
    return !!isTechnologyNameValid();
  }

  function isTechnologyNameValid() {
    return TECHNOLOGY_NAME.test(technologyName);
  }

  function addTechnology(): Promise<void> {
    if (!isFormValid()) {
      setIsSubmitted(true);
      return Promise.resolve();
    }

    setTechnologyCreationInProgress(true);

    return projectsAPI.addTechnology(projectId, {
      name: technologyName,
      description: technologyDescription
    }).then(() => {
      showSuccessNotification({
        header: i18n.technologyCreationSucessHeader,
        content: i18n.technologyCreationSuccessContent
      });
    }).finally(() => {
      setTechnologyCreationInProgress(false);
      setIsSubmitted(false);
    });
  }
};

export { useAddTechnology };