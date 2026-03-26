import { useState } from 'react';
import { projectsAPI } from '../../../services';
import { useNotifications } from '../../layout';
import { i18n } from './update-technology.translations';

type UpdateTechnologyProps = {
  projectId: string,
  techId: string,
  techName: string,
  techDescription: string,
};


const useUpdateTechnology = ({ projectId, techId, techName, techDescription }: UpdateTechnologyProps) => {
  const [technologyName, setTechnologyName] = useState<string>(techName);
  const [technologyDescription, setTechnologyDescription] = useState<string>(techDescription);
  const [technologyCreationInProgress, setTechnologyCreationInProgress] = useState(false);

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  return {
    technologyName,
    setTechnologyName,
    technologyDescription,
    setTechnologyDescription,
    isFormValid,
    technologyCreationInProgress,
    updateTechnology,
    showErrorNotification
  };


  function isFormValid() {
    return !!technologyName;
  }

  function updateTechnology(): Promise<void> {
    if (!isFormValid()) {
      return Promise.resolve();
    }

    setTechnologyCreationInProgress(true);

    return projectsAPI.updateTechnology(projectId, techId, {
      name: technologyName,
      description: technologyDescription
    }).then(() => {
      showSuccessNotification({
        header: i18n.technologyUpdateSuccessHeader,
        content: i18n.technologyUpdateSuccessContent
      });
    }).finally(() => {
      setTechnologyCreationInProgress(false);
    });
  }
};

export { useUpdateTechnology };