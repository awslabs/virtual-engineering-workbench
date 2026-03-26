import React from 'react';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout.tsx';
import { useProvisionedProducts } from './logic.ts';
import {
  Tools,
  ProvisionedProductHeaderActions,
  ProvisionedProductList,
  ProvisionedProductListHeader,
  ProvisionedProductsToDeleteList,
} from './components.tsx';
import { UserPrompt } from '../shared/user-prompt.tsx';
import { ProvisionedProduct } from '../../../services/API/proserve-wb-provisioning-api/index.ts';
import { EmptyGridNotification } from '../shared/index.ts';
import { ProvisionedProductsProps } from './interface.ts';
import { i18n } from './provisioned-product-actions/translations.ts';

/**
 * This component renders a generic list of provisioned products.
 *
 * @param {string} productType The product type ('Workbench' | 'VirtualTarget').
 * @param {CardsProps.SectionDefinition<ProvisionedProduct>[]|undefined} additionalCardDefinitionSections\
 *  This is the way to add your specific Difinition Sections
 * @returns {JSX.Element} A React element that renders a generic list of provisioned products.
 */
export const MyProvisionedProducts = (props: ProvisionedProductsProps) => {
  const {
    targets,
    crumbs,
    isInTurnDownMode,
    isLoading,
    isValidToTurnDown,
    turnDownConfirmVisible,
    selectionType,
    paginationProps,
    propertyFilterProps,
    collectionProps,
    turnDownTimeOutInProgress,
    turnDownInProgress,
    handleRemoveClick,
    handleRemoveCancel,
    handleRemoveSubmit,
    refreshWorkbenches,
    navigateToProductsScreen,
    handleRemoveConfirmSubmit,
    handleRemoveConfirmCancel,
    handleViewDetail,
    // isFeatureAccessible,
    isCardDisabled,
    isProvisionedProductListLoading,
    decideStatusIndicatorType,
    decideToHideUpgradeButton,
    decideToDisableUpgradeButton,
  } = useProvisionedProducts(props);

  const actions: React.ReactNode =
    <ProvisionedProductHeaderActions
      isInTurnDownMode={isInTurnDownMode}
      isLoading={isLoading}
      isValidToTurnDown={isValidToTurnDown}
      onCancelRemoveHandler={handleRemoveCancel}
      onRefreshHandler={refreshWorkbenches}
      onRemoveHandler={handleRemoveClick}
      onProvisionHandler={navigateToProductsScreen}
      onSubmitRemoveHandler={handleRemoveSubmit}
      translations={props.translations}
    />
  ;
  const header: React.ReactNode =
    <ProvisionedProductListHeader
      actions={actions}
      translations={props.translations}
    />
  ;
  const content: React.ReactNode =
    <>
      <ProvisionedProductList
        additionalCardDefinitionSections={
          props.additionalCardDefinitionSections
        }
        collectionProps={collectionProps}
        filterProps={propertyFilterProps}
        paginationProps={paginationProps}
        isCardDisabled={isCardDisabled}
        selectionType={selectionType}
        isLoading={isProvisionedProductListLoading}
        isInTurnDownMode={isInTurnDownMode}
        targets={targets}
        header={header}
        empty={
          <EmptyGridNotification
            title={props.translations.noProducts}
            subTitle={props.translations.noProductsLong}
            actionButtonText={props.translations.noProductsActionButtonText}
            actionButtonOnClick={navigateToProductsScreen}
          />
        }
        decideStatusIndicatorType={decideStatusIndicatorType}
        decideToHideUpgradeButton={decideToHideUpgradeButton}
        decideToDisableUpgradeButton={decideToDisableUpgradeButton}
        handleViewDetail={handleViewDetail}
        translations={props.translations}
        upgradePage={props.upgradePage}
        loginTranslations={i18n}
        stateActionCompleteHandler={refreshWorkbenches}
        productType={props.productType}
        disableCardMenu={props.disableCardMenu ?? false}
      />
      <UserPrompt
        onConfirm={handleRemoveConfirmSubmit}
        onCancel={handleRemoveConfirmCancel}
        headerText={props.translations.deprovisionModalHeader}
        content={
          <ProvisionedProductsToDeleteList
            targets={collectionProps.selectedItems as ProvisionedProduct[]}
            translations={props.translations}
          />
        }
        cancelText={props.translations.deprovisionModalCancel}
        confirmText={props.translations.deprovisionModalOK}
        confirmButtonLoading={turnDownInProgress || turnDownTimeOutInProgress}
        visible={turnDownConfirmVisible}
      />
    </>;

  return (
    <WorkbenchAppLayout
      breadcrumbItems={crumbs}
      content={content}
      contentType="cards"
      tools={<Tools {...props.translations} />}
    />
  );
};
