import { useCollection } from '@cloudscape-design/collection-hooks';
import {
  Badge,
  Button,
  Header,
  Pagination,
  SpaceBetween,
  StatusIndicator,
  StatusIndicatorProps,
  Table,
  TableProps,
  TextFilter,
  ColumnLayout, Box, Container,
  HelpPanel,
  Popover,
  Icon
} from '@cloudscape-design/components';
import { ProjectAccount } from '../../../../services/API/proserve-wb-projects-api';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { CopyText, NoMatchTableNotification } from '../../shared';
import { EnabledRegion, REGION_NAMES } from '../../../user-preferences';
import { useProjectAccounts } from './project-accounts.logic';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../state';
import { useLocation, useNavigate } from 'react-router-dom';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './project-accounts.translations';
import { useCloudscapeTablePersisentState } from '../../../../hooks';

const DEFAULT_PAGE_SIZE = 20;
const ONE_ITEM = 1;
const EMPTY = 0;
const ERROR_MESSAGE_TRIM_START = 0;
const ERROR_MESSAGE_MAX_LEN = 300;

const ACCOUNT_STATUS_MAP: { [key: string]: StatusIndicatorProps.Type } = {
  Creating: 'in-progress',
  OnBoarding: 'in-progress',
  Active: 'success',
  OffBoarding: 'in-progress',
  Archived: 'stopped',
  Failed: 'error',
  Inactive: 'pending',
};

const ACCOUNT_ONBOARD_RESULT_MAP: { [key: string]: StatusIndicatorProps.Type } = {
  Failed: 'error',
  Succeeded: 'success',
};


function getRegionName(r?: string) {
  if (!r) {
    return 'Undefined';
  }
  return REGION_NAMES[r as EnabledRegion] || r;
}

const LastOnboardingResultCell = ({ account }: { account: ProjectAccount }) => {

  if (!account.lastOnboardingErrorMessage) {
    return renderContent();
  }

  return <>
    <Popover
      dismissButton={false}
      position="top"
      size="large"
      triggerType="custom"
      content={
        <Box>
          {account.lastOnboardingErrorMessage.substring(ERROR_MESSAGE_TRIM_START, ERROR_MESSAGE_MAX_LEN)}
        </Box>
      }
    >
      {renderContent()}
    </Popover>
  </>;

  function renderContent() {
    if (!account.lastOnboardingResult) {
      return <></>;
    }

    if (!(account.lastOnboardingResult in ACCOUNT_ONBOARD_RESULT_MAP)) {
      return <>{account.lastOnboardingResult}</>;
    }

    return <>
      <SpaceBetween direction='horizontal' size="xs">
        <StatusIndicator type={ACCOUNT_ONBOARD_RESULT_MAP[account.lastOnboardingResult]}>
          {account.lastOnboardingResult}
        </StatusIndicator>
        {!!account.lastOnboardingErrorMessage && <Icon name="status-info" />}
      </SpaceBetween>
    </>;
  }
};

const COLUMN_DEFINITIONS: TableProps.ColumnDefinition<ProjectAccount>[] = [
  {
    id: 'id',
    header: i18n.tableHeaderAccountId,
    cell: e => e.id,
    sortingField: 'id'
  },
  {
    id: 'accountId',
    header: i18n.tableHeaderAWSAccountId,
    cell: e => <CopyText
      copyText={e.awsAccountId}
      copyButtonLabel={i18n.copyButtonLabel}
      successText={i18n.copySuccess}
      errorText={i18n.copyError} />,
    sortingField: 'accountId'
  },
  {
    id: 'region',
    header: i18n.tableHeaderRegion,
    cell: e => getRegionName(e.region),
    sortingField: 'region'
  },
  {
    id: 'name',
    header: i18n.tableHeaderAccountName,
    cell: e => <CopyText
      copyText={e.accountName || ''}
      copyButtonLabel={i18n.copyButtonLabel}
      successText={i18n.copySuccess}
      errorText={i18n.copyError} />,
    sortingField: 'accountName'
  },
  {
    id: 'description',
    header: i18n.tableHeaderAccountDescription,
    cell: e => e.accountDescription,
    sortingField: 'accountDescription'
  },
  {
    id: 'type',
    header: i18n.tableHeaderAccountType,
    cell: e => <Badge>{e.accountType}</Badge>,
    sortingField: 'accountType'
  },
  {
    id: 'stage',
    header: i18n.tableHeaderAccountStage,
    cell: e => <Badge>{e.stage}</Badge>,
    sortingField: 'stage'
  },
  {
    id: 'status',
    header: i18n.tableHeaderAccountStatus,
    cell: e => <StatusIndicator type={ACCOUNT_STATUS_MAP[e.accountStatus ?? '']}>
      {e.accountStatus}
    </StatusIndicator>,
    sortingField: 'accountStatus'
  },
  {
    id: 'lastOnboardingResult',
    header: i18n.tableHeaderLastOnboardingResult,
    cell: e => <LastOnboardingResultCell account={e} />,
    sortingField: 'tableHeaderLastOnboardingResult',
  },
  {
    id: 'technologyId',
    header: i18n.tableHeaderAccountTechnology,
    cell: e => <CopyText
      copyText={e.technologyId}
      copyButtonLabel={i18n.copyButtonLabel}
      successText={i18n.copySuccess}
      errorText={i18n.copyError} />,
    sortingField: 'technologyId'
  },
];

