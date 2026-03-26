import {
  TableProps,
  Header,
  SpaceBetween,
  Container,
  ColumnLayout,
  Table,
  Spinner,
  Badge,
  StatusIndicator,
  StatusIndicatorProps,
  Alert,
  Box,
  HelpPanel,
  Tabs,
} from '@cloudscape-design/components';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { CopyText, EmptyGridNotification } from '../../shared';
import { ValueWithLabel } from '../../shared/value-with-label';
import { useProvisionedProductDetails } from './logic';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import {
  PRODUCT_INSTANCE_STATE_INDICATOR_MAP,
  PRODUCT_STATE_TRANSLATIONS,
} from '../logic';
import { EnabledRegion, REGION_NAMES } from '../../../user-preferences';
import {
  ProvisionedProductParameters,
  ProvisionedProductDetailsProps,
} from './interface';
import { FeatureToggle } from '../../shared/feature-toggle';
import { Feature } from '../../../feature-toggles/feature-toggle.state';
import { ProvisionedProductInstalledToolsList } from './components';

function getOSImage(osVersion: string) {
  if (osVersion.toLocaleLowerCase().includes('ubuntu')) {
    return <img src='/ubuntu.svg' width={20} height={20} />;
  } else if (osVersion.toLocaleLowerCase().includes('windows')) {
    return <img src='/windows.svg' width={20} height={20} />;
  } else if (osVersion.toLocaleLowerCase().includes('blackberry')) {
    return <img src='/blackberry.svg' width={20} height={20} />;
  }
  return <></>;
}

