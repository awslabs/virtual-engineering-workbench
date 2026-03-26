import { ProvisionedProduct } from '../../../../services/API/proserve-wb-provisioning-api';
import { provisioningAPI } from '../../../../services/API/provisioning-api';
import {
  MyProvisionedProducts,
  ProvisionedProductCardActions,
  useProvisionedProducts
} from '../../provisioned-products';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { i18nMyVirtualTargets } from '..';
import { i18nVirtualTargetLogin } from '../../provisioned-products/provisioned-product-actions';

export const MyVirtualTargets = () => {
  const props = {
    serviceAPI: provisioningAPI,
    provisionedProductDetailsRouteName: RouteNames.VirtualTargetDetails,
    availableProvisionedProductRouteName: RouteNames.AvailableVirtualTargets,
    productType: 'virtualTarget',
    translations: i18nMyVirtualTargets,
    upgradePage: RouteNames.UpgradeVirtualTarget,
  };
  const {
    isInTurnDownMode,
    handleViewDetail,
    isProvisionedProductListLoading,
    refreshWorkbenches,
  } = useProvisionedProducts(props);

  const additionalCardDefinitionSections = [
    {
      id: 'actions',
      content: (e: ProvisionedProduct) =>
        <ProvisionedProductCardActions
          state={e.status}
          isLoading={isProvisionedProductListLoading(e)}
          isInTurnDownMode={isInTurnDownMode}
          onViewDetailsHandler={() => handleViewDetail(e)}
          provisionedProduct={e}
          translations={i18nMyVirtualTargets}
          loginTranslations={i18nVirtualTargetLogin}
          headlessLogin
          stateActionCompleteHandler={refreshWorkbenches}
          productType={props.productType}
        />
      ,
    },
  ];

  return <MyProvisionedProducts
    {...props}
    additionalCardDefinitionSections={additionalCardDefinitionSections}
    translations={i18nMyVirtualTargets}
  />;
};
