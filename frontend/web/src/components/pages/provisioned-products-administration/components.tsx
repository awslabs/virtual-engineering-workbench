import {
  Box,
  Alert,
  Button,
  ColumnLayout,
  Container,
  Header,
  HelpPanel,
  Pagination,
  Popover,
  Select,
  SpaceBetween,
  StatusIndicator,
  Table,
  TableProps,
  TextFilter,
  ButtonDropdown,
  ButtonDropdownProps,
} from '@cloudscape-design/components';
import {
  PRODUCT_INSTANCE_STATE_INDICATOR_MAP,
  PRODUCT_INSTANCE_STATES,
  PRODUCT_STATE_TRANSLATIONS,
  PRODUCT_TYPE_MAP,
  ProvisionedProductsAdministrationTranslations,
  ProvisionedProductsListProps,
  ProvisionedProductsOverviewProps,
  ProvisionedProductStatusProps,
  ProvisionedProductsListActionsProps,
} from './interface';
import { InfoBox } from '../shared/info-box';
import { CopyText, EmptyGridNotification, UserDate } from '../shared';
import {
  AdditionalConfiguration,
  ProvisionedProduct,
} from '../../../services/API/proserve-wb-provisioning-api';
import { UserPrompt } from '../shared/user-prompt';
import { useCloudscapeTablePersisentState } from '../../../hooks';
import { REGION_NAMES } from '../../user-preferences';

export const ProvisionedProductsAdministrationHeader = (
  translations: ProvisionedProductsAdministrationTranslations
) => {
  return (
    <Header variant="h1" description={translations.navHeaderDescription}>
      {translations.navHeader}
    </Header>
  );
};

export const ProvisionedProductsAdministrationTools = (
  translations: ProvisionedProductsAdministrationTranslations
) => {
  return (
    <HelpPanel header={<h2>{translations.infoPanelHeader}</h2>}>
      <SpaceBetween size={'s'}>
        <Box variant="awsui-key-label">{translations.infoPanelLabel1}</Box>
        <Box variant="p">{translations.infoPanelMessage1}</Box>
        <Box variant="awsui-key-label">{translations.infoPanelLabel2}</Box>
        <Box variant="p">{translations.infoPanelMessage2}</Box>
      </SpaceBetween>
    </HelpPanel>
  );
};

export const ProvisionedProductsOverview = (
  props: ProvisionedProductsOverviewProps
) => {
  const { translations, provisionedProducts, provisionedProductsLoading } =
    props;

  return (
    <Container
      header={<Header>{translations.overviewHeader}</Header>}
      data-test="provisioned-products-admin-overview"
    >
      <ColumnLayout columns={2} variant="text-grid">
        <InfoBox
          data-test="total-provisioned-products"
          label={translations.totalCount}
          value={provisionedProducts.length}
          loading={provisionedProductsLoading}
        />
        <InfoBox
          data-test="running-provisioned-products"
          label={translations.runningCount}
          value={
            provisionedProducts.filter(
              (x) => x.status === PRODUCT_INSTANCE_STATES.Running
            ).length
          }
          loading={provisionedProductsLoading}
        />
      </ColumnLayout>
    </Container>
  );
};

function ProvisionedProductCardStatus({
  status,
}: ProvisionedProductStatusProps) {
  return (
    <StatusIndicator
      type={PRODUCT_INSTANCE_STATE_INDICATOR_MAP.get(status) || 'warning'}
    >
      {PRODUCT_STATE_TRANSLATIONS.get(status) || status}
    </StatusIndicator>
  );
}

