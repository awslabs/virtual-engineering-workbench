import {
  Button,
  Header,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
  TextFilter
} from '@cloudscape-design/components';
import {
  ComponentVersionTestExecutionSummary
} from '../../../../../services/API/proserve-wb-packaging-api';
import { i18n } from './view-component-version.translations';
import { CopyText, EmptyGridNotification, NoMatchTableNotification, UserDate } from '../../../shared';
import { intervalToDuration, differenceInSeconds, formatDuration } from 'date-fns';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { useEffect } from 'react';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../../../state';
import { useViewComponentVersionTests } from './view-component-version-tests.logic';
import { packagingAPI } from '../../../../../services';
import { TestExecutionStatus } from '../../shared/test-execution-status';

export const ViewComponentVersionTests = ({
  componentId,
  versionId,
}: {
  componentId: string,
  versionId: string,
}) => {
  const selectedProject = useRecoilValue(selectedProjectState);
  const PAGE_SIZE = 20;
  const PAGE_INDEX = 1;

  const {
    testExecutions,
    testExecutionsLoading,
    loadTestExecutions,
    selectedTestExecution,
    setSelectedTestExecution,
    downloadLogs,
    downloadLogsInProgress
  } = useViewComponentVersionTests({
    serviceApi: packagingAPI,
    projectId: selectedProject.projectId || '',
    componentId: componentId,
    versionId: versionId
  });

  const formatTestDuration = (startDate: string, endDate: string) => {
    return formatDuration(intervalToDuration({
      start: new Date(startDate),
      end: new Date(endDate),
    }));
  };

  const columnDefinitions: TableProps.ColumnDefinition<ComponentVersionTestExecutionSummary>[] = [
    {
      id: 'testExecutionId',
      header: i18n.tableTestsColumnHeaderExecutionId,
      cell: e => <CopyText
        copyText={e.testExecutionId}
        successText={i18n.testExecutionIdCopySuccess}
        errorText={i18n.testExecutionIdCopyError}
        copyButtonLabel=''
      />,
      sortingField: 'testExecutionId',
    },
    {
      id: 'instanceArchitecture',
      header: i18n.tableTestsColumnHeaderArchitecture,
      cell: e => e.instanceArchitecture,
      sortingField: 'instanceArchitecture',
    },
    {
      id: 'instanceOsVersion',
      header: i18n.tableTestsColumnHeaderOSVersion,
      cell: e => e.instanceOsVersion,
      sortingField: 'instanceOsVersion',
    },
    {
      id: 'instancePlatform',
      header: i18n.tableTestsColumnHeaderPlatform,
      cell: e => e.instancePlatform,
      sortingField: 'instancePlatform',
    },
    {
      id: 'status',
      header: i18n.tableTestsColumnHeaderExecutionStatus,
      cell: e => <TestExecutionStatus status={e.status}/>,
      sortingField: 'status',
    },
    {
      id: 'testExecutionDuration',
      header: i18n.tableTestsColumnHeaderDuration,
      cell: e => formatTestDuration(e.createDate, e.lastUpdateDate),
      sortingComparator: (a, b) =>
        differenceInSeconds(new Date(b.createDate), new Date(b.lastUpdateDate)) -
        differenceInSeconds(new Date(a.createDate), new Date(a.lastUpdateDate)),
      sortingField: 'testExecutionDuration'
    },
    {
      id: 'testExecutionLastUpdate',
      header: i18n.tableTestsColumnHeaderLastUpdate,
      cell: e => <UserDate date={e.lastUpdateDate} />,
      sortingField: 'lastUpdateDate'
    },
  ];

  const { items, actions, filterProps, collectionProps, paginationProps } = useCollection(
    testExecutions || [],
    {
      filtering: {
        empty: <EmptyGridNotification
          title={i18n.tableTestsEmptyTitle}
          subTitle={i18n.tableTestsEmptySubtitle}
        />,
        noMatch: <NoMatchTableNotification
          title={i18n.tableTestsFilterNoResultTitle}
          buttonAction={() => actions.setFiltering('')}
          buttonText={i18n.tableTestsFilterNoResultActionText}
          subtitle={i18n.tableTestsFilterNoResultSubtitle} />,
      },
      selection: {},
      sorting: { defaultState: { sortingColumn: columnDefinitions[6], isDescending: true } },
      pagination: { defaultPage: PAGE_INDEX, pageSize: PAGE_SIZE }
    }
  );

  useEffect(() => {
    setSelectedTestExecution?.(collectionProps.selectedItems && collectionProps.selectedItems[0]);
  }, [collectionProps, setSelectedTestExecution]);

  return <Table
    {...collectionProps}
    header={
      <Header
        variant='h2'
        counter={`(${testExecutions?.length})`}
        actions={
          <SpaceBetween direction='horizontal' size='s'>
            <Button
              data-test='button-refresh-table'
              iconName='refresh'
              onClick={loadTestExecutions}
              loading={testExecutionsLoading}
            />
            <Button
              onClick={downloadLogs}
              data-test="download-test-execution"
              disabled={
                !selectedTestExecution ||
                ['PENDING', 'RUNNING'].includes(selectedTestExecution.status)
              }
              loading={downloadLogsInProgress}
            >
              {i18n.buttonDownloadTestExecution}
            </Button>
          </SpaceBetween>
        }
      >
        {i18n.testExecutionsHeader}
      </Header>
    }
    loading={testExecutionsLoading}
    items={items}
    selectionType="single"
    filter={
      <TextFilter
        {...filterProps}
        filteringPlaceholder={i18n.findTestsPlaceholder}
        filteringAriaLabel={i18n.findTestsPlaceholder}
      />
    }
    pagination={<Pagination
      {...paginationProps}
    />}
    columnDefinitions={columnDefinitions}
    data-test="component-version-test-executions"
  />;
};