import { useState } from 'react';
import { useNotifications } from '../../components/layout';
import { ImportImageRequest, ImportImageResponse } from '../../services/API/proserve-wb-packaging-api';

interface ServiceAPI {
  importImage: (projectId: string, body: ImportImageRequest) => Promise<ImportImageResponse>,
}

export const useImportImage = ({ serviceApi, projectId }: { serviceApi: ServiceAPI, projectId: string }) => {
  const { showErrorNotification } = useNotifications();
  const [isLoading, setIsLoading] = useState(false);

  const importImage = async (body: ImportImageRequest): Promise<ImportImageResponse> => {
    setIsLoading(true);
    try {
      return await serviceApi.importImage(projectId, body);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Import failed';
      showErrorNotification({ header: 'Import failed', content: msg });
      throw e;
    } finally {
      setIsLoading(false);
    }
  };

  return { importImage, isLoading };
};
