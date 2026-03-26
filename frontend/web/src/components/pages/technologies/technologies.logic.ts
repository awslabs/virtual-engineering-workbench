import { useEffect, useState } from 'react';
import { projectsAPI } from '../../../services';
import { useNotifications } from '../../layout';
import { i18n } from './technologies.translations';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { Technology } from '../../../services/API/proserve-wb-projects-api';

interface TechnologyProps {
  projectId: string,
  pageSize: string,
}

export const useTechnologies = ({ projectId, pageSize }: TechnologyProps) => {
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [technologyDeletionInProgress, setTechnologyDeletionInProgress] = useState(false);
  const [isLoadingTechnologies, setIsLoadingTechnologies] = useState(false);
  const [technologies, setTechnologies] = useState<Technology[]>();

  function loadTechnologies() {
    if (!projectId) {
      return;
    }

    setIsLoadingTechnologies(true);
    projectsAPI.getTechnologies(projectId, pageSize)
      .then((response) => {
        setTechnologies(response?.technologies || []);
      }).catch(async e => {
        showErrorNotification({
          header: i18n.errorFetchTechnology,
          content: await extractErrorResponseMessage(e)
        });
      }).finally(() => {
        setIsLoadingTechnologies(false);
      });
  }

  useEffect(() => {
    loadTechnologies();
  }, [projectId]);

  function deleteTechnology(techId: string): Promise<void> {

    setTechnologyDeletionInProgress(true);

    return projectsAPI.deleteTechnology(projectId, techId).then(() => {
      showSuccessNotification({
        header: i18n.technologyDeletionSuccessHeader,
        content: i18n.technologyDeletionSuccessContent
      });
    }).catch(async e => {
      showErrorNotification({
        header: i18n.technologyDeleteSuccessError,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setTechnologyDeletionInProgress(false);
    });
  }

  return {
    deleteTechnology: deleteTechnology,
    technologyDeletionInProgress: technologyDeletionInProgress,
    technologies: technologies ? technologies : [],
    loadTechnologies,
    isLoadingTechnologies,
  };
};

