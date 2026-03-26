import { SpaceBetween } from '@cloudscape-design/components';
import { provisioningAPI } from '../../../services';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { useProvisionedProductsAdministration } from './logic';
import { i18n } from './translations';
import {
  ProvisionedProductsAdministrationHeader,
  ProvisionedProductsAdministrationTools,
  ProvisionedProductsList,
  ProvisionedProductsListActions,
  ProvisionedProductsOverview,
} from './components';

export const ProvisionedProductsAdministration = () => {
  const {
    breadcrumbItems,
    provisionedProducts,
    provisionedProductsLoading,
    provisionedProductsTableProps,
    selectedProvisionedProductsTableProps,
    productOptions,
    selectedProductOption,
    setSelectedProductOption,
    productTypeOptions,
    selectedProductTypeOption,
    setSelectedProductTypeOption,
    statusOptions,
    selectedStatusOption,
    setSelectedStatusOption,
    additionalInformationOptions,
    selectedAdditionalInformationOption,
    setSelectedAdditionalInformationOption,
    reloadProvisionedProducts,
    stopActionDisabled,
    stopProvisionedProductsPromptOpen,
    setStopProvisionedProductsPromptOpen,
    stopProvisionedProductsInProgress,
    stopProvisionedProducts,
    terminateActionDisabled,
    terminateProvisionedProductsPromptOpen,
    setTerminateProvisionedProductsPromptOpen,
    terminateProvisionedProductsInProgress,
    terminateProvisionedProducts,
    getSelectedProvisionedProducts,
  } = useProvisionedProductsAdministration({
    serviceAPI: provisioningAPI,
    translations: i18n,
  });

  const renderContent = () => {
    return (
      <>
        <SpaceBetween direction="vertical" size="s">
          <ProvisionedProductsOverview
            translations={i18n}
            provisionedProducts={provisionedProducts}
            provisionedProductsLoading={provisionedProductsLoading}
          />
          <ProvisionedProductsList
            translations={i18n}
            tableProps={provisionedProductsTableProps}
            tableLoading={provisionedProductsLoading}
            productOptions={productOptions}
            selectedProductOption={selectedProductOption}
            setSelectedProductOption={setSelectedProductOption}
            productTypeOptions={productTypeOptions}
            selectedProductTypeOption={selectedProductTypeOption}
            setSelectedProductTypeOption={setSelectedProductTypeOption}
            statusOptions={statusOptions}
            selectedStatusOption={selectedStatusOption}
            setSelectedStatusOption={setSelectedStatusOption}
            additionalInformationOptions={additionalInformationOptions}
            selectedAdditionalInformationOption={
              selectedAdditionalInformationOption
            }
            setSelectedAdditionalInformationOption={setSelectedAdditionalInformationOption}
            tableActions={
              <ProvisionedProductsListActions
                getSelectedProvisionedProducts={getSelectedProvisionedProducts}
                translations={i18n}
                reloadProvisionedProducts={reloadProvisionedProducts}
                provisionedProductsLoading={provisionedProductsLoading}
                selectedProvisionedProductsTableProps={
                  selectedProvisionedProductsTableProps
                }
                stopActionDisabled={stopActionDisabled}
                stopProvisionedProductsPromptOpen={
                  stopProvisionedProductsPromptOpen
                }
                setStopProvisionedProductsPromptOpen={
                  setStopProvisionedProductsPromptOpen
                }
                stopProvisionedProductsInProgress={
                  stopProvisionedProductsInProgress
                }
                stopProvisionedProducts={stopProvisionedProducts}
                terminateActionDisabled={terminateActionDisabled}
                terminateProvisionedProductsPromptOpen={
                  terminateProvisionedProductsPromptOpen
                }
                setTerminateProvisionedProductsPromptOpen={
                  setTerminateProvisionedProductsPromptOpen
                }
                terminateProvisionedProductsInProgress={
                  terminateProvisionedProductsInProgress
                }
                terminateProvisionedProducts={terminateProvisionedProducts}
              />
            }
          />
        </SpaceBetween>
      </>
    );
  };

  return (
    <WorkbenchAppLayout
      breadcrumbItems={breadcrumbItems}
      content={renderContent()}
      contentType="default"
      tools={<ProvisionedProductsAdministrationTools {...i18n} />}
      customHeader={<ProvisionedProductsAdministrationHeader {...i18n} />}
    />
  );
};
