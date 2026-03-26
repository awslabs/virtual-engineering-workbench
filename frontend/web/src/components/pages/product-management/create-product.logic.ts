/* eslint-disable @stylistic/max-len */
import { useState } from 'react';
import { useNotifications } from '../../layout';
import { useTechnologies } from '../technologies/technologies.logic';
import { publishingAPI } from '../../../services/API/publishing-api';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { i18n } from './create-product.translations';
import { PRODUCT_TYPE_MAP } from './products.translations';
import { Technology } from '../../../services/API/proserve-wb-projects-api/index.ts';

const PRODUCT_NAME_REGEX = /^[A-Za-z0-9_ -]{1,50}$/u;
const PRODUCT_DESCRIPTION_REGEX = /^[A-Za-z0-9_ -]{0,100}$/u;

type CreateProductProps = {
  projectId: string,
};

export const useCreateProduct = ({ projectId }: CreateProductProps) => {
  const DEFAULT_PAGE_SIZE = 50;

  const { showErrorNotification, showSuccessNotification } = useNotifications();

  const {
    technologies,
    isLoadingTechnologies,
  } = useTechnologies({ projectId: projectId, pageSize: DEFAULT_PAGE_SIZE.toString() });

  const productTypes = Object.keys(PRODUCT_TYPE_MAP).filter(type => type !== 'CONTAINER');


  const [productName, setProductName] = useState<string>('');
  const [productDescription, setProductDescription] = useState<string>('');
  const [technology, setTechnology] = useState<Technology>();
  const [productType, setProductType] = useState<string>();
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const { navigateTo } = useNavigationPaths();

  // eslint-disable-next-line complexity
  function isFormValid(): boolean {
    return !!productName.trim() && !!technology && !!productType && isProductNameValid() && isProductDescriptionValid();
  }

  function isProductNameValid(): boolean {
    return PRODUCT_NAME_REGEX.test(productName);
  }

  function isProductDescriptionValid(): boolean {
    return PRODUCT_DESCRIPTION_REGEX.test(productDescription.trim());
  }

  function isProductTechnologyValid(): boolean {
    return technology !== undefined;
  }

  function isProductTypeValid(): boolean {
    return productType !== undefined;
  }

  function saveProduct() {
    if (!isFormValid()) {
      setIsSubmitted(true);
      return;
    }
    setIsSaving(true);
    publishingAPI.createProduct(projectId, {
      productName: productName.trim(),
      productDescription: productDescription.trim(),
      technologyId: technology!.id,
      technologyName: technology!.name,
      productType: productType!
    }).then(() => {
      showSuccessNotification({
        header: i18n.createSuccessMessageHeader,
        content: i18n.createSuccessMessageContent
      });
      navigateTo(RouteNames.Products);
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
    technologies,
    isLoadingTechnologies,
    productName,
    setProductName,
    productDescription,
    setProductDescription,
    technology,
    setTechnology,
    showErrorNotification,
    showSuccessNotification,
    isFormValid,
    saveProduct,
    isSaving,
    productTypes,
    productType,
    setProductType,
    isProductNameValid,
    isProductDescriptionValid,
    isProductTechnologyValid,
    isProductTypeValid,
    isSubmitted
  };
};
