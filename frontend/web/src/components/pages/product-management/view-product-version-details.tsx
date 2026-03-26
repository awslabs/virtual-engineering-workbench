import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { CopyText, EmptyGridNotification, UserDate, YamlCodeEditor } from '../shared';
import { ValueWithLabel } from '../shared/value-with-label';
import { i18n } from './view-product-version-details.translations';
import {
  Badge,
  Box,
  Button,
  ColumnLayout,
  Container,
  FormField,
  Header,
  HelpPanel,
  Popover,
  SpaceBetween,
  Spinner,
  StatusIndicator,
  Table,
  TableProps,
  Tabs
} from '@cloudscape-design/components';
import { useEffect, useState } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { useRecoilValue } from 'recoil';
import { PromoteVersionPrompt, RetireVersionPrompt, RestoreVersionPrompt } from './user-prompts';
import { useProductVersionDetails } from './view-product-version-details.logic';
import { VersionDistribution, VersionSummary } from '../../../services/API/proserve-wb-publishing-api';
import { PRODUCT_STATUS_COLOR_MAP, PRODUCT_STATUS_MAP } from './products.translations';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { VersionStage, VersionStatus, VersionSummaryStatus, VersionType } from '../../../model';
import { useRoleAccessToggle } from '../../../hooks/role-access-toggle';
import { RoleBasedFeature, selectedProjectState } from '../../../state';
import { parseISO, compareAsc } from 'date-fns';
import { RecommendedVersionIndicator } from './view-product/recommended-version-indicator';
import { RestoredVersionIndicator } from './view-product/restored-version-indicator';
import { REGION_NAMES } from '../../user-preferences';

const UPDATE_VERSION_ALLOWED_STATUSES = new Set<VersionSummaryStatus>(['CREATED', 'FAILED']);
const UPDATE_VERSION_DENY_STAGES = new Set<VersionStage>(['PROD']);
const UPDATE_VERSION_DENY_TYPES = new Set<VersionType>(['RESTORED']);
const PROMOTE_VERSION_ALLOWED_STATUSES = new Set<VersionSummaryStatus>(['CREATED']);
const PROMOTE_VERSION_DENY_STAGES = new Set<VersionStage>(['PROD']);
const PROMOTE_VERSION_TO_PROD_DENY_TYPES = new Set<VersionType>(['RESTORED']);
const RETRY_DISTRIBUTION_ALLOWED_STATUSES = new Set<VersionStatus>(['FAILED']);
type VersionDistributionReadable = VersionDistribution & { readeableRegion: string };

const getBadgeColor = (stage: string, stages: string[]) =>
  stages.includes(stage) ? 'blue' : 'grey';

const mapProductDistributions = (distributions: any[], regionNames: { [x: string]: any }) =>
  distributions.map(versionDist => ({
    ...versionDist,
    readeableRegion: regionNames[versionDist.region] || versionDist.region,
  }));


