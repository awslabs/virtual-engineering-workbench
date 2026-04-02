import { useEffect, useState } from 'react';
import { extractErrorResponseMessage } from '../../../../utils/api-helpers';
import { useNotifications } from '../../../layout';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { useRecoilValue } from 'recoil';
import { RoleBasedFeature, selectedProjectState } from '../../../../state';
import {
  GetAvailableProductsResponse,
  AvailableProduct,
  GetAvailableProductVersionsResponse,
  AvailableVersionDistribution
} from '../../../../services/API/proserve-wb-provisioning-api';
import { useRoleAccessToggle } from '../../../../hooks/role-access-toggle';
import { i18nWorkbench } from './available-products-new.workbench.translations';
import { i18nVirtualTarget } from './available-products-new.virtual-targets.translations';
import { SelectProps } from '@cloudscape-design/components';
import { compareSemanticVersions } from '../../../../hooks/provisioning';
import { useLocalStorage } from '../../../../hooks';

export type AvailableProductsTranslations = typeof i18nWorkbench | typeof i18nVirtualTarget;
const DEFAULT_REGION = 'us-east-1';
enum Stages {
  DEV = 'DEV',
  QA = 'QA',
  PROD = 'PROD'
}


interface Version {
  versionId: string,
  versionName: string,
  versionDescription?: string,
  isRecommendedVersion: boolean,
}


export interface ServiceAPI {
  getAvailableProducts: (projectId: string, productType: string) => Promise<GetAvailableProductsResponse>,
  getAvailableProductVersions: (
    projectId: string,
    productId: string,
    stage: string,
    region: string
  ) => Promise<GetAvailableProductVersionsResponse>,
}

interface Props {
  pageSize: number,
  emptyGridNotification: JSX.Element,
  noMatchGridNotification: JSX.Element,
  serviceAPI: ServiceAPI,
  productType: string,
  i18n: AvailableProductsTranslations,
}

interface OptionDefinition {
  label: string,
  value: string,
}