export const ProvisionedProductsList = (
  props: ProvisionedProductsListProps
) => {
  const {
    translations,
    tableProps,
    tableLoading,
    tableActions,
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
  } = props;

  const { items, filterProps, collectionProps, paginationProps } = tableProps;

  const getJobNameValue = (
    vvAdditionalConfiguration: AdditionalConfiguration
  ) => {
    const jobName = vvAdditionalConfiguration.parameters!.find(
      (parameter) => parameter.key === 'jobName'
    );
    return jobName && jobName.value ? jobName.value : 'N/A';
  };

  const getPlatformValue = (
    vvAdditionalConfiguration: AdditionalConfiguration
  ) => {
    const platformType = vvAdditionalConfiguration.parameters!.find(
      (parameter) => parameter.key === 'platformType'
    );
    return platformType && platformType.value ? platformType.value : 'N/A';
  };

  const getVersionValue = (
    vvAdditionalConfiguration: AdditionalConfiguration
  ) => {
    const version = vvAdditionalConfiguration.parameters!.find(
      (parameter) => parameter.key === 'version'
    );
    return version && version.value ? version.value : 'N/A';
  };

  const getPlatformInfo = (product: ProvisionedProduct) => {
    const vvAdditionalConfiguration = product.additionalConfigurations?.find(
      (configuration) =>
        configuration.type === 'VVPL_PROVISIONED_PRODUCT_CONFIGURATION'
    );
    if (vvAdditionalConfiguration && vvAdditionalConfiguration.parameters) {
      return (
        <Box>
          {translations.mappingInfo(
            getJobNameValue(vvAdditionalConfiguration),
            getPlatformValue(vvAdditionalConfiguration),
            getVersionValue(vvAdditionalConfiguration)
          )}
        </Box>
      );
    }
    return <></>;
  };

  const getExperimentalBanner = (product: ProvisionedProduct) => {
    if (
      product.provisioningParameters?.some(
        (x) => x.key === 'Experimental' && x.value === 'True'
      )
    ) {
      return <Box>{translations.experimentalProductBanner}</Box>;
    }
    return <></>;
  };

  const getAdditionInfo = (product: ProvisionedProduct) => {
    return (
      <>
        {getPlatformInfo(product)}
        {getExperimentalBanner(product)}
      </>
    );
  };

  const getReadableRegionName = (region: string) => {
    return REGION_NAMES[region as keyof typeof REGION_NAMES] || region;
  };

  const columnDefinitions: TableProps.ColumnDefinition<ProvisionedProduct>[] = [
    {
      id: 'productName',
      header: translations.columnProductName,
      cell: (e) => e.productName,
      sortingField: 'productName',
    },
    {
      id: 'productType',
      header: translations.columnProductType,
      cell: (e) => PRODUCT_TYPE_MAP[e.provisionedProductType || 'UNKNOWN'],
      sortingField: 'productType',
    },
    {
      id: 'status',
      header: translations.columnStatus,
      cell: (e) => <ProvisionedProductCardStatus status={e.status} />,
      sortingField: 'status',
    },
    {
      id: 'owner',
      header: translations.columnOwner,
      cell: (e) => <> {
        !!e.userId &&
          <CopyText
            copyText={e.userId ?? ''}
            copyButtonLabel={translations.copyButtonLabel}
            successText={translations.copySuccess}
            errorText={translations.copyError} />
      }
      </>,
      sortingField: 'userId',
    },
    {
      id: 'version',
      header: translations.columnVersion,
      cell: (e) => e.versionName,
      sortingField: 'version',
    },
    {
      id: 'additionalInfo',
      header: translations.columnAdditionalInfo,
      cell: (e) => getAdditionInfo(e),
      sortingField: 'additionalInfo',
    },
    {
      id: 'awsAccountId',
      header: translations.columnAwsAccount,
      cell: (e) => <> {
        !!e.awsAccountId &&
          <CopyText
            copyText={e.awsAccountId ?? ''}
            copyButtonLabel={translations.copyButtonLabel}
            successText={translations.copySuccess}
            errorText={translations.copyError} />
      }
      </>,
      sortingField: 'awsAccountId'
    },
    {
      id: 'region',
      header: translations.columnRegion,
      cell: e => <Popover
        dismissButton={false}
        position="top"
        size="small"
        triggerType="text"
        content={
          <StatusIndicator type="info">
            {e.region}
          </StatusIndicator>
        }
      >
        {getReadableRegionName(e.region)}
      </Popover>,
      sortingField: 'region'
    },
    {
      id: 'instanceId',
      header: translations.columnInstanceId,
      cell: (e) => <> {
        !!e.instanceId &&
          <CopyText
            copyText={e.instanceId ?? ''}
            copyButtonLabel={translations.copyButtonLabel}
            successText={translations.copySuccess}
            errorText={translations.copyError} />
      }
      </>,
      sortingField: 'instanceId'
    },
    {
      id: 'createDate',
      header: translations.columnCreateDate,
      cell: (e) => <UserDate date={e.createDate} />,
      sortingField: 'createDate',
    },
    {
      id: 'lastUpdateDate',
      header: translations.columnLastUpdateDate,
      cell: (e) => <UserDate date={e.lastUpdateDate} />,
      sortingField: 'lastUpdateDate',
    },
  ];

  const { onSortingChange } = useCloudscapeTablePersisentState<ProvisionedProduct>({
    key: 'admin-pp',
    columnDefinitions,
    setSorting: tableProps.actions.setSorting,
  });

  return (
    <Table
      data-test="table-provisioned-products"
      {...collectionProps}
      onSortingChange={onSortingChange}
      header={
        <Header
          variant="h2"
          counter={`(${collectionProps.totalItemsCount})`}
          actions={tableActions}
        >
          {translations.tableProvisioningProductsHeader}
        </Header>
      }
      loading={tableLoading}
      items={items}
      selectionType="multi"
      filter={
        <SpaceBetween size="m" direction="horizontal">
          <div className="filter">
            <TextFilter
              {...filterProps}
              filteringPlaceholder={
                translations.findProvisionedProductsPlaceholder
              }
              filteringAriaLabel={
                translations.findProvisionedProductsPlaceholder
              }
            />
          </div>
          <Select
            options={productOptions}
            selectedAriaLabel="Selected"
            selectedOption={selectedProductOption}
            onChange={(event) =>
              setSelectedProductOption(event.detail.selectedOption)
            }
            expandToViewport={true}
            data-test="product-name-filter"
            filteringType='auto'
          />
          <Select
            options={productTypeOptions}
            selectedAriaLabel="Selected"
            selectedOption={selectedProductTypeOption}
            onChange={(event) =>
              setSelectedProductTypeOption(event.detail.selectedOption)
            }
            expandToViewport={true}
            data-test="product-type-filter"
          />
          <Select
            options={statusOptions}
            selectedAriaLabel="Selected"
            selectedOption={selectedStatusOption}
            onChange={(event) =>
              setSelectedStatusOption(event.detail.selectedOption)
            }
            expandToViewport={true}
            data-test="status-filter"
          />
          <Select
            options={additionalInformationOptions}
            selectedAriaLabel="Selected"
            selectedOption={selectedAdditionalInformationOption}
            onChange={(event) =>
              setSelectedAdditionalInformationOption(event.detail.selectedOption)
            }
            expandToViewport={true}
            data-test="additional-information-filter"
          />
        </SpaceBetween>
      }
      empty={
        <EmptyGridNotification
          title={translations.emptyProvisionedProductsTable}
          subTitle={translations.emptyProvisionedProductsTableDescription}
        />
      }
      pagination={<Pagination {...paginationProps} />}
      columnDefinitions={columnDefinitions}
    />
  );
};

