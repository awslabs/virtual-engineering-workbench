/* eslint-disable */
import {
  Box,
  Button,
  ButtonDropdown,
  ButtonDropdownProps,
  Header,
  HelpPanel,
  Link,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
  TextFilter,
} from '@cloudscape-design/components';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { FC, useEffect } from 'react';
import { BreadcrumbItem } from '../../../layout';
import { WorkbenchAppLayout } from '../../../layout/workbench-app-layout/workbench-app-layout';
import { UserDate, EmptyGridNotification, NoMatchTableNotification, CollapsibleText, CopyText } from '../../shared';
import { usePipelines } from './pipelines.logic';
import { i18n, } from './pipelines.translations';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { Pipeline } from '../../../../services/API/proserve-wb-packaging-api';
import { PipelineStatus } from './pipeline-status';
import cronstrue from 'cronstrue';
import { PIPELINE_STATES_FOR_ANY_ACTION, PIPELINE_STATES_FOR_CREATE_IMAGE, PIPELINE_STATES_FOR_RETIRE, PIPELINE_STATES_FOR_UPDATE, PipelineState } from './pipeline-status.static';
import { UserPrompt } from '../../shared/user-prompt';
import { packagingAPI } from '../../../../services';
import { useCloudscapeTablePersisentState } from '../../../../hooks';

const PAGE_SIZE = 20;
const PAGE_INDEX = 1;
const ZERO_INDEX = 0;

interface PipelinesProps {
}