export function useAvailableProducts({
  pageSize,
  emptyGridNotification,
  noMatchGridNotification,
  serviceAPI,
  productType,
  i18n,
}: Props) {

  const [availableProducts, setAvailableProducts] = useState<AvailableProduct[]>([]);
  const [availableProductVersions,
    setAvailableProductVersions] = useState<AvailableVersionDistribution[]>([]);
  const [availableProductsLoading, setAvailableProductsLoading] = useState(false);
  const [availableProductVersionsLoading, setavailableProductVersionsLoading] = useState(false);
  const [selectedProducts, setSelectedProducts] = useState<AvailableProduct[]>([]);
  const selectedProject = useRecoilValue(selectedProjectState);
  const [selectedRegion,
    setSelectedRegion] = useState<string>(i18n.firstRegionDropdownOption);
  const [selectedStage,
    setSelectedStage] = useState<string>(i18n.firstStageDropdownOption);
  const isFeatureAccessible = useRoleAccessToggle();
  const [selectedProduct, setSelectedProduct] = useState<AvailableProduct | null>(null);
  const [selectedVersionRegion,
    setSelectedVersionRegion] = useState<string | undefined>(selectedProduct?.availableStages[0]);
  const [selectedVersionStage,
    setSelectedVersionStage] = useState<string | undefined>(DEFAULT_REGION);
  const [selectedVersionOptions, setSelectedVersionOptions] = useState<OptionDefinition[]>([]);
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [localStorageSelectedStage, setlocalStorageSelectedStage] = useLocalStorage('selectedStage');
  const [localStorageSelectedRegion, setlocalStorageSelectedRegion] = useLocalStorage('selectedRegion');

  const [selectedProductVersionTools,
    setSelectedProductVersionTools] = useState<{
      name: string,
      version: string,
    }[] | undefined>(undefined);

  const [selectedVersionOption, setSelectedVersionOption] = useState<SelectProps.Option>();
  const [selectedVersionOptionsIsLoading, setselectedVersionOptionsIsLoading] = useState<boolean>(true);

  const { showErrorNotification, clearNotifications } = useNotifications();

  const filteredProducts = filterProducts(
    availableProducts.filter(item =>
      (item.availableStages?.includes(selectedStage) || selectedStage === i18n.firstStageDropdownOption) &&
      (item.availableRegions?.includes(selectedRegion) || selectedRegion === i18n.firstRegionDropdownOption)
    ),
    searchFilter
  );

  const {
    items,
    actions,
    filteredItemsCount,
    collectionProps,
    propertyFilterProps,
    paginationProps,
  } = useCollection(filteredProducts, {
    propertyFiltering: {
      empty: emptyGridNotification,
      noMatch: noMatchGridNotification,
      filteringProperties: [
        {
          key: 'productName',
          operators: ['=', ':', '!='],
          propertyLabel: 'Name',
          groupValuesLabel: 'Name values',
        },
        {
          key: 'availableTools',
          operators: ['=', ':', '!='],
          propertyLabel: 'Tools',
          groupValuesLabel: 'Tools values',
        },
      ],
    },
    pagination: { pageSize },
    selection: {},
  });

  function filterProducts(products: AvailableProduct[], searchFilter: string): AvailableProduct[] {
    if (!searchFilter) {
      return products;
    }

    const filteredProducts = products.filter(product => {
      const matchesTool = product.availableTools?.some(tool =>
        tool.toLowerCase().includes(searchFilter.toLowerCase()));
      const matchesName = product.productName?.toLowerCase().includes(searchFilter.toLowerCase());
      return matchesTool || matchesName;
    });
    return filteredProducts;
  }

  function handleFilterChange(newFilter: string) {
    setSearchFilter(newFilter);
  }

  const stagesOfAvailableProducts = availableProducts.reduce((prev, curr) =>
    new Set<string>([...prev, ...curr.availableStages || []]), new Set<string>([]));
  const availableStages = [i18n.firstStageDropdownOption, ...stagesOfAvailableProducts];

  const regionsOfAvailableProducts = availableProducts.
    reduce((prev, curr) => new Set<string>([...prev, ...curr.availableRegions || []]), new Set<string>([]));

  const availableRegions = [i18n.firstRegionDropdownOption, ...regionsOfAvailableProducts];

  function defaultIfNull<T>(value: T, defaultValue: T) {
    return value ?? defaultValue;
  }


  useEffect(() => {
    if (!selectedProject?.projectId || availableProductsLoading) {
      return;
    }

    clearNotifications();
    resetFilter();
    setAvailableProductsLoading(true);

    serviceAPI.getAvailableProducts(selectedProject.projectId, productType).then(data => {
      setAvailableProducts(defaultIfNull(data.availableProducts, []).
        filter(filterByUserVisibility).
        map(p => ({
          productId: p.productId,
          productName: p.productName,
          productDescription: defaultIfNull(p.productDescription, ''),
          productType: defaultIfNull(p.productType, ''),
          availableRegions: p.availableRegions,
          availableStages: defaultIfNull(p.availableStages, []),
          availableOSVersions: defaultIfNull(p.availableOSVersions, []),
          availableTools: defaultIfNull(p.availableTools, []),
          averageProvisioningTime: p.averageProvisioningTime,
          totalReportedTimes: p.totalReportedTimes,
        })));
    }).catch(async e => {
      showErrorNotification({
        header: i18n.errorFetchAvailableProducts,
        content: await extractErrorResponseMessage(e),
      });
      setAvailableProducts([]);
    }).finally(() => {
      setAvailableProductsLoading(false);
    });
  }, [selectedProject, productType]);

  useEffect(() => {
    if (!selectedProduct) { return; }
    setSelectedVersionStage(selectedProduct.availableStages[0]);
    setSelectedVersionRegion(DEFAULT_REGION);
  }, [selectedProduct]);

  useEffect(() => {
    if (!selectedProduct || !selectedVersionStage || !selectedVersionRegion) {
      return;
    }
    setSelectedVersionOption(undefined);
    getSelectedProductVersions(selectedProduct.productId, selectedVersionStage, selectedVersionRegion);
  }, [selectedProduct, selectedVersionStage, selectedVersionRegion]);

  useEffect(() => {
    if (!selectedVersionOptions) {
      return;
    }
    setSelectedVersionOption(selectedVersionOptions[0]);

  }, [selectedVersionOptions]);

  useEffect(() => {
    if (!selectedVersionOption) {
      setSelectedProductVersionTools([]);
      return;
    }
    const tools = getComponentVersionDetailsByVersionName(selectedVersionOption.value || '');
    setSelectedProductVersionTools(tools || []);

  }, [selectedVersionOption]);

  return {
    availableProductsLoading,
    filteredProducts: items,
    filteredProductsCount: filteredItemsCount,
    collectionProps,
    propertyFilterProps,
    paginationProps,
    setFreeTextFilter: (filter: string) => actions.setFiltering(filter),
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
    selectedProduct,
    setSelectedProduct,
    availableProductVersions,
    setAvailableProductVersions,
    availableProductVersionsLoading,
    setavailableProductVersionsLoading,
    getSelectedProductVersions,
    selectedVersionRegion,
    setSelectedVersionRegion,
    selectedVersionStage,
    setSelectedVersionStage,
    selectedProductVersionTools,
    setSelectedProductVersionTools,
    selectedVersionOption,
    setSelectedVersionOption,
    selectedVersionOptions,
    setSelectedVersionOptions,
    selectedVersionOptionsIsLoading,
    searchFilter,
    handleFilterChange,
    localStorageSelectedStage,
    setlocalStorageSelectedStage,
    localStorageSelectedRegion,
    setlocalStorageSelectedRegion
  };

  async function getSelectedProductVersions(
    productId: string,
    stage: string,
    region: string
  ) {
    setSelectedVersionOptions([]);
    setavailableProductVersionsLoading(true);
    setselectedVersionOptionsIsLoading(true);
    if (!isValidRequest(productId)) {
      resetProductVersions();
      return [];
    }

    try {
      const data = await fetchProductVersions(productId, stage, region);
      processProductVersions(data);
    } catch (e) {
      handleFetchError(e);
    } finally {
      setavailableProductVersionsLoading(false);
      setselectedVersionOptionsIsLoading(false);

    }
    return availableProductVersions;
  }

  function isValidRequest(productId: string): boolean {
    return !!productId && !!selectedProject.projectId;
  }

  function resetProductVersions(): void {
    setAvailableProductVersions([]);
    setSelectedVersionOptions([]);
  }

  async function fetchProductVersions(
    productId: string,
    stage: string,
    region: string
  ): Promise<any> {
    if (!selectedProject.projectId) {
      return Promise.resolve([]); // Return a resolved promise with an empty array or any default value
    }
    return serviceAPI.getAvailableProductVersions(
      selectedProject.projectId,
      productId,
      stage,
      region
    );
  }


  function processProductVersions(data: any): void {
    setAvailableProductVersions(data.availableProductVersions || []);
    setSelectedVersionOptions(mapVersions(data.availableProductVersions) as OptionDefinition[]);
  }

  async function handleFetchError(e: any): Promise<void> {
    showErrorNotification({
      header: i18n.errorFetchAvailableProductVersions,
      content: await extractErrorResponseMessage(e),
    });
    resetProductVersions();
  }


  function filterByUserVisibility(p: AvailableProduct): boolean {
    if (canListOnlyProd()) {
      return p.availableStages?.includes(Stages.PROD);
    }
    if (canListOnlyProdAndQa()) {
      return p.availableStages?.includes(Stages.PROD) || p.availableStages?.includes(Stages.QA);
    }
    return true;
  }

  function canListOnlyProd() {
    return !isFeatureAccessible(RoleBasedFeature.ListAllProducts) &&
      !isFeatureAccessible(RoleBasedFeature.ListProdAndQaProducts);
  }

  function canListOnlyProdAndQa() {
    return !isFeatureAccessible(RoleBasedFeature.ListAllProducts) &&
      isFeatureAccessible(RoleBasedFeature.ListProdAndQaProducts);
  }

  function resetFilter() {
    actions.setFiltering('');
    setSelectedRegion(availableRegions[0]);
    setSelectedStage(availableStages[0]);
  }

  function getComponentVersionDetailsByVersionName(versionName: string) {
    const version = availableProductVersions.find(
      version => version.versionId === versionName
    );
    if (version && version.componentVersionDetails) {
      return version.componentVersionDetails.map(component => ({
        name: component.componentName,
        version: component.softwareVersion
      }));
    }
    return null;

  }

  function mapVersions(versions: Version[]): SelectProps.Option[] {
    return versions.sort(compareSemanticVersions()).map<SelectProps.Option>(mapVersion);
  }

  function mapVersion(version: Version): SelectProps.Option {
    return {
      label: version.versionName || 'Unknown Version', // Ensure label is a non-empty string
      value: version.versionId,
      tags: [version.isRecommendedVersion ? i18n.recommendedVersionTag : '']
    };
  }
}