export const ProductVersionDetails = () => {
  const { getPathFor, goBack, navigateTo } = useNavigationPaths();
  const { productId, versionId } = useParams();
  const productPath = getPathFor(RouteNames.Product, { ':id': productId });
  const [promoteConfirmVisible, setPromoteConfirmVisible] = useState(false);
  const [retireConfirmVisible, setRetireConfirmVisible] = useState(false);
  const [restoreConfirmVisible, setRestoreConfirmVisible] = useState(false);
  const [
    prodVersionDistributionsMapped,
    setProdVersionDistributionsMapped
  ] = useState<Array<VersionDistributionReadable>>([]);
  const isFeatureAccessible = useRoleAccessToggle();
  const selectedProject = useRecoilValue(selectedProjectState);
  const { state } = useLocation();
  const DEFAULT_EMPTY_DATE = '2023-01-01';
  const {
    loadProductVersion,
    retryDistribution,
    isLoading,
    isRetrying,
    productVersionDistributions,
    productVersion,
    productVersionTemplate,
  } = useProductVersionDetails();

  useEffect(() => {
    const mappedDistributions = mapProductDistributions(productVersionDistributions, REGION_NAMES);
    setProdVersionDistributionsMapped(mappedDistributions);
  }, [productVersionDistributions]);

  const getDynamicColumns = (
    isLoading: boolean):
  TableProps.ColumnDefinition<VersionDistributionReadable>[] => {
    if (isLoading) { return []; }

    return [
      {
        id: 'originalAmiId',
        header: i18n.originalAmiId,
        cell: (e: VersionDistributionReadable) => <>
          {!!e.originalAmiId &&
            <CopyText
              copyText={e.originalAmiId ?? ''}
              copyButtonLabel={i18n.originalAmiId}
              successText={i18n.copySuccess}
              errorText={i18n.copyError}
            />
          }
        </>,
        sortingField: 'originalAmiId',
      },
      {
        id: 'copiedAmiId',
        header: i18n.copiedAmiId,
        cell: (e: VersionDistributionReadable) => <>
          {!!e.copiedAmiId &&
            <CopyText
              copyText={e.copiedAmiId ?? ''}
              copyButtonLabel={i18n.copiedAmiId}
              successText={i18n.copySuccess}
              errorText={i18n.copyError}
            />
          }
        </>,
        sortingField: 'copiedAmiId',
      },
    ];
  };

  const columnDefinitions: TableProps.ColumnDefinition<VersionDistributionReadable>[] = [
    {
      id: 'awsId',
      header: i18n.awsId,
      cell: e => <> {
        !!e.awsAccountId &&
        <CopyText
          copyText={e.awsAccountId ?? ''}
          copyButtonLabel={i18n.awsId}
          successText={i18n.copySuccess}
          errorText={i18n.copyError} />
      } </>,
      sortingField: 'awsId',
      sortingComparator: compareAwsAccountIds
    },
    ...getDynamicColumns(isLoading),
    {
      id: 'region',
      header: i18n.region,
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
        {e.readeableRegion}
      </Popover>,
      sortingField: 'region'
    },
    {
      id: 'stage',
      header: i18n.stage,
      cell: e => <> {
        !!e.stage &&
        <Badge color="blue">{e.stage}</Badge>
      } </>,
      sortingField: 'stage'
    },
    {
      id: 'status',
      header: i18n.status,
      cell: e => <StatusIndicator
        type={PRODUCT_STATUS_COLOR_MAP[e.status || 'UNKNOWN'] || 'pending'}
      >
        {PRODUCT_STATUS_MAP[e.status || 'UNKNOWN']}
      </StatusIndicator>,
      sortingField: 'status'
    },
    {
      id: 'lastUpdate',
      header: i18n.lastUpdate,
      cell: e => <UserDate date={e.lastUpdateDate} />,
      sortingField: 'lastUpdate',
      sortingComparator: compareLastUpdateDates
    },
  ];

  const { items, collectionProps } = useCollection(
    prodVersionDistributionsMapped,
    {
      filtering: {
        empty: <EmptyGridNotification title={i18n.noDistributions}
          subTitle={i18n.noDistributionsSubtitle}
        />,
      },
      sorting: { defaultState: { sortingColumn: columnDefinitions[0] } },
      selection: {},
    }
  );

  return (
    <>
      <PromoteVersionPrompt
        projectId={selectedProject.projectId}
        productId={productId}
        selectedVersion={productVersion}
        promoteConfirmVisible={promoteConfirmVisible}
        setPromoteConfirmVisible={setPromoteConfirmVisible}
        loadProductDetails={loadProductVersion}
      />
      <RetireVersionPrompt
        projectId={selectedProject.projectId!}
        productId={productId!}
        selectedVersion={productVersion!}
        retireConfirmVisible={retireConfirmVisible}
        setRetireConfirmVisible={setRetireConfirmVisible}
        loadProducts={loadProductVersion}
      />
      <RestoreVersionPrompt
        projectId={selectedProject.projectId!}
        productId={productId!}
        selectedVersion={productVersion!}
        restoreConfirmVisible={restoreConfirmVisible}
        setRestoreConfirmVisible={setRestoreConfirmVisible}
        loadProducts={loadProductVersion}
      />
      <WorkbenchAppLayout
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Products) },
          { path: i18n.breadcrumbLevel2, href: productPath },
          { path: i18n.breadcrumbLevel3, href: '#' },
        ]}
        customHeader={renderHeader()}
        content={renderContent()}
        tools={renderTools()}
      />
    </>
  );


  function renderHeader() {
    return <Header
      variant='awsui-h1-sticky'
      description={productVersion?.description}
      actions={
        <SpaceBetween size={'s'} direction="horizontal">
          <Button iconName='refresh' onClick={loadProductVersion} />
          <Button
            onClick={goBack}
            variant='normal'>{i18n.buttonReturn}
          </Button>
          {!isProductArchived() &&
          <>
            {!isRetired() &&
            <>
              <Button
                data-test="retire-button"
                onClick={handleRetireAction}
                disabled={!canRetireProductVersion()}
                variant='normal'>{i18n.buttonRetire}
              </Button>
              <Button
                data-test="update-button"
                onClick={navigateToUpdateProductVersion}
                disabled={!canUpdateProductVersion()}
                variant='normal'>{i18n.buttonUpdate}
              </Button>
              <Button
                data-test="promote-button"
                onClick={handlePromoteAction}
                disabled={!canPromoteProductVersion()}
                variant='primary'>{i18n.buttonPromote}
              </Button>
            </>
            }
            {isRetired() &&
            <Button
              data-test="restore-button"
              onClick={handleRestoreAction}
              disabled={!canRestoreProductVersion()}
              variant='primary'>{i18n.buttonRestore}
            </Button>
            }
          </>
          }
        </SpaceBetween>
      }
    >
      {productVersion?.name}
    </Header>;
  }

  function handlePromoteAction() {
    setPromoteConfirmVisible(true);
  }

  function handleRetireAction() {
    setRetireConfirmVisible(true);
  }

  function handleRestoreAction() {
    setRestoreConfirmVisible(true);
  }

  function renderTemplate() {
    return <Container header={<Header>{i18n.templateDefinition}</Header>} data-test="template-definition">
      <FormField stretch>
        <YamlCodeEditor
          yamlDefinition={productVersionTemplate}
          setYamlDefinition={e=> e}
          setYamlDefinitionValid={e=>e}
          disabled={true}
          cfCompatible
        />
      </FormField>
    </Container>;
  }

  function renderTabs() {
    return <Tabs
      tabs={[
        {
          label: i18n.tableHeader,
          id: 'versionDistributions',
          content: renderTable()
        },
        {
          label: i18n.templateDefinition,
          id: 'templateDefinition',
          content: renderTemplate()
        }
      ]}
    />;
  }

  function renderContent() {
    return <>
      <SpaceBetween size='l'>
        {renderOverview()}
        {renderTabs()}
      </SpaceBetween>
    </>;
  }

  function isVersionRestored(version: VersionSummary) {
    if (version && version.restoredFromVersionName !== undefined) {
      return true;
    }
    return false;
  }

  function renderOverview() {
    const THREE_COLUMNS = 3;
    const TWO_COLUMNS = 2;
    const stages = productVersion?.stages ?? [];

    const countColumns = () => {
      return productVersion?.recommendedVersion || isVersionRestored(productVersion!) ?
        THREE_COLUMNS : TWO_COLUMNS;
    };

    return <>
      <Container data-test="version-overview-container" header={
        <Header>
          {i18n.containerHeader}
        </Header>
      }>
        <ColumnLayout columns={countColumns()} variant="text-grid">
          <ValueWithLabel label={i18n.stage}>
            <SpaceBetween size='xs' direction='horizontal'>
              <Badge color={getBadgeColor('DEV', stages)}>{i18n.envDev}</Badge>
              <Badge color={getBadgeColor('QA', stages)}>{i18n.envQa}</Badge>
              <Badge color={getBadgeColor('PROD', stages)}>{i18n.envProd}</Badge>
            </SpaceBetween>
          </ValueWithLabel>
          <ValueWithLabel label={i18n.lastUpdate}>
            <UserDate date={productVersion?.lastUpdate} />
          </ValueWithLabel>
          {(productVersion?.restoredFromVersionName ||
              productVersion?.recommendedVersion) &&
              <ValueWithLabel label={i18n.additionalInfo}>
                <RecommendedVersionIndicator
                  isRecommendedVersion={
                    productVersion ? productVersion.recommendedVersion : false
                  }
                ></RecommendedVersionIndicator>
                <RestoredVersionIndicator
                  productVersion={productVersion!}
                ></RestoredVersionIndicator>
              </ValueWithLabel>
          }
        </ColumnLayout>
      </Container>
    </>;
  }
  // eslint-disable-next-line complexity
  function renderTable() {
    const NO_ITEM = 0;
    return <>
      {isLoading ?
        <Spinner size="large" />
        :
        <Table
          {...collectionProps}
          header={
            <Header
              variant='h2'
              counter={`(${productVersionDistributions?.length ?? NO_ITEM})`}
              actions={
                <SpaceBetween direction='horizontal' size='m'>
                  {!isProductArchived() &&
                      <>
                        <Button iconName='refresh' onClick={loadProductVersion} />
                        <Button
                          onClick={retrySelectedDistributions}
                          loading={isRetrying}
                          disabled={!canRetry()}
                          data-test="retry-btn">
                          {i18n.retryButton}
                        </Button></>}
                </SpaceBetween>
              }
            >
              {i18n.tableHeader}
            </Header>}
          visibleColumns={[
            'awsId',
            ...!isLoading ? ['originalAmiId', 'copiedAmiId'] : [],
            'region',
            'stage',
            'status',
            'lastUpdate'
          ]}
          loading={isLoading}
          items={items}
          selectionType='multi'
          isItemDisabled={item => !RETRY_DISTRIBUTION_ALLOWED_STATUSES.has(item.status as VersionStatus)}
          empty={
            <EmptyGridNotification title={i18n.noDistributions}
              subTitle={i18n.noDistributionsSubtitle}
            />
          }
          columnDefinitions={columnDefinitions}
          data-test="version-distributions-table" />
      }
    </>;
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
          <Box>
            <p>{i18n.infoPanelMessage3}</p>
            <ul>
              <li><b>{i18n.infoPanelPoint1}</b><br />{i18n.infoPanelPoint1Message}</li>
              <li><b>{i18n.infoPanelPoint2}</b><br />{i18n.infoPanelPoint2Message}</li>
              <li><b>{i18n.infoPanelPoint3}</b><br />{i18n.infoPanelPoint3Message}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }

  function canRetry() {
    const EMPTY_COUNT = 0;
    return (collectionProps.selectedItems || []).length > EMPTY_COUNT;
  }

  function retrySelectedDistributions() {
    if (!collectionProps.selectedItems) {
      return;
    }
    retryDistribution((collectionProps.selectedItems || []).map(x => x.awsAccountId)).
      then(() => loadProductVersion());
  }

  function navigateToUpdateProductVersion() {
    navigateTo(RouteNames.UpdateProductVersion, {
      ':productId': productId,
      ':versionId': versionId,
    }, {
      productVersionDescription: productVersion?.description,
      isRecommended: productVersion?.recommendedVersion,
    });
  }

  function canUpdateProductVersion() {
    return !!productVersion &&
      !productVersion.stages.some(x => UPDATE_VERSION_DENY_STAGES.has(x as VersionStage)) &&
      UPDATE_VERSION_ALLOWED_STATUSES.has(productVersion.status as VersionSummaryStatus) &&
      !UPDATE_VERSION_DENY_TYPES.has(productVersion.versionType as VersionType);
  }

  // eslint-disable-next-line complexity
  function canPromoteProductVersion() {
    return !!productVersion &&
      !productVersion.stages.some(x => PROMOTE_VERSION_DENY_STAGES.has(x as VersionStage)) &&
      PROMOTE_VERSION_ALLOWED_STATUSES.has(productVersion.status as VersionSummaryStatus) &&
      (productVersion?.stages.includes('QA') ?
        isFeatureAccessible(RoleBasedFeature.ManageProdProducts) &&
        !PROMOTE_VERSION_TO_PROD_DENY_TYPES.has(productVersion.versionType as VersionType) : true);
  }

  function canRetireProductVersion() {
    return productVersion?.status === 'CREATED';
  }

  function canRestoreProductVersion() {
    return productVersion?.status === 'RETIRED' &&
    productVersion.versionType !== 'RESTORED' &&
    productVersion.stages.includes('PROD');
  }

  function isRetired() {
    return productVersion?.status === 'RETIRED';
  }

  function isProductArchived() {
    return state.productStatus === 'ARCHIVED';
  }

  function compareISODates(a: string | undefined, b: string | undefined) {
    return compareAsc(
      parseISO(a || DEFAULT_EMPTY_DATE),
      parseISO(b || DEFAULT_EMPTY_DATE)
    );
  }

  function compareLastUpdateDates(
    a: VersionDistribution,
    b: VersionDistribution) {
    return compareISODates(a.lastUpdateDate, b.lastUpdateDate);
  }

  function compareAwsAccountIds(
    a: VersionDistribution,
    b: VersionDistribution) {
    return parseInt(a.awsAccountId, 10) - parseInt(b.awsAccountId, 10);
  }
};