const Pipelines: FC<PipelinesProps> = () => {

  const {
    pipelines,
    loadPipelines,
    isLoading,
    updatePipeline,
    setSelectedPipeline,
    isRetirePipelineModalOpen,
    setIsRetirePipelineModalOpen,
    isRetireInProgress,
    retirePipeline,
    isCreateImageModalOpen,
    setIsCreateImageModalOpen,
    isCreateImageInProgress,
    createImage,
  } = usePipelines({serviceApi: packagingAPI});

  const { navigateTo, getPathFor } = useNavigationPaths();

  const columnDefinitions: TableProps.ColumnDefinition<Pipeline>[] = [
    {
      id: 'pipelineName',
      header: i18n.tableHeaderPipelineName,
      cell: e => e.pipelineName,
      sortingField: 'pipelineName'
    },
    {
      id: 'pipelineId',
      header: i18n.tableHeaderPipelineId,
      cell: (e) => e.pipelineId && <CopyText
        copyText={e.pipelineId}
        copyButtonLabel={i18n.copyPipelineId}
        successText={i18n.copyPipelineIdSuccess}
        errorText={i18n.copyPipelineIdError} />,
    },
    {
      id: 'pipelineDescription',
      header: i18n.tableHeaderPipelineDescription,
      cell: e => e.pipelineDescription,
      maxWidth: '200px',
    },
    {
      id: 'pipelineSchedule',
      header: i18n.tableHeaderPipelineSchedule,
      cell: e => cronstrue.toString(e.pipelineSchedule, {verbose: true, }),
    },
    {
      id: 'buildInstanceTypes',
      header: i18n.tableHeaderbuildInstanceTypes,
      cell: e => <CollapsibleText items={e.buildInstanceTypes}/>,
    },
    {
      id: "recipe",
      header: i18n.tableHeaderRecipe,
      cell: (e) => (
        <Link
          href={getPathFor(RouteNames.ViewRecipe, { ":recipeId": e.recipeId })}
          external
        >
          {e.recipeName}
        </Link>
      ),
      sortingField: 'recipeName'
    },
    {
      id: "recipeVersion",
      header: i18n.tableHeaderRecipeVersion,
      cell: (e) => (
        <Link
          href={getPathFor(RouteNames.ViewRecipeVersion, {
            ":recipeId": e.recipeId,
            ":versionId": e.recipeVersionId,
          })}
          external
        >
          {e.recipeVersionName}
        </Link>
      ),
      sortingField: 'recipeVersionName'
    },
    {
      id: 'status',
      header: i18n.tableHeaderStatus,
      cell: e => <PipelineStatus status={e.status} />,
      width: '120px',
      sortingField: 'status'
    },
    {
      id: 'lastUpdateDate',
      header: i18n.tableHeaderPipelineLastUpdate,
      cell: e => <UserDate date={e.lastUpdateDate} />,
      sortingField: 'lastUpdateDate'
    },
  ];

  const { items, actions, filterProps, collectionProps, paginationProps } = useCollection(
    pipelines,
    {
      filtering: {
        empty: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => actions.setFiltering('')}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle}
        />,
        noMatch: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => actions.setFiltering('')}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle} />,
      },
      selection: {},
      sorting: { defaultState: { sortingColumn: columnDefinitions.find(x => x.id==='lastUpdateDate') || {}, isDescending: true } },
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE }
    }
  );

  const { onSortingChange } = useCloudscapeTablePersisentState<Pipeline>({
    key: 'prod-man-pipelines',
    columnDefinitions,
    setSorting: actions.setSorting,
  });

  useEffect(() => {
    setSelectedPipeline?.(collectionProps.selectedItems && collectionProps.selectedItems[0]);
  }, [collectionProps, setSelectedPipeline]);

  return (
    <WorkbenchAppLayout
      breadcrumbItems={getBreadcrumbItems()}
      content={renderContent()}
      contentType="default"
      tools={renderTools()}
      customHeader={renderHeader()}
    />
  );

  function getBreadcrumbItems(): BreadcrumbItem[] {
    return [
      { path: i18n.breadcrumbLevel1, href: '#' },
    ];
  }

  function renderHeader() {
    return <>
      <Header
        variant='h1'
        description={i18n.navHeaderDescription}
        actions={
          <Button onClick={() => {
            navigateTo(RouteNames.CreatePipeline);
          }}
            variant='primary'
            data-test='create-pipeline-btn'
          >
            {i18n.createButtonText}
          </Button>
        }
      >
        {i18n.navHeader}
      </Header>
    </>;
  }

  function getSelectedItem(): Pipeline | undefined {
    if (collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined) {
      return collectionProps.selectedItems[0]
    }
    return undefined;
  }

  function isItemSelected(predicate?: (vs: Pipeline) => boolean) {
    return collectionProps.selectedItems !== undefined &&
      collectionProps.selectedItems?.length >= ZERO_INDEX &&
      collectionProps.selectedItems[0] !== undefined &&
      (!predicate || predicate(collectionProps.selectedItems[0]));
  }

  function preventAction(acceptedStatuses: Set<PipelineState>){
    return !isItemSelected() ||
      isItemSelected(pipe => !acceptedStatuses.has(pipe.status as PipelineState));
  }

  function handleDropdownClick({ detail }: CustomEvent<ButtonDropdownProps.ItemClickDetails>) {
    if (detail.id === 'update') {
      updatePipeline();
    } else if (detail.id === 'retire') {
      setIsRetirePipelineModalOpen(true);
    }
  }

  function renderContent() {
    return (
      <>
        <Table
          data-test="table-pipelines"
          {...collectionProps}
          onSortingChange={onSortingChange}
          header={
            <Header
              variant="h2"
              counter={`(${pipelines.length})`}
              description={i18n.tableHeaderDescription}
              actions={
                <SpaceBetween direction="horizontal" size="m">
                  <Button
                    data-test="button-refresh-table"
                    iconName="refresh"
                    onClick={loadPipelines}
                    loading={isLoading}
                  />
                  <ButtonDropdown
                    data-test="actions-dropdown"
                    onItemClick={handleDropdownClick}
                    disabled={preventAction(PIPELINE_STATES_FOR_ANY_ACTION)}
                    items={[
                      {
                        text: i18n.pipelineUpdate,
                        id: "update",
                        disabled: preventAction(PIPELINE_STATES_FOR_UPDATE),
                      },
                      {
                        text: i18n.pipelineRetire, id: 'retire',
                        disabled: preventAction(PIPELINE_STATES_FOR_RETIRE)
                      },
                    ]}
                  >
                    {i18n.pipelineActions}
                  </ButtonDropdown>
                  <Button 
                    variant='primary' 
                    onClick={() => setIsCreateImageModalOpen(true)}
                    disabled={preventAction(PIPELINE_STATES_FOR_CREATE_IMAGE)}
                    data-test='create-image-btn'
                  >
                    {i18n.createImageHeader}
                  </Button>
                </SpaceBetween>
              }
            >
              {i18n.tableHeader}
            </Header>
          }
          loading={isLoading}
          items={items}
          selectionType="single"
          empty={
            <EmptyGridNotification
              title={i18n.emptyPipelines}
              subTitle={i18n.emptyPipelinesSubTitle}
              actionButtonText={i18n.emptyPipelinesResolve}
              actionButtonOnClick={emptyPipelinesResolveAction}
            />
          }
          filter={
            <TextFilter
              {...filterProps}
              filteringPlaceholder={i18n.findPipelinesPlaceholder}
              filteringAriaLabel={i18n.findPipelinesPlaceholder}
            />
          }
          pagination={<Pagination {...paginationProps} />}
          columnDefinitions={columnDefinitions}
          contentDensity="compact"
          wrapLines
        />
        {isRetirePipelineModalOpen && <UserPrompt
          onConfirm={retirePipeline}
          onCancel={() => setIsRetirePipelineModalOpen(false)}
          headerText={i18n.retirePipelineHeader}
          content={
            <SpaceBetween direction='vertical' size='l'>
              <Box>{i18n.retirePipelineMessage1}<b>{getSelectedItem()?.pipelineName}</b>.</Box>
              <Box>{i18n.retirePipelineMessage2}</Box>
              <Box>{i18n.retirePipelineMessage3}</Box>
            </SpaceBetween>
          }
          cancelText={i18n.retirePipelineCancelText}
          confirmText={i18n.retirePipelineConfirmText}
          confirmButtonLoading={isRetireInProgress}
          visible={isRetirePipelineModalOpen}
        />}
        {isCreateImageModalOpen && <UserPrompt 
          onConfirm={createImage}
          onCancel={() => setIsCreateImageModalOpen(false)}
          headerText={i18n.createImageHeader}
          content={
            <SpaceBetween direction='vertical' size='l'>
              <Box>{i18n.createImageMessage1}<b>{getSelectedItem()?.pipelineName}</b>.</Box>
              <Box>{i18n.createImageMessage2}</Box>
              <Box>{i18n.createImageMessage3}</Box>
            </SpaceBetween>
          }
          cancelText={i18n.createImageCancelText}
          confirmText={i18n.createImageConfirmText}
          confirmButtonLoading={isCreateImageInProgress}
          visible={isCreateImageModalOpen}
          data-test="user-prompt-create-image"
        />}
      </>
    );
  }


  function emptyPipelinesResolveAction() {
    navigateTo(RouteNames.CreatePipeline);
  }

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
              <li><b>{i18n.infoPanelPoint5}</b><br />{i18n.infoPanelPoint5Message}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};

export { Pipelines };