function projectAccounts() {

  const { getPathFor, navigateTo } = useNavigationPaths();
  const navigate = useNavigate();
  const { state } = useLocation();
  const selectedProject = useRecoilValue(selectedProjectState);
  if (selectedProject.projectId === undefined) {
    return <div>No project selected</div>;
  }

  const {
    accountsLoading,
    loadProjectAccounts,
    reonboardProjectAccount,
    reonboardLoading,
    activateProjectAccount,
    deactivateProjectAccount,
    technologyAccounts,
  } = useProjectAccounts({ projectId: selectedProject.projectId });

  const { items, actions, filteredItemsCount, collectionProps, filterProps, paginationProps } = useCollection(
    technologyAccounts,
    {
      filtering: {
        empty: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonText={i18n.tableFilterNoResultActionText}
          buttonAction={navigateToOnboardAccountScreen}
          subtitle={i18n.tableFilterNoResultSubtitle} />,
        noMatch: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonText={i18n.tableFilterNoResultActionText}
          buttonAction={() => actions.setFiltering('')}
          subtitle={i18n.tableFilterNoResultSubtitle} />,
      },
      pagination: { pageSize: DEFAULT_PAGE_SIZE },
      sorting: { defaultState: { sortingColumn: COLUMN_DEFINITIONS[0] } },
      selection: {},
    }
  );
  const { onSortingChange } = useCloudscapeTablePersisentState<ProjectAccount>({
    key: 'project-account',
    columnDefinitions: COLUMN_DEFINITIONS,
    setSorting: actions.setSorting,
  });

  const renderContent = () => {
    return (
      <Table
        {...collectionProps}
        columnDefinitions={COLUMN_DEFINITIONS}
        items={items}
        loading={accountsLoading}
        loadingText={i18n.tableLoading}
        trackBy="id"
        selectedItems={collectionProps.selectedItems}
        selectionType='multi'
        data-test="program-accounts-table"
        onSortingChange={onSortingChange}
        header={
          <Header
            actions={
              <SpaceBetween size={'xs'} direction={'horizontal'}>
                <Button
                  onClick={(e) => { e.preventDefault(); activate(); }}
                  disabled={!canActivate()}
                  data-test="activate-btn"
                >
                  {i18n.tableActionActivate}
                </Button>
                <Button
                  onClick={(e) => { e.preventDefault(); deactivate(); }}
                  disabled={!canDeactivate()}
                  data-test="deactivate-btn"
                >
                  {i18n.tableActionDeactivate}
                </Button>
                <Button
                  onClick={reonboard}
                  loading={reonboardLoading}
                  disabled={!canReonboard()}
                  data-test="reonboard-btn"
                >
                  {i18n.tableActionReonboard}
                </Button>
                <Button
                  iconName='refresh'
                  loading={accountsLoading}
                  onClick={(e) => { e.preventDefault(); loadProjectAccounts(); }} />
                <Button onClick={(e) => {
                  e.preventDefault();
                  navigateToOnboardAccountScreen();
                }}
                variant='primary'
                data-test="onboard-btn"
                >
                  {i18n.tableActionOnboard}
                </Button>
              </SpaceBetween>
            }
          >
            {i18n.tableHeader}
          </Header>
        }
        columnDisplay={[
          { id: 'accountId', visible: true },
          { id: 'region', visible: true },
          { id: 'name', visible: true },
          { id: 'status', visible: true },
          { id: 'lastOnboardingResult', visible: true },
          { id: 'type', visible: true },
          { id: 'stage', visible: true },
          { id: 'technologyId', visible: true },
        ]}
        pagination={<Pagination {...paginationProps} />}
        filter={
          <TextFilter
            {...filterProps}
            filteringAriaLabel="Filter accounts"
            filteringPlaceholder={i18n.filterPlaceholder}
            countText={i18n.searchResult(filteredItemsCount || EMPTY)}
          />
        }
      />
    );
  };

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box>
            <p>{i18n.infoPanelMessage2}</p>
            <ul>
              <li><b>{i18n.infoPanelPoint1}</b><br />{i18n.infoPanelPoint1Message}</li>
              <li><b>{i18n.infoPanelPoint2}</b><br />{i18n.infoPanelPoint2Message}</li>
              <li><b>{i18n.infoPanelPoint3}</b><br />{i18n.infoPanelPoint3Message}</li>
              <li><b>{i18n.infoPanelPoint4}</b><br />{i18n.infoPanelPoint4Message}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }

  if (state && state.technologyId) {
    return (
      <WorkbenchAppLayout
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Technologies) },
          { path: i18n.breadcrumbLevel2, href: '#' }
        ]}
        content={
          <SpaceBetween size={'m'} direction={'vertical'}>
            <Container header={<Header variant="h2">{i18n.overview}</Header>}
              data-test="technology-details-container">
              <ColumnLayout columns={4} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label" fontWeight="bold">{i18n.overviewAllAccounts}</Box>
                  <h1>{technologyAccounts.length}</h1>
                </div>
                <div>
                  <Box variant="awsui-key-label" fontWeight="bold">{i18n.overviewActiveAWSAccounts}</Box>
                  <h1>{technologyAccounts.filter(account =>
                    account.accountStatus === 'Active').length}</h1>
                </div>
                <div>
                  <Box variant="awsui-key-label" fontWeight="bold">{i18n.overviewInactiveAWSAccounts}</Box>
                  <h1>{technologyAccounts.filter(account =>
                    account.accountStatus === 'Inactive').length}</h1>
                </div>
                <div>
                  <Box variant="awsui-key-label" fontWeight="bold">{i18n.overviewArchivedAWSAccounts}</Box>
                  <h1>{technologyAccounts.filter(account =>
                    account.accountStatus === 'Archived').length}</h1>
                </div>
                <div>
                  <Box variant="awsui-key-label" fontWeight="bold">{i18n.overviewWorkbenchAccounts}</Box>
                  <h1>
                    {technologyAccounts
                      .filter(account => account.accountType.toUpperCase() === 'USER')
                      .length}
                  </h1>
                </div>
                <div>
                  <Box variant="awsui-key-label" fontWeight="bold">{i18n.overviewPipelineAccounts}</Box>
                  <h1>
                    {technologyAccounts
                      .filter(account => account.accountType.toUpperCase() === 'TOOLCHAIN')
                      .length}
                  </h1>
                </div>
              </ColumnLayout>
            </Container>
            {renderContent()}
          </SpaceBetween>
        }
        contentType="default"
        tools={renderTools()}
        headerText={state.technologyName}
      />
    );

  }

  return (
    renderContent()
  );

  function canDeactivate() {
    return collectionProps.selectedItems?.length === ONE_ITEM
      && collectionProps.selectedItems[EMPTY].accountStatus === 'Active';
  }

  function deactivate() {
    if (selectedProject.projectId === undefined
      || collectionProps.selectedItems === undefined
      || collectionProps.selectedItems[EMPTY].id === undefined) {
      return;
    }
    deactivateProjectAccount(selectedProject.projectId, collectionProps.selectedItems[EMPTY].id);
  }

  function canActivate() {
    return collectionProps.selectedItems?.length === ONE_ITEM
      && collectionProps.selectedItems[EMPTY].accountStatus === 'Inactive';
  }

  function activate() {
    if (selectedProject.projectId === undefined
      || collectionProps.selectedItems === undefined
      || collectionProps.selectedItems[EMPTY].id === undefined) {
      return;
    }
    activateProjectAccount(selectedProject.projectId, collectionProps.selectedItems[EMPTY].id);
  }

  function navigateToOnboardAccountScreen() {

    if (state && state.technologyId) {
      navigate(`${getPathFor(RouteNames.OnboardProjectAccount)}`, {
        state: {
          technologyId: state.technologyId,
        }
      });
    } else {
      navigateTo(RouteNames.OnboardProjectAccount);
    }
  }

  function canReonboard() {
    return (collectionProps.selectedItems?.length || EMPTY) > EMPTY;
  }

  function reonboard() {
    if (selectedProject.projectId === undefined) {
      return;
    }

    reonboardProjectAccount(selectedProject.projectId, getSelectedAccountId());
  }

  function getSelectedAccountId() {
    return collectionProps.selectedItems?.map(a => a.id).filter((id): id is string => id !== undefined) || [];
  }
}

export { projectAccounts as ProjectAccounts };