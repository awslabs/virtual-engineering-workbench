/* eslint-disable */
import { useMemo, useState } from 'react';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../state';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers';
import { useNotifications } from '../../../layout';
import { useParams } from 'react-router-dom';
import {
  GetProvisionedProductResponse,
  ProductParameter,
} from '../../../../services/API/proserve-wb-provisioning-api';
import { ServiceAPI } from '../../../../services';
import {
  ProvisionedProductParameters,
  RecommendationReason,
  ProvisionedProductRecommendationWarning,
  ProvisionedProductDetailsHookPorps,
} from './interface';
import { useCommonProvisionedProduct, useCommonProvisionedProductState } from '../common.logic';
import useSWR from 'swr';

type FetcherProps = {
  projectId: string,
  provisionedProductId: string,
};

export const useProvisionedProductDetails = (
  props: ProvisionedProductDetailsHookPorps
) => {
  const { id } = useParams();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { showErrorNotification } = useNotifications();
  const [stopConfirmVisible, setStopConfirmVisible] = useState(false);

  const fetcherFactory =
    (serviceAPI: ServiceAPI) =>
      async ({
        projectId,
        provisionedProductId,
      }: FetcherProps): Promise<GetProvisionedProductResponse> => {
        const serviceApiProm = serviceAPI.getProvisionedProduct(
          projectId,
          provisionedProductId
        );
        serviceApiProm.catch(async (e) => {
          showErrorNotification({
            header: props.translations.errorMessageHeader,
            content: await extractErrorResponseMessage(e),
          });
        });
        return serviceApiProm;
      };

  const {
    data: apiResponse,
    mutate,
    isLoading: isLoadingProvProd,
  } = useSWR(
    {
      key: `products/${props.productType}/provisioned/${id}`,
      projectId: selectedProject.projectId!,
      provisionedProductId: id,
    },
    fetcherFactory(props.serviceAPI),
    {
      shouldRetryOnError: false,
    }
  );


  const provisionedProduct = apiResponse?.provisionedProduct;
  const provisioningParameters =
    provisionedProduct?.provisioningParameters || [];
  const outputParameters = provisionedProduct?.outputs || [];
  const parametersMetadata = apiResponse?.versionMetadata;

  const commonHookRes = useCommonProvisionedProduct();
  const commonStateHookRes = useCommonProvisionedProductState({
    provisionedProduct,
    stateActionCompleteHandler: mutate,
    setStopConfirmVisible
  });

  const paramsMetadataMap = useMemo(() => {
    const map = new Map<string, ProductParameter>();
    provisioningParameters.forEach((provisionedParam) => {
      parametersMetadata?.parameters?.forEach((metadataParam) => {
        if (provisionedParam.key === metadataParam.parameterKey) {
          map.set(provisionedParam.key, metadataParam);
        }
      });
    });
    return map;
  }, [parametersMetadata, provisioningParameters]);

  const recommendedParamMetadata = () => {
    const instanceTypeParam = parametersMetadata?.parameters?.find(
      (param) => param.parameterKey === 'InstanceType'
    );
    const recommendedOption = Object.entries(
      instanceTypeParam?.parameterMetaData?.optionLabels || []
    ).find(([key]) => key === provisionedProduct?.recommendedInstanceType);
    if (!recommendedOption) {
      return '';
    }

    return recommendedOption[1];
  };

  const getParameterLabel = (object: object | undefined, key: string | undefined) => {
    if (object && key && key !== '') {
      const map = new Map(Object.entries(object));
      return map.get(key);
    }
    return key;
  };

  const parameters: ProvisionedProductParameters[] = provisioningParameters
    .map((param) => ({
      key: param.key || '',
      value: getParameterLabel(
        paramsMetadataMap.get(param.key)?.parameterMetaData?.optionLabels, param.value
      ) || props.translations.tableValueNotAvailableText,
      description:
        paramsMetadataMap.get(param.key)?.description ??
        props.translations.tableDescriptionNotAvailableText,
    }))
    .concat(
      outputParameters.map((param) => ({
        key: param.outputKey,
        value: param.outputValue,
        description: param.description ?? props.translations.tableDescriptionNotAvailableText,
      }))
    )
    .filter((e) => e.key !== 'FeatureToggles');


  const getUnderprovisionedRecommendation = () => {
    let recommendation = `${props.translations.warningUnderprovisionedBaiseContent}`;
    if (recommendedParamMetadata()) {
      recommendation = recommendation.concat(
        ` ${props.translations.warningUnderprovisionedWithInsatnceTypeContent}`
      );
    }
    return recommendation;
  };

  const getOverprovisionedRecommendation = () => {
    let recommendation = `${props.translations.warningOverprovisionedBaiseContent}`;
    if (recommendedParamMetadata()) {
      recommendation = recommendation.concat(
        ` ${props.translations.warningOverprovisionedWithInsatnceTypeContent}`
      );
    }
    return recommendation;
  };

  const isOverprovisionedWarning = () => {
    if (provisionedProduct?.instanceRecommendationReason === undefined) {
      return false;
    }
    return (
      provisionedProduct?.instanceRecommendationReason ===
      RecommendationReason.OverProvisioned
    );
  };

  const getRecommendationWarning = () => {
    const recommendation = isOverprovisionedWarning()
      ? getOverprovisionedRecommendation()
      : getUnderprovisionedRecommendation();
    const recommendationWarning: ProvisionedProductRecommendationWarning = {
      recommendationMessage: recommendation,
      recommendedInstanceType: recommendedParamMetadata(),
    };
    return recommendationWarning;
  };

  const recommendation: ProvisionedProductRecommendationWarning =
    getRecommendationWarning();

  const handleRemoveProvisionedProduct = async (projectId: string, provisionedProductId: string) => {
    if (!projectId) {
      throw new Error('No project selected');
    }
    if (!provisionedProductId) {
      throw new Error('No provisioned product id');
    }
    return props.serviceAPI.removeProvisionedProduct(
      projectId,
      provisionedProductId
    );
  };

  return {
    ...{
      isLoading: isLoadingProvProd,
      provisionedProduct,
      parameters,
      recommendation,
      stopConfirmVisible,
      setStopConfirmVisible,
      isOverprovisionedWarning,
      mutate,
      handleRemoveProvisionedProduct: handleRemoveProvisionedProduct,
    },
    ...commonHookRes,
    ...commonStateHookRes,
  };
};
