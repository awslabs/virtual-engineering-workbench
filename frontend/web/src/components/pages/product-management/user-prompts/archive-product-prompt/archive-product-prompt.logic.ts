import { useState } from 'react';
import { useNotifications } from '../../../../layout';
import { publishingAPI } from '../../../../../services/API';
import { extractErrorResponseMessage } from '../../../../../utils/api-helpers';
import { i18n } from './archive-product-prompt.translations';
import { PRODUCT_STATUS_MAP } from '../../products.translations';

type ArchiveProductProps = {
  projectId?: string,
  productId?: string,
  productStatus?: string,
  loadProductDetails?: () => void,
};

export const useArchiveProductPrompt = ({
  projectId,
  productId,
  productStatus,
  loadProductDetails,
}: ArchiveProductProps) => {

  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const [productArchivingInProgress, setProductArchivingInProgress] = useState(false);

  function archiveProduct() {
    if (productStatus !== PRODUCT_STATUS_MAP.CREATED.toUpperCase()) {
      showErrorNotification({
        header: i18n.archiveErrorWrongStatusHeader,
        content: i18n.archiveErrorWrongStatusContent
      });
    }
    setProductArchivingInProgress(true);
    publishingAPI.archiveProduct(projectId ?? '', productId ?? '').then(() => {
      showSuccessNotification({
        header: i18n.archiveSuccessMessageHeader,
        content: i18n.archiveSuccessMessageContent
      });
    }).catch(async e => {
      showErrorNotification({
        header: i18n.archiveFailMessageHeader,
        content: await extractErrorResponseMessage(e)
      });
    }).finally(() => {
      setProductArchivingInProgress(false);
      loadProductDetails?.();
    });
  }

  return {
    productArchivingInProgress,
    archiveProduct,
  };
};