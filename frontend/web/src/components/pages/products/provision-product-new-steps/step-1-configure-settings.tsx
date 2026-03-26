import {
  Alert,
  Box,
  Container,
  FormField,
  Header,
  Link,
  Pagination,
  Select,
  SelectProps,
  SpaceBetween,
  Table,
  TableProps,
  TextContent,
  TextFilter
} from '@cloudscape-design/components';
import { RoleBasedFeature } from '../../../../state';
import { FC, useState, useEffect } from 'react';
import { EnabledRegion, REGION_NAMES } from '../../../user-preferences';
import { compareSemanticVersions } from '../../../../hooks/provisioning';
import { useRoleAccessToggle } from '../../../../hooks/role-access-toggle';
import { useFeatureToggles } from '../../../feature-toggles/feature-toggle.hook';
import { Feature } from '../../../feature-toggles/feature-toggle.state';
import { StepsTranslations } from '../../../../hooks/provisioning/provision-product.logic';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { EmptyGridNotification, NoMatchTableNotification } from '../../shared';
import { useLocalStorage } from '../../../../hooks';
import { RegionSelect } from './region-select';

const EMPTY_ARRAY_COUNT = 0;
const PAGE_INDEX = 1;
const PAGE_SIZE = 20;

interface ComponentVersionDetails {
  componentName: string,
  componentVersionType: string,
  licenseDashboard?: string,
  notes?: string,
  softwareVendor: string,
  softwareVersion: string,
}

export interface Step1Version {
  componentVersionDetails?: Array<ComponentVersionDetails>,
  isRecommendedVersion: boolean,
  osVersion?: string,
  versionDescription?: string,
  versionId: string,
  versionName: string,
}

interface ProductVersionMetadataItem {
  label?: string,
  value?: string[],
}

export interface ProductVersionMetadata {
  [key: string]: ProductVersionMetadataItem,
}

const ProductVersionMetadataComponent: FC<{
  metadataKey: string,
  metadataValue: ProductVersionMetadataItem,
}> = ({ metadataKey, metadataValue }) => {
  if (!metadataValue.value) {
    return <></>;
  }
  return <TextContent key={metadataKey}>
    <Box variant="div">
      <Header variant="h3">
        {metadataValue.label || metadataKey}
      </Header>
      {metadataValue.value?.map(m => <Box variant="div" key={m}>
        {renderProductVersionMetadataItemValue(m)}
      </Box>)}
    </Box>
  </TextContent>;

  function renderProductVersionMetadataItemValue(metadataItem: string) {
    if (/http[s]{0,1}:\/\//gui.test(metadataItem)) {
      return <Link href={metadataItem} external>{metadataItem}</Link>;
    }
    return metadataItem;
  }
};

interface ConfigureSettingsStepParams {
  selectedVersionRegion: string,
  selectedVersionStage: string,
  selectedVersion?: Step1Version,
  selectedVersionValid: boolean,
  setSelectedVersionRegion?: (region: string) => void,
  setSelectedVersionStage?: (stage: string) => void,
  setSelectedVersion?: (version?: Step1Version) => void,
  availableRegions?: string[],
  availableStages?: string[],
  productVersions: Step1Version[],
  productVersionsLoading: boolean,
  showValidationErrors: boolean,
  disabled?: boolean,
  productVersionMetadata?: ProductVersionMetadata,
  i18nSteps: StepsTranslations,
  vvJobName?: string,
  vvPlatform?: string,
  vvVersion?: string,
  vvArtifactUpstreamPath?: string,
  productType?: string,
}

