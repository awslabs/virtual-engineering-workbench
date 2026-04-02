// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { FC, ReactNode, useState } from 'react';
import {
  Button,
  Cards,
  CardsProps,
  Header,
  HelpPanel,
  Pagination,
  PropertyFilter,
  PropertyFilterProps,
  Box,
  SpaceBetween,
  Select,
  FormField,
  Spinner,
  Table,
  TextFilter,
  NonCancelableCustomEvent,
} from '@cloudscape-design/components';
import { BreadcrumbItem } from '../../../layout';
import { AvailableProduct } from '../../../../services/API/proserve-wb-provisioning-api';
import {
  AvailableProductsTranslations,
  ServiceAPI,
  useAvailableProducts
} from './available-products-new.logic';
import { EmptyGridNotification } from '../../shared/empty-grid-notification';
import { NoMatchGridNotification } from '../../shared/no-match-grid-notification';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { useFeatureToggles } from '../../../feature-toggles/feature-toggle.hook';
import { RoleAccessToggle } from '../../shared/role-access-toggle';
import { RoleBasedFeature } from '../../../../state';
import { Feature } from '../../../feature-toggles/feature-toggle.state';
import { EnabledRegion, REGION_NAMES, STAGES, UserPreferences } from '../../../user-preferences';
import { FeatureToggle } from '../../shared/feature-toggle';
import { useRoleAccessToggle } from '../../../../hooks/role-access-toggle';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { NoMatchTableNotification } from '../../shared/no-match-table-notification';
import styles from './available-products-new.module.scss';
/* eslint @typescript-eslint/no-magic-numbers: "off" */



const DEFAULT_GRID_PAGE_SIZE = 12;

const propertyFilterI18nStrings: PropertyFilterProps.I18nStrings = {
  filteringAriaLabel: 'Filter',
  dismissAriaLabel: 'Dismiss',
  filteringPlaceholder: 'Find workbenches or tools',
  groupValuesText: 'Values',
  groupPropertiesText: 'Properties',
  operatorsText: 'Operators',
  operationAndText: 'and',
  operationOrText: 'or',
  operatorLessText: 'Less than',
  operatorLessOrEqualText: 'Less than or equal',
  operatorGreaterText: 'Greater than',
  operatorGreaterOrEqualText: 'Greater than or equal',
  operatorContainsText: 'Contains',
  operatorDoesNotContainText: 'Does not contain',
  operatorEqualsText: 'Equals',
  operatorDoesNotEqualText: 'Does not equal',
  editTokenHeader: 'Edit filter',
  propertyText: 'Property',
  operatorText: 'Operator',
  valueText: 'Value',
  cancelActionText: 'Cancel',
  applyActionText: 'Apply',
  allPropertiesLabel: 'All properties',
  tokenLimitShowMore: 'Show more',
  tokenLimitShowFewer: 'Show fewer',
  clearFiltersText: 'Clear filters',
  removeTokenButtonAriaLabel: token => `Remove token ${token.propertyKey} ${token.operator} ${token.value}`,
  enteredTextLabel: text => `Use: "${text}"`,
};
type ProductSelectedEvent = NonCancelableCustomEvent<CardsProps.SelectionChangeDetail<AvailableProduct>>;

interface AvailableProductsProps {
  productType: string,
  i18n: AvailableProductsTranslations,
  availableProductsServiceApi: ServiceAPI,
}