// eslint-disable-next-line complexity
export const ProvisionedProductsListActions = (
  props: ProvisionedProductsListActionsProps
) => {
  const {
    translations,
    provisionedProductsLoading,
    selectedProvisionedProductsTableProps,
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
  } = props;
  let provisionedProductType = 'selected product';

  const { items, collectionProps, paginationProps } =
    selectedProvisionedProductsTableProps;

  const renderSelectedProvisionedProducts = () => {
    return (
      <Table
        header={
          <Header variant="h3" counter={`(${items.length})`}>
            {translations.promptTableHeader}
          </Header>
        }
        {...collectionProps}
        items={items}
        pagination={<Pagination {...paginationProps} />}
        loading={provisionedProductsLoading}
        contentDensity="compact"
        resizableColumns
        columnDefinitions={[
          {
            id: 'productName',
            header: translations.columnProductName,
            cell: (e) => e.productName,
          },
          {
            id: 'productType',
            header: translations.columnProductType,
            cell: (e) =>
              PRODUCT_TYPE_MAP[e.provisionedProductType || 'UNKNOWN'],
          },
          {
            id: 'owner',
            header: translations.columnOwner,
            cell: (e) => e.userId,
          },
          {
            id: 'lastUpdateDate',
            header: translations.columnLastUpdateDate,
            cell: (e) => <UserDate date={e.lastUpdateDate} />,
            sortingField: 'lastUpdateDate',
          },
        ]}
      />
    );
  };

  function renderTerminatePromptDisclaimer() {
    const minLength = 1;
    if (items.length === minLength) {
      provisionedProductType =
        PRODUCT_TYPE_MAP[items[0].provisionedProductType || 'selected product'].toUpperCase();
    } else {
      provisionedProductType = 'SELECTED PRODUCTS';
    }
    return <Alert type="warning">
      {translations.terminatePromptDisclaimer(provisionedProductType)}
    </Alert>;
  }

  function renderStopPromptDisclaimer() {
    const minLength = 1;
    if (items.length === minLength) {
      provisionedProductType =
        PRODUCT_TYPE_MAP[items[0].provisionedProductType || 'selected product'].toUpperCase();
    } else {
      provisionedProductType = 'SELECTED PRODUCTS';
    }
    return <Alert type="warning">
      {translations.stopPromptDisclaimer(provisionedProductType)}
    </Alert>;
  }

  function handleDropdownClick(
    { detail }: CustomEvent<ButtonDropdownProps.ItemClickDetails>
  ) {
    if (detail.id === 'setTerminateProvisionedProductsPromptOpen') {
      setTerminateProvisionedProductsPromptOpen(true);
    }
    if (detail.id === 'setStopProvisionedProductsPromptOpen') {
      setStopProvisionedProductsPromptOpen(true);
    }
  }

  function itemsArrayForActionsDropdown(): ButtonDropdownProps.Item[] {
    const actionItems = [
      {
        id: 'setTerminateProvisionedProductsPromptOpen',
        action: 'start', text: translations.buttonTerminate,
        disabled: terminateActionDisabled || terminateProvisionedProductsInProgress,
      },
      {
        id: 'setStopProvisionedProductsPromptOpen',
        action: 'stop', text: translations.buttonStop,
        disabled: stopActionDisabled || stopProvisionedProductsInProgress,
      },
    ];
    return actionItems;
  }

  return (
    <>
      <SpaceBetween direction="horizontal" size="s">
        <Button
          data-test="button-refresh-table"
          iconName="refresh"
          onClick={reloadProvisionedProducts}
          loading={provisionedProductsLoading}
        />
        <ButtonDropdown
          data-test="actions-dropdown"
          onItemClick={handleDropdownClick}
          loading={
            provisionedProductsLoading ||
            terminateProvisionedProductsInProgress && stopProvisionedProductsInProgress
          }
          items={itemsArrayForActionsDropdown()}
        >
          {translations.actionsButton}
        </ButtonDropdown>
      </SpaceBetween>
      {stopProvisionedProductsPromptOpen &&
        <UserPrompt
          onConfirm={stopProvisionedProducts}
          onCancel={() => setStopProvisionedProductsPromptOpen(false)}
          headerText={translations.stopPromptHeader}
          content={
            <SpaceBetween direction="vertical" size="l">
              {renderStopPromptDisclaimer()}
              <Box>{translations.stopPromptMessage1}</Box>
              <Box>{translations.stopPromptMessage2}</Box>
              <Box>{translations.stopPromptMessage3}</Box>
              {renderSelectedProvisionedProducts()}
            </SpaceBetween>
          }
          cancelText={translations.buttonCancel}
          confirmText={translations.buttonConfirm}
          confirmButtonLoading={stopProvisionedProductsInProgress}
          visible={stopProvisionedProductsPromptOpen}
          data-test="stop-provisioned-products-prompt"
          size="large"
        />
      }
      {terminateProvisionedProductsPromptOpen &&
        <UserPrompt
          onConfirm={terminateProvisionedProducts}
          onCancel={() => setTerminateProvisionedProductsPromptOpen(false)}
          headerText={translations.terminatePromptHeader}
          content={
            <SpaceBetween direction="vertical" size="l">
              {renderTerminatePromptDisclaimer()}
              <Box>{translations.terminatePromptMessage1}</Box>
              <Box>{translations.terminatePromptMessage2}</Box>
              <Box>{translations.terminatePromptMessage3}</Box>
              {renderSelectedProvisionedProducts()}
            </SpaceBetween>
          }
          cancelText={translations.buttonCancel}
          confirmText={translations.buttonConfirm}
          confirmButtonLoading={terminateProvisionedProductsInProgress}
          visible={terminateProvisionedProductsPromptOpen}
          data-test="terminate-provisioned-products-prompt"
          size="large"
        />
      }
    </>
  );
};