// eslint-disable-next-line complexity
const configureSettingsStep: FC<ConfigureSettingsStepParams> = ({
  selectedVersionRegion,
  selectedVersionStage,
  selectedVersion,
  selectedVersionValid,
  setSelectedVersionRegion,
  setSelectedVersionStage,
  setSelectedVersion,
  availableRegions,
  availableStages,
  productVersions,
  productVersionsLoading,
  showValidationErrors,
  disabled,
  productVersionMetadata,
  i18nSteps,
  vvJobName,
  vvPlatform,
  vvVersion,
  vvArtifactUpstreamPath,
  productType
}) => {
  const { isFeatureEnabled } = useFeatureToggles();
  const isFeatureAccessible = useRoleAccessToggle();
  const componentVersionTypeFirstOption = {
    label: i18nSteps.selectComponentVersionTypePlaceholder,
    value: i18nSteps.componentVersionTypeAnyOption,
  };
  const [componentVersionType, setComponentVersionType] = useState<SelectProps.Option>(
    componentVersionTypeFirstOption
  );
  const softwareVendorFirstOption = {
    label: i18nSteps.selectSoftwareVendorPlaceholder,
    value: i18nSteps.softwareVendorAnyOption,
  };
  const [softwareVendor, setSoftwareVendor] = useState<SelectProps.Option>(
    softwareVendorFirstOption
  );

  const localStorageSelectedStage = useLocalStorage('selectedStage');
  const localStorageSelectedRegion = useLocalStorage('selectedRegion');

  if (localStorageSelectedStage[0]) {
    setSelectedVersionStage?.(localStorageSelectedStage[0]);
    localStorage.removeItem('selectedStage');
  }

  if (localStorageSelectedRegion[0]) {
    setSelectedVersionRegion?.(localStorageSelectedRegion[0]);
    localStorage.removeItem('selectedRegion');
  }

  // Pre-select recommended version by default when no version is selected
  useEffect(() => {
    if (!selectedVersion && !productVersionsLoading) {
      const recommendedVersion = productVersions.find(version => version.isRecommendedVersion);
      if (recommendedVersion) {
        setSelectedVersion?.(recommendedVersion);
      }
    }
  }, [productVersions, productVersionsLoading, selectedVersion, setSelectedVersion]);

  const columnDefinitions: TableProps.ColumnDefinition<ComponentVersionDetails>[] = [
    {
      id: 'componentName',
      header: i18nSteps.tableHeaderComponentName,
      cell: (e) => e.componentName,
    },
    {
      id: 'softwareVersion',
      header: i18nSteps.tableHeaderSoftwareVersion,
      cell: (e) => e.softwareVersion,
    },
    {
      id: 'componentVersionType',
      header: i18nSteps.tableHeaderComponentVersionType,
      cell: (e) => e.componentVersionType,
    },
    {
      id: 'softwareVendor',
      header: i18nSteps.tableHeaderSoftwareVendor,
      cell: (e) => e.softwareVendor,
    },
    {
      id: 'notes',
      header: i18nSteps.tableHeaderNotes,
      cell: (e) => e.notes,
    },
    {
      id: 'licenseDashboard',
      header: i18nSteps.tableHeaderLicenseDashboard,
      cell: (e) => <Link external href={e.licenseDashboard}> {e.licenseDashboard} </Link>,
    }
  ];
  const { items, actions, filterProps, collectionProps, paginationProps } =
    useCollection(selectedVersion?.componentVersionDetails?.filter(componentVersion =>
      (componentVersion.componentVersionType === componentVersionType?.value ||
        componentVersionType?.value === i18nSteps.componentVersionTypeAnyOption) &&
      (componentVersion.softwareVendor === softwareVendor?.value ||
        softwareVendor?.value === i18nSteps.softwareVendorAnyOption)) || [], {
      filtering: {
        empty:
          <NoMatchTableNotification
            title={i18nSteps.tableFilterNoResultTitle}
            buttonAction={() => actions.setFiltering('')}
            buttonText={i18nSteps.tableFilterNoResultActionText}
            subtitle={i18nSteps.tableFilterNoResultSubtitle}
          />
        ,
        noMatch:
          <NoMatchTableNotification
            title={i18nSteps.tableFilterNoResultTitle}
            buttonAction={() => actions.setFiltering('')}
            buttonText={i18nSteps.tableFilterNoResultActionText}
            subtitle={i18nSteps.tableFilterNoResultSubtitle}
          />
        ,
      },
      selection: {},
      sorting: { defaultState: { sortingColumn: columnDefinitions[0] } },
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE },
    });

  const isVVAdditionalConfiguration = () => {
    return vvJobName || vvPlatform || vvVersion || vvArtifactUpstreamPath;
  };

  const getValue = (value: string | undefined) => {
    return value ? value : 'N/A';
  };

  const getPlatformInfo = () => {
    return isVVAdditionalConfiguration() && <Alert statusIconAriaLabel="Info">
      {i18nSteps.mappingInfo(
        getValue(vvJobName),
        getValue(vvPlatform),
        getValue(vvVersion),
        getValue(vvArtifactUpstreamPath)
      )}
    </Alert>;
  };

  const getComponentVersionTypeOptions = () => {
    const componentVersionTypesOptions = [
      ...new Set(selectedVersion?.componentVersionDetails)
    ].map((componentVersion) => {
      return {
        label: componentVersion.componentVersionType,
        value: componentVersion.componentVersionType,
      } as SelectProps.Option;
    });

    componentVersionTypesOptions.unshift(componentVersionTypeFirstOption);

    return componentVersionTypesOptions;
  };

  const getSoftwareVendorOptions = () => {
    const softwareVendorsOptions = [
      ...new Set(selectedVersion?.componentVersionDetails)
    ].map((componentVersion) => {
      return {
        label: componentVersion.softwareVendor,
        value: componentVersion.softwareVendor,
      } as SelectProps.Option;
    });

    softwareVendorsOptions.unshift(softwareVendorFirstOption);

    return softwareVendorsOptions;
  };

  return <SpaceBetween size={'s'}>
    {getPlatformInfo()}
    <Container
      header={
        <Header variant="h2">
          {i18nSteps.settingsContainerHeader}
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="l">
        {renderRegionSelector()}
        {renderStageSelector()}
        {renderVersionSelector()}
        {!isFeatureEnabled(Feature.ProductMetadata) && renderMetadata()}
        {isFeatureEnabled(Feature.ProductMetadata) && renderVersionDetails()}
        {isFeatureEnabled(Feature.ProductMetadata) && renderVersionOsVersion()}
        {isFeatureEnabled(Feature.ProductMetadata) && renderComponentVersionDetails()}
      </SpaceBetween>
    </Container>
  </SpaceBetween>;

  function isRegionEnabled() {
    return true;
  }

  function renderComponentVersionDetails() {
    if (!selectedVersion?.componentVersionDetails) {
      return <></>;
    }

    return <>
      <Table

        data-test="table-component-version-details"
        {...collectionProps}
        header={
          <h4>
            {i18nSteps.tableHeader} ({selectedVersion.componentVersionDetails.length})
          </h4>
        }
        columnDisplay={
          [
            { id: 'componentName', visible: true },
            { id: 'softwareVersion', visible: true },
            { id: 'componentVersionType', visible: true },
            { id: 'softwareVendor', visible: true },
            { id: 'notes', visible: true },
            { id: 'licenseDashboard', visible: true },
          ]
        }
        items={items}
        empty={
          <EmptyGridNotification
            title={i18nSteps.emptyInstalledTools}
            subTitle={i18nSteps.emptyInstalledToolsSubTitle}
          />
        }
        filter={
          <SpaceBetween size="m" direction="horizontal">
            <TextFilter
              {...filterProps}
              filteringPlaceholder={i18nSteps.findInstalledToolsPlaceholder}
              filteringAriaLabel={i18nSteps.findInstalledToolsPlaceholder}
            />
            <Select
              options={getComponentVersionTypeOptions()}
              // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
              selectedOption={componentVersionType!}
              onChange={event => {
                setComponentVersionType(event.detail.selectedOption);
              }}
              placeholder={i18nSteps.selectComponentVersionTypePlaceholder}
              data-test="select-component-version-type"
            />
            <Select
              options={getSoftwareVendorOptions()}
              // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
              selectedOption={softwareVendor!}
              onChange={event => {
                setSoftwareVendor(event.detail.selectedOption);
              }}
              placeholder={i18nSteps.selectSoftwareVendorPlaceholder}
              data-test="select-software-vendor"
            />
          </SpaceBetween>
        }
        pagination={<Pagination {...paginationProps} />}
        resizableColumns
        variant="borderless"
        columnDefinitions={columnDefinitions}
      />
    </>;
  }

  function renderVersionDetails() {
    if (!selectedVersion?.versionDescription) {
      return <></>;
    }

    return <TextContent key="version-details">
      <Box variant="div">
        <Header variant='h3'>
          {i18nSteps.headerVersionDetails}
        </Header>
        {<Box variant="div" data-test="version-details">
          {selectedVersion.versionDescription}
        </Box>}
      </Box>
    </TextContent>;
  }

  function renderVersionOsVersion() {
    if (!selectedVersion?.osVersion) {
      return <></>;
    }

    return <TextContent key="os-version">
      <Box variant="div">
        <h5>
          {i18nSteps.headerOsVersion}
        </h5>
        {<Box variant="div" data-test="os-version">
          {selectedVersion.osVersion}
        </Box>}
      </Box>
    </TextContent>;
  }

  function renderRegionSelector() {
    return renderRegionSelectorWithoutLatencies();
  }

  function renderRegionSelectorWithoutLatencies() {
    return <RegionSelect
      enabledRegions={availableRegions || []}
      i18n={i18nSteps}
      selectedVersionRegion={selectedVersionRegion}
      setSelectedVersionRegion={setSelectedVersionRegion}
      disabled={disabled || false}
      getRegionLabel={getRegionLabel}
      isRegionEnabled={isRegionEnabled}
    />;
  }
  function renderStageSelector() {
    return <>{isFeatureAccessible(RoleBasedFeature.ChooseStageInProductSelection) &&
      <FormField
        label={i18nSteps.formFieldStageHeader}
        description={i18nSteps.formFieldStageDescription}
      >
        <SpaceBetween direction="vertical" size="xxs">
          <Select
            selectedOption={getStageOption(selectedVersionStage)}
            onChange={({ detail }) => {
              setSelectedVersionStage?.(detail.selectedOption.value ?? '');
              setSelectedVersion?.();
            }}
            options={availableStages!.map(getStageOption)}
            selectedAriaLabel="Selected"
            data-test="select-stage"
            disabled={disabled}
          />
          {productType !== 'CONTAINER' &&
            <Alert type="info">
              {i18nSteps.experimentalWarning}
              <Link
                href={i18nSteps.experimentalWarningLinkUrl}
                target="_blank"
                rel="noopener noreferrer"
              >{i18nSteps.experimentalWarningLinkText}
              </Link>.
            </Alert>
          }
        </SpaceBetween>
      </FormField>
    }</>;
  }

  function renderVersionSelector() {
    const noVersionsAvailable = productVersions.length === EMPTY_ARRAY_COUNT;

    return <FormField
      label={i18nSteps.formFieldVersionHeader}
      description={i18nSteps.formFieldVersionDescription}
      errorText={showSelectedVersionErrorText()}
    >
      <Select
        selectedOption={mapVersion(selectedVersion)}
        onChange={({ detail }) => {
          setSelectedVersion?.(
            productVersions.find((v: { versionId: string | undefined }) =>
              v.versionId === detail.selectedOption.value));
        }}
        options={mapVersions(productVersions)}
        selectedAriaLabel="Selected"
        loadingText={i18nSteps.productVersionsLoading}
        statusType={productVersionsLoading ? 'loading' : 'finished'}
        data-test="select-version"
        disabled={noVersionsAvailable || disabled}
      />
    </FormField>;
  }

  function showSelectedVersionErrorText() {
    if (showValidationErrors && !selectedVersionValid) {
      return i18nSteps.formFieldVersionError;
    }
    return undefined;
  }

  function getStageOption(stage: string) {
    return {
      label: stage, value: stage
    };
  }

  function getRegionLabel(region: string) {
    return REGION_NAMES[region as EnabledRegion];
  }

  function mapVersions(versions: Step1Version[]): SelectProps.Option[] {
    return versions.sort(compareSemanticVersions()).map<SelectProps.Option>(mapVersion);
  }

  function mapVersion(version?: Step1Version): SelectProps.Option {
    if (!version) {
      return { label: i18nSteps.dropdownVersionNotSelected };
    }

    return {
      label: getVersionLabel(version.versionName, version.versionDescription),
      value: version.versionId,
      tags: [version.isRecommendedVersion ? i18nSteps.recommendedVersionTag : '']
    };
  }

  function getVersionLabel(versionName: string, versionDescription?: string) {
    if (!versionDescription) {
      return versionName;
    }
    return versionName + ' - ' + versionDescription;
  }

  function renderMetadata() {
    if (!productVersionMetadata) {
      return <></>;
    }

    return Object.
      entries(productVersionMetadata).
      map(([metadataKey, metadataValue]) =>
        <ProductVersionMetadataComponent
          key={metadataKey}
          metadataKey={metadataKey}
          metadataValue={metadataValue}
        />
      );
  }
};

export { configureSettingsStep as ConfigureSettingsStep };