export const AvailableProductsNew: FC<AvailableProductsProps> = ({
  productType,
  i18n,
  availableProductsServiceApi,
}: AvailableProductsProps) => {
  const { navigateTo, getPathFor } = useNavigationPaths();
  const { isFeatureEnabled } = useFeatureToggles();
  const [preferencesVisible, setPreferencesVisible] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const isFeatureAccessible = useRoleAccessToggle();

  const {
    availableProductsLoading,
    filteredProducts,
    collectionProps,
    propertyFilterProps,
    paginationProps,
    resetFilter,
    selectedProducts,
    setSelectedProducts,
    selectedRegion,
    setSelectedRegion,
    availableRegions,
    selectedStage,
    setSelectedStage,
    availableStages,
    canListOnlyProd,
    selectedVersionStage,
    setSelectedVersionStage,
    selectedProduct,
    setSelectedProduct,
    selectedProductVersionTools,
    selectedVersionOption,
    setSelectedVersionOption,
    selectedVersionOptions,
    selectedVersionOptionsIsLoading,
    setlocalStorageSelectedStage,
    setlocalStorageSelectedRegion
  } = useAvailableProducts({
    pageSize: DEFAULT_GRID_PAGE_SIZE,
    emptyGridNotification: <EmptyGridNotification
      title={i18n.noProducts}
      subTitle={i18n.noProductsLong} />,
    noMatchGridNotification: <NoMatchGridNotification
      title={i18n.noProductsFound}
      clearButtonText={i18n.clearFilter}
      clearButtonAction={() => resetFilter()} />,
    serviceAPI: availableProductsServiceApi,
    productType,
    i18n,
  });

  const COLUMN_DEFINITION = [
    {
      id: 'name',
      header: i18n.tableHeaderToolsName,
      cell: (item: { name: string }) => item.name,
      sortingField: 'name'
    },
    {
      id: 'version',
      header: i18n.tableHeaderToolsVersion,
      cell: (item: { version: string }) => item.version,
      sortingField: 'version'
    },
  ];


  const {
    items,
    actions,
    filterProps,
    collectionProps: collectionPropsTable,
    // paginationProps: paginationPropsTable
  } = useCollection(
    selectedProductVersionTools || [],
    {
      filtering: {
        empty: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => resetFilterToolsTable()}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle}
        />,
        noMatch: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => resetFilterToolsTable()}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle} />,
      },
      selection: {},
      sorting: { defaultState: { sortingColumn: COLUMN_DEFINITION[0] } },
      // pagination: { pageSize: DEFAULT_PAGE_SIZE },
    }
  );

  function resetFilterToolsTable() {
    actions.setFiltering('');
  }

  function handleViewComponentDetailsButton(item: AvailableProduct) {
    setSelectedProduct(item);
    setToolsOpen(true);
  }

  function handleCloseHelpPanel() {
    setToolsOpen(false); // Close the HelpPanel manually
    setSelectedProduct(null); // Clear selected product
  }

  function getDropdownOption(input: string) {
    return {
      label: REGION_NAMES[input as EnabledRegion || 'unspecified'] || input, value: input
    };
  }

  const selectedRegionOption = getDropdownOption(selectedRegion);
  const selectedStageOption = getDropdownOption(selectedStage);

  const regionOptions = availableRegions.map(getDropdownOption);
  const stageOptions = availableStages.map(getDropdownOption);

  function displayToolsPanel() {
    return toolsOpen && selectedProduct && isFeatureEnabled(Feature.ProductMetadata);
  }

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={getBreadcrumbItems()}
        content={renderContent()}
        contentType="cards"
        tools={renderTools()}
        toolsOpen={toolsOpen}
        onToolsChange={(evt) => {
          setToolsOpen(evt.detail.open);
          if (!evt.detail.open) {
            handleCloseHelpPanel(); // Catch hide event and handle closing actions
          }
        }}
        toolsWidth={displayToolsPanel() ? 340 : 290}
      />
      <UserPreferences
        visible={preferencesVisible}
        onDismiss={() => setPreferencesVisible(false)}
        onConfirmSuccess={() => setPreferencesVisible(false)}
      />
    </>

  );

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.AvailableWorkbenches) },
    ];
  }


  function canCreateWorkbench() {
    return true;
  }

  function getOSImages(osVersions: string[]): JSX.Element[] {
    // Use a Set to avoid duplicate images
    const images: JSX.Element[] = [];

    for (const os of osVersions) {
      images.push(getOsImge(os.toLocaleLowerCase()));

    }
    return images.length > 0 ? images : [<Box key="na"></Box>];
  }

  function getOsImge(osname: string): JSX.Element {
    if (osname.includes('ubuntu')) {
      return <img key="ubuntu" src='/ubuntu.svg' width={30} height={30} alt='Ubuntu' />;
    }
    if (osname.includes('windows')) {
      return <img key="windows" src='/windows.svg' width={30} height={30} alt='Windows' />;
    }
    if (osname.includes('blackberry')) {
      return <img key="blackberry" src='/blackberry.svg' width={30} height={30} alt='Blackberry' />;
    }
    return <Box>N/A</Box>;
  }



  function renderHeader(item: AvailableProduct) {
    return (
      <div className={styles['card-header']}>
        {item.productName}
        <div className={styles['card-header-os-icons']}>
          <FeatureToggle feature={Feature.ProductMetadata}>
            {getOSImages(item.availableOSVersions || [])}
          </FeatureToggle>
        </div>
      </div>
    );
  }

  function renderContent() {
    const cardDefinition: CardsProps.CardDefinition<AvailableProduct> = {
      header: (e) => renderHeader(e),
      sections: [
        {
          id: 'description',
          content(item: AvailableProduct): ReactNode {
            return <div className={styles['card-fields']}>
              {item.productDescription}
            </div>;
          }
        },
        {
          id: 'provisioningTime',
          header: i18n.availableProductProvisioningTime,
          content(item: AvailableProduct): ReactNode {
            return <div className={styles['card-fields-1line']}>
              {renderProvisioningTime(item)}
            </div>;
          }
        },
        {
          id: 'actions',
          content(item: AvailableProduct): ReactNode {
            return <div className={styles['card-footer']}>
              <Box float='right'>
                <SpaceBetween size='s' direction='horizontal'>
                  {isFeatureEnabled(Feature.ProductMetadata) &&
                    <Button
                      variant='link'
                      data-test={`preview-${item.productName}`}
                      data-action={`preview-${item.productName}`}
                      onClick={() => handleViewComponentDetailsButton(item)} // Handle button click
                    >
                      {i18n.actionToolsPreview}
                    </Button>
                  }
                  <RoleAccessToggle feature={RoleBasedFeature.ProvisionWorkbench}>
                    <Button
                      data-test={`create-${item.productName}`}
                      data-action={`create-${item.productName}`}
                      variant='primary'
                      disabled={!canCreateWorkbench()}
                      onClick={() => {
                        type ProductType = 'WORKBENCH' | 'VIRTUAL_TARGET' | 'CONTAINER';

                        const isProductType = (value: string): value is ProductType => {
                          return ['WORKBENCH', 'VIRTUAL_TARGET', 'CONTAINER'].includes(value);
                        };

                        const commonNavigationParams = {
                          productDescription: item.productDescription,
                          productType: item.productType,
                          availableRegions: item.availableRegions,
                          availableStages: item.availableStages,
                          productName: item.productName,
                        };

                        const routeMap = {
                          WORKBENCH: RouteNames.ProvisionWorkbench,
                          VIRTUAL_TARGET: RouteNames.ProvisionWorkbench,
                          CONTAINER: RouteNames.ProvisionWorkbench
                        };

                        if (isProductType(item.productType)) {
                          const route = routeMap[item.productType];
                          if (route) {
                            navigateTo(
                              route,
                              { ':id': item.productId },
                              commonNavigationParams
                            );
                          }
                        }
                      }}>
                      {i18n.actionProvision}
                    </Button>
                  </RoleAccessToggle>
                </SpaceBetween>
              </Box>
            </div>;
          }
        }
      ]
    };

    function renderProvisioningTime(item: AvailableProduct) {
      const itemProvisioningTime = item.averageProvisioningTime;
      if (itemProvisioningTime) {
        if (itemProvisioningTime > 59) {
          const minutesShown = Math.floor(itemProvisioningTime / 60);
          const secondsShown = itemProvisioningTime % 60;
          if (secondsShown > 0) {
            return `${minutesShown} min ${secondsShown} s`;
          }
          return `${minutesShown} minutes`;
        }
        return `${itemProvisioningTime} seconds`;
      }
      return i18n.noProvisioningTime;
    }

    // State to store search query and filtered products
    const filterDefinition: ReactNode = <div className='inputs'>
      <SpaceBetween size={'s'} direction='horizontal'>
        <FormField label='&nbsp;'>
          <div className='filter'>
            <PropertyFilter
              data-test="input-filter"
              {...propertyFilterProps}
              i18nStrings={propertyFilterI18nStrings}
              expandToViewport
              hideOperations
              tokenLimit={2}
            />
          </div>
        </FormField>
        <FormField label={i18n.selectRegion}>
          <Select
            data-test="select-region"
            selectedOption={selectedRegionOption}
            onChange={({ detail }) => {
              setlocalStorageSelectedRegion(detail.selectedOption.value ?? '');
              setSelectedRegion(detail.selectedOption.value ?? '');
            }}
            options={regionOptions}
          />
        </FormField>
        {!canListOnlyProd() &&
          <FormField label={i18n.selectStage}>
            <Select
              data-test="select-stage"
              selectedOption={selectedStageOption}
              onChange={({ detail }) => {
                setlocalStorageSelectedStage(detail.selectedOption.value ?? '');
                setSelectedStage(detail.selectedOption.value ?? '');
              }}
              options={stageOptions}
            />
          </FormField>
        }
      </SpaceBetween>
    </div>;

    const paginationDefinition: ReactNode = <Pagination {...paginationProps} />;

    const headerDefinition: ReactNode = <Header variant='awsui-h1-sticky'>
      {i18n.headerTitle}
    </Header>;

    const cardLayoutDefinition: CardsProps.CardsLayout[] = [
      { cards: 1 },
      { minWidth: 600, cards: 2 },
      { minWidth: 900, cards: 3 },
      { minWidth: 1200, cards: 4 },
    ];

    return <>
      <Cards
        data-test="product-card"
        {...collectionProps}
        ariaLabels={{
          itemSelectionLabel: (_, t) => `select ${t.productName}`,
          selectionGroupLabel: i18n.productSelection
        }}
        cardDefinition={cardDefinition}
        cardsPerRow={cardLayoutDefinition}
        items={filteredProducts}
        loadingText={i18n.loadingProducts}
        loading={availableProductsLoading}
        trackBy="productId"
        filter={filterDefinition}
        header={headerDefinition}
        stickyHeader={true}
        pagination={paginationDefinition}
        selectedItems={selectedProducts}
        onSelectionChange={
          (event: ProductSelectedEvent) => setSelectedProducts(event.detail.selectedItems)}
        variant='full-page'
      />
    </>;
  }

  function renderTools(): ReactNode {
    if (selectedProduct && isFeatureEnabled(Feature.ProductMetadata)) {
      return renderToolsProductTools(selectedProduct, i18n);
    }
    return renderToolsDefault();
  }

  function renderToolsProductTools(
    selectedProduct: AvailableProduct,
    i18n: AvailableProductsTranslations): ReactNode {
    return (
      <HelpPanel
        header={<Header variant="h2">{i18n.helpPanelProductToolsDetails}</Header>}
      >
        <div className={styles['form-content']}>
          <Box>
            <SpaceBetween size='m' direction='vertical'>
              <h4>{selectedProduct.productName}</h4>
              <SpaceBetween size='m' direction='vertical'>
                <label>{i18n.helpPanelStaticDescription}</label>
                {renderStageSelector()}
                <SpaceBetween size="s">
                  {renderProductVersionSelector()}
                  {renderToolsTable()}
                </SpaceBetween>
              </SpaceBetween>
            </SpaceBetween>
          </Box>
        </div>
      </HelpPanel>
    );
  }
  function renderToolsDefault(): ReactNode {
    return (
      <HelpPanel>
        <h2>{i18n.helpPanelHeader}</h2>
        <p>{i18n.helpPanelDetails}</p>
      </HelpPanel>
    );
  }

  // stage selector for the helper panel
  function renderStageSelector() {
    if (!selectedProduct) { return null; }
    return (
      <>
        {isFeatureAccessible(RoleBasedFeature.ChooseStageInProductSelection) &&
          <FormField label={i18n.formFieldStageHeader}>
            <div id={styles['form-dropdown']}>
              <Select
                selectedOption={getStageOption(selectedVersionStage ?? '')}
                onChange={({ detail }) => {
                  setSelectedVersionStage?.(detail.selectedOption.value || '');
                }}
                options={selectedProduct?.availableStages!.map(stage => {
                  return {
                    label: getStageLabel(stage),
                    value: stage,
                  };
                })}
                selectedAriaLabel="Selected"
                data-test="select-stage"
              />
            </div>
          </FormField>
        }
      </>
    );
  }

  function getStageOption(stage: string) {
    return {
      label: STAGES[stage], // label is correctly set as a string here
      value: stage,
    };
  }

  function getStageLabel(stage: string) {
    return STAGES[stage];
  }

  // Product version for the help panel
  function renderProductVersionSelector() {
    // Determine if there are no options
    const noOptionsAvailable = !selectedVersionOptions || selectedVersionOptions.length === 0;

    return (
      <>
        <FormField label={i18n.formFieldVersionHeader}>
          <div id={styles['form-dropdown']} style={{ position: 'relative' }}>
            {selectedVersionOptionsIsLoading &&
              <div className={styles.selectSpinner}>
                <Spinner />
              </div>
            }
            <Select
              selectedOption={selectedVersionOption || selectedVersionOptions[0]}
              onChange={({ detail }) =>
                setSelectedVersionOption(detail.selectedOption)
              }
              options={selectedVersionOptions}
              selectedAriaLabel="Selected"
              data-test="select-version"
              disabled={noOptionsAvailable}
            // Optionally add a `loading` state to `Select` if supported
            />
          </div>
        </FormField>
      </>
    );
  }
  function renderSpinner() {
    if (selectedVersionOptionsIsLoading) {
      return (
        <div className={styles.tableSpinner}>
          <Spinner size="large" />
        </div>
      );
    }
    return null;
  }

  function renderEmptyContent() {
    if (!selectedProductVersionTools || selectedProductVersionTools.length === 0 || !selectedVersionOptions) {
      return (
        <Box margin={{ vertical: 'xxxs' }} textAlign="center" color="inherit">
          <SpaceBetween size="xxs">
            <b>{i18n.tableNoResources}</b>
          </SpaceBetween>
        </Box>
      );
    }
    return null;
  }

  function renderTableContent() {
    return (
      <SpaceBetween direction="vertical" size="l">
        <TextFilter
          {...filterProps}
          filteringAriaLabel={i18n.filterToolsPlaceholder}
          filteringPlaceholder={i18n.filterToolsPlaceholder}
        />
        <Table
          data-test="tools-table"
          {...collectionPropsTable}
          columnDefinitions={COLUMN_DEFINITION}
          items={items}
          loadingText={i18n.tableLoadingResources}
          selectionType={undefined}
          variant="borderless"
          stickyHeader={true}
        />
      </SpaceBetween>
    );
  }

  function renderToolsTable() {
    return (
      renderSpinner() ||
      renderEmptyContent() ||
      renderTableContent()
    );
  }


};