export function ProvisionedProductDetails(props: ProvisionedProductDetailsProps) {
  const { headerActions, ...provProdDetailsProps } = props;
  const { getPathFor } = useNavigationPaths();
  const {
    provisionedProduct,
    isLoading,
    parameters,
    recommendation,
  } = useProvisionedProductDetails(provProdDetailsProps);
  const dataTestPrefix = props.dataTestPrefix ?? 'provisioned-product';
  const columnDefinitions: TableProps.ColumnDefinition<ProvisionedProductParameters>[] =
    [
      {
        id: 'key',
        header: props.translations.tableNameLabel,
        cell: (e) => <>{e.key}</>,
      },
      {
        id: 'value',
        header: props.translations.tableValueLabel,
        cell: (e) =>
          <>
            {' '}
            {!!e.value &&
              <CopyText
                copyText={e.value ?? ''}
                copyButtonLabel={props.translations.copyButtonText}
                successText={props.translations.copySuccess}
                errorText={props.translations.copyError}
              />
            }{' '}
          </>
        ,
      },
      {
        id: 'description',
        header: props.translations.tableDescriptionLabel,
        cell: (e) => <>{e.description ?? ''}</>,
      },
    ];

  const breadcrumbItems = [
    {
      path: props.translations.breadcrumbItemLvl1,
      href: getPathFor(props.myProvisionedProductRouteName),
    },
    { path: props.translations.breadcrumbItemLvl2, href: '#' },
  ];

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={breadcrumbItems}
        customHeader={renderHeader()}
        content={renderContent()}
        tools={renderTools()}
      />
    </>
  );

  function renderHeader() {
    return (
      <Header
        variant="awsui-h1-sticky"
        description={provisionedProduct?.productDescription}
        data-test={`${dataTestPrefix}-header`}
        actions={headerActions ?? null}
      >
        {provisionedProduct?.productName}
      </Header>
    );
  }

  function renderContent() {
    return (
      <SpaceBetween size="l">
        {renderAlert()}
        {renderOverview()}
        <Tabs
          tabs={
            [
              {
                label: props.translations.tabLabelGeneral,
                id: 'ppd-general',
                content:
                    <SpaceBetween size="l">
                      {renderTable()}
                      {renderInstalledTools()}
                    </SpaceBetween>
              },
            ]
          }
        />
      </SpaceBetween>
    );
  }

  function getStatusType(): StatusIndicatorProps.Type {
    return (
      PRODUCT_INSTANCE_STATE_INDICATOR_MAP.get(
        provisionedProduct?.status ?? ''
      ) || 'warning'
    );
  }

  function getStatus(): string {
    return (
      PRODUCT_STATE_TRANSLATIONS.get(provisionedProduct?.status ?? '') ||
      (provisionedProduct?.status ?? '')
    );
  }


  function renderOverview() {
    return (
      <>
        <Container
          data-test={`${dataTestPrefix}-overview`}
          header={<Header>{props.translations.overviewHeader}</Header>}
        >
          {isLoading ?
            <Spinner></Spinner>
            :
            <ColumnLayout columns={5} variant="text-grid" minColumnWidth={100}>
              {renderOverviewStage()}
              <ValueWithLabel label={props.translations.overviewVersionLabel}>
                {provisionedProduct?.versionName}
              </ValueWithLabel>
              <ValueWithLabel label={props.translations.overviewStatusLabel}>
                <StatusIndicator type={getStatusType()}>
                  {getStatus()}
                </StatusIndicator>
              </ValueWithLabel>
              {renderOverviewOperatingSystem()}
            </ColumnLayout>
          }
        </Container>
      </>
    );
  }

  function renderOverviewStage() {
    return (
      <ValueWithLabel label={props.translations.overviewStageAndRegion}>
        <SpaceBetween size={'xxs'} direction="horizontal">
          <Badge color="blue">
            {provisionedProduct?.stage?.toUpperCase() ?? 'n/a'}
          </Badge>
          /
          <Box>
            {REGION_NAMES[
              (provisionedProduct?.region as EnabledRegion) || 'unspecified'
            ] || provisionedProduct?.region}
          </Box>
        </SpaceBetween>
      </ValueWithLabel>
    );
  }

  function renderOverviewOperatingSystem() {
    return (
      <FeatureToggle feature={Feature.ProductMetadata}>
        <ValueWithLabel label={props.translations.overviewOS}>
          <SpaceBetween size={'xxxs'} direction="horizontal">
            {getOSImage(provisionedProduct?.osVersion || 'N/A')}{' '}
            {provisionedProduct?.osVersion || 'N/A'}
          </SpaceBetween>
        </ValueWithLabel>
      </FeatureToggle>
    );
  }

  function renderInstalledTools() {
    return <ProvisionedProductInstalledToolsList
      componentVersionDetails={provisionedProduct?.componentVersionDetails || []}
      translations={props.translations}
    />;
  }

  function renderTable() {
    return (
      <>
        <Table
          loading={isLoading}
          header={<Header variant="h2">{props.translations.generalConfigurationHeader}</Header>}
          visibleColumns={['key', 'value', 'description']}
          items={parameters ?? []}
          empty={
            <EmptyGridNotification
              title={props.translations.noParamsTitle}
              subTitle={props.translations.noParamsSubtitle}
            />
          }
          columnDefinitions={columnDefinitions}
          data-test={`${dataTestPrefix}-params-table`}
        />
      </>
    );
  }

  function renderAlert() {
    return (
      <>
        {!!provisionedProduct?.instanceRecommendationReason &&
          <Alert
            statusIconAriaLabel="Warning"
            type="warning"
            header={`${props.translations.alertWarningHeader} ${provisionedProduct?.productName}`}
          >
            {recommendation.recommendationMessage}{' '}
            <strong>{recommendation.recommendedInstanceType}</strong>
          </Alert>
        }
      </>
    );
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{props.translations.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{props.translations.infoPanelLabel1}</Box>
          <Box variant="p">{props.translations.infoPanelMessage1}</Box>
          <Box variant="p">{props.translations.infoPanelMessage2}</Box>
          <Box variant="p">{props.translations.infoPanelMessage3}</Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }

}
