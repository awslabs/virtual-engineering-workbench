import { selectedProjectState } from '../../../../state';
import { useRecoilValue } from 'recoil';
import { useNotifications } from '../../../layout';
import { i18n } from './images.translations';
import useSWR, { useSWRConfig } from 'swr';
import { GetImagesResponse, Image } from '../../../../services/API/proserve-wb-packaging-api';
import { useState } from 'react';

interface ServiceAPI {
  getImages: (projectId: string,) => Promise<GetImagesResponse>,
}



const IMAGE_FETCH_KEY = (projectId?: string,) => {
  if (!projectId) {
    return null;
  }
  return [
    `projects/${projectId}/images`,
    projectId,
  ];
};

export const useImages = ({ serviceApi }:{ serviceApi: ServiceAPI }) => {
  const { showErrorNotification } = useNotifications();
  const { cache } = useSWRConfig();
  const [selectedImage, setSelectedImage] = useState<Image>();

  const selectedProject = useRecoilValue(selectedProjectState);

  const fetcher = ([, projectId, ]: [url: string, projectId: string]) => {
    return serviceApi.getImages(projectId);
  };

  const { data, isLoading, mutate } = useSWR(
    IMAGE_FETCH_KEY(selectedProject.projectId),
    fetcher,
    {
      shouldRetryOnError: false,
      onError: (err) => {
        showErrorNotification({
          header: i18n.imagesFetchErrorTitle,
          content: err.message,
        });
      }
    }
  );

  const fetchData = () => {
    cache.delete(`projects/${selectedProject.projectId}/images`);
    mutate(undefined);
  };

  return {
    images: data?.images || [],
    isLoading,
    loadImages: fetchData,
    selectedImage,
    setSelectedImage,
  };
};

