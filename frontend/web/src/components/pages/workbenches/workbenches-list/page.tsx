import { ProvisionedProduct } from '../../../../services/API/proserve-wb-provisioning-api';
import { provisioningAPI } from '../../../../services/API/provisioning-api';
import {
  MyProvisionedProducts,
  ProvisionedProductCardActions,
  useProvisionedProducts
} from '../../provisioned-products';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { i18n } from './translations';
import { i18nWorkbenchLogin } from '../../provisioned-products/provisioned-product-actions';

export const MyWorkbenches = () => {
  const props = {
    serviceAPI: provisioningAPI,
    provisionedProductDetailsRouteName: RouteNames.WorkbenchDetails,
    availableProvisionedProductRouteName: RouteNames.AvailableWorkbenches,
    productType: 'workbench',
    translations: i18n,
    upgradePage: RouteNames.UpgradeWorkbenchV2,
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
          translations={i18n}
          loginTranslations={i18nWorkbenchLogin}
          stateActionCompleteHandler={refreshWorkbenches}
          productType={props.productType}
        />
      ,
    },
  ];

  return <MyProvisionedProducts
    {...props}
    additionalCardDefinitionSections={additionalCardDefinitionSections}
    translations={i18n}
  />;
};
