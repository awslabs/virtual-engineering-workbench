import { useState } from 'react';
import {
  ContentLayout,
  Container,
  Header,
  ColumnLayout,
  Box,
  SpaceBetween,
  Button,
  Pagination,
  TextFilter,
  Table,
  TableProps,
  Link,
  HelpPanel
} from '@cloudscape-design/components';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './technologies.translations';
import { NoMatchTableNotification } from '../shared';
import { UserPrompt } from '../shared/user-prompt';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { Technology } from '../../../services/API/proserve-wb-projects-api';
import { useTechnologies } from './technologies.logic';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../state';
import { useProjectAccounts } from '../projects/project-details/project-accounts.logic';
import { useNavigate } from 'react-router-dom';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';


const technologies = () => {
  const DEFAULT_PAGE_SIZE = 50;
  const EMPTY = 0;
  const navigate = useNavigate();
  const { navigateTo, getPathFor } = useNavigationPaths();
  const [selectedItems, setSelectedItems] = useState<Technology[]>([]);
  const [deleteConfirmVisible, setDeleteConfirmVisible] = useState(false);

  const selectedProject = useRecoilValue(selectedProjectState);
  if (selectedProject.projectId === undefined) {
    return <div>No project selected</div>;
  }
  const {
    technologies,
    isLoadingTechnologies,
    loadTechnologies,
    deleteTechnology,
    technologyDeletionInProgress
  } = useTechnologies({ projectId: selectedProject.projectId, pageSize: DEFAULT_PAGE_SIZE.toString() });
  const {
    projectAccounts,
  } = useProjectAccounts({ projectId: selectedProject.projectId });
  const columnDefinition: TableProps.ColumnDefinition<Technology>[] = [
    {
      id: 'name',
      header: i18n.tableHeaderTechnologyName,
      cell: e =><Link onFollow={(event) => {
        event.preventDefault();
        navigate(`${getPathFor(RouteNames.Technologies)}/${e.id}`, {
          state: {
            technologyId: e.id,
            technologyName: e.name
          }
        });
      }}>{e.name}</Link>,
      sortingField: 'name'
    },
    {
      id: 'description',
      header: i18n.tableHeaderTechnologyDescription,
      cell: e => e.description,
      sortingField: 'description'
    },
    {
      id: 'id',
      header: i18n.tableHeaderTechnologyId,
      cell: e => e.id,
      sortingField: 'id'
    },
  ];
  const { items, actions, filteredItemsCount, collectionProps, filterProps, paginationProps } = useCollection(
    technologies,
    {
      filtering: {
        empty: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonText={i18n.tableNoItems}
          buttonAction={navigateToAddTechnologyScreen}
          subtitle={''}/>,
        noMatch: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonText={i18n.tableFilterNoMatch}
          buttonAction={() => actions.setFiltering('')}
          subtitle={i18n.tableFilterNoResultSubtitle}/>,
      },
      pagination: { pageSize: DEFAULT_PAGE_SIZE },
      sorting: { defaultState: { sortingColumn: columnDefinition[0] } },
      selection: {},
    }
  );

  return <>
    {renderDeletePrompt()}
    <WorkbenchAppLayout breadcrumbItems={[
      { path: i18n.breadcrumbLevel1, href: '#' }
    ]}
    content={
      <ContentLayout header={renderHeader()}>
        <SpaceBetween size={'m'} direction={'vertical'}>
          <Container header={<Header variant="h2">{i18n.overview}</Header>}>
            <ColumnLayout columns={4} variant="text-grid">
              <div>
                <Box variant="awsui-key-label" fontWeight="bold">{i18n.availableTechnologies}</Box>
                <h1>{technologies?.length}</h1>
              </div>
              <div>
                <Box variant="awsui-key-label" fontWeight="bold">{i18n.activeAWSAccounts}</Box>
                <h1>{projectAccounts.filter(account => account.accountStatus === 'Active').length}</h1>
              </div>
              <div>
                <Box variant="awsui-key-label" fontWeight="bold">{i18n.inactiveAWSAccounts}</Box>
                <h1>{projectAccounts.filter(account => account.accountStatus === 'Inactive').length}</h1>
              </div>
              <div>
                <Box variant="awsui-key-label" fontWeight="bold">{i18n.archivedAWSAccounts}</Box>
                <h1>{projectAccounts.filter(account => account.accountStatus === 'Archived').length}</h1>
              </div>
            </ColumnLayout>
          </Container>
          <Table
            {...collectionProps}
            columnDefinitions={columnDefinition}
            items={items}
            loading={isLoadingTechnologies}
            loadingText={i18n.tableLoading}
            trackBy="id"
            selectionType='single'
            onSelectionChange={({ detail }) => setSelectedItems(detail.selectedItems)}
            selectedItems={selectedItems}
            header={
              <Header
                actions={
                  <SpaceBetween size={'xs'} direction={'horizontal'}>
                    <Button
                      iconName='refresh'
                      loading={isLoadingTechnologies}
                      onClick={(e) => { e.preventDefault(); loadTechnologies(); }}/>
                    <Button
                      onClick={handleDeleteAction}
                      variant='normal'
                      disabled={selectedItems.length === EMPTY}
                      data-test="delete-technology-btn">
                      {i18n.tableActionDeleteTechnology}
                    </Button>
                    <Button
                      onClick={(e) => {
                        e.preventDefault();
                        const techId = selectedItems[0].id;
                        const path = getPathFor(RouteNames.UpdateTechnology).replace(':id', techId);
                        navigate(path, {
                          state: {
                            technologyId: techId,
                            technologyName: selectedItems[0].name,
                            technologyDescription: selectedItems[0].description,
                          }
                        });
                      }}
                      variant='normal'
                      disabled={selectedItems.length === EMPTY}
                      data-test="update-technology-btn">
                      {i18n.tableActionUpdateTechnology}
                    </Button>
                    <Button
                      onClick={(e) => {
                        e.preventDefault();
                        navigate(`${getPathFor(RouteNames.Technologies)}/${selectedItems[0].id}`, {
                          state: {
                            technologyId: selectedItems[0].id,
                            technologyName: selectedItems[0].name
                          }
                        });
                      }}
                      variant='primary'
                      disabled={selectedItems.length === EMPTY}
                      data-test="view-technology-btn">
                      {i18n.tableActionViewTechnology}
                    </Button>
                  </SpaceBetween>
                }
              >
                {i18n.tableHeader}
              </Header>
            }
            visibleColumns={[
              'name',
              'description',
              'id'
            ]}
            pagination={<Pagination {...paginationProps} />}
            filter={
              <TextFilter
                {...filterProps}
                filteringAriaLabel={i18n.filterPlaceholder}
                filteringPlaceholder={i18n.filterPlaceholder}
                countText={i18n.searchResult(filteredItemsCount || EMPTY)}
              />
            }
            data-test="technologies-table"
          />
        </SpaceBetween>
      </ContentLayout>
    }
    contentType="default"
    tools={renderTools()}
    />
  </>;

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel2}</Box>
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

  function handleDeleteAction() {
    setDeleteConfirmVisible(true);
  }

  function renderDeletePrompt() {
    return <>
      <UserPrompt
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteConfirmVisible(false)}
        headerText={i18n.deleteModalHeader}
        content={createDeleteModalText()}
        cancelText={i18n.deleteModalCancel}
        confirmText={i18n.deleteModalOK}
        confirmButtonLoading={technologyDeletionInProgress}
        visible={deleteConfirmVisible}
        data-test="delete-technology-prompt"
      />
    </>;
  }

  function handleDeleteConfirm() {
    deleteTechnology(selectedItems[0].id);
    setDeleteConfirmVisible(false);
  }

  function createDeleteModalText() {
    const technologyToOffboard = selectedItems.map((item) =>
      <li key={item.id}><b>{item.name} with technology ID {item.id}</b></li>
    );
    return <>{i18n.deleteModalText1}<p>{technologyToOffboard}</p>{i18n.deleteModalText2}
      <p>{i18n.deleteModalText3}</p></>;
  }

  function renderHeader() {
    return <Header
      variant='awsui-h1-sticky'
      actions={
        <Button
          onClick={navigateToAddTechnologyScreen}
          variant='primary' data-test="create-technology-btn">
          {i18n.buttonAddTechnology}</Button>
      }
    >{i18n.layoutHeader}</Header>;
  }

  function navigateToAddTechnologyScreen() {
    navigateTo(RouteNames.AddTechnology);
  }
};

export { technologies as Technologies };