import { FC, Dispatch, useState, useMemo, useCallback, SetStateAction } from 'react';
import {
  TextFilter,
  Table,
  Header,
  SpaceBetween,
  Button,
  TableProps,
  StatusIndicator,
  Select,
  SelectProps,
  Pagination
} from '@cloudscape-design/components';
import { parseISO, format } from 'date-fns';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { EnhancedProjectEnrolmentResponseItem } from './members';
import { CopyText, NoMatchTableNotification } from '../shared';
import { DeclineModal } from './decline-modal';
import { getEnrolmentStatusType } from './helpers';
import { i18n } from './enrolments.translations';
import { ApproveModal } from './approve-modal';
import { CompareDates } from '../shared/compare-dates';

type Props = {
  enrolments: EnhancedProjectEnrolmentResponseItem[],
  status: SelectProps.Option,
  defaultStatus: SelectProps.Option,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setStatus: Dispatch<SetStateAction<any>>,
  handleApproveEnrolments: (
    enrolmentIds: string[], userIds: string[], roleOption: SelectProps.Option
  ) => void,
  handleRejectEnrolments: (ids: string[], reason: string) => void,
  isLoading: boolean,
  isApproveLoading: boolean,
  isDeclineLoading: boolean,
  reloadEnrolments: () => void,
};

const EMPTY_COUNT = 0;
const PENDING_STATE = 'Pending';


export const Enrolments: FC<Props> = ({
  handleApproveEnrolments,
  handleRejectEnrolments,
  status,
  defaultStatus,
  setStatus,
  enrolments,
  isLoading,
  reloadEnrolments,
  isApproveLoading,
  isDeclineLoading,
}) => {
  const [isOpenDeclineModal, setIsOpenDeclineModal] = useState(false);
  const [isOpenApproveModal, setIsOpenApproveModal] = useState(false);
  const selectStatusOptions = [
    { label: i18n.statusOption0, value: '0' },
    { label: i18n.statusOption1, value: '1' },
    { label: i18n.statusOption2, value: '2' },
    { label: i18n.statusOption3, value: '3' },
  ];
  const DEFAULT_PAGE_SIZE = 100;

  const columnDefinitions: TableProps.ColumnDefinition<EnhancedProjectEnrolmentResponseItem>[] = [
    {
      id: 'duplicate',
      header: i18n.tableDuplicateTitle,
      cell: item => {
        if (!item.isDuplicate || item.status !== PENDING_STATE) {
          return '';
        }
        return <StatusIndicator type="warning">{i18n.duplicationWarning}</StatusIndicator>;
      }
    },
    {
      id: 'ticketId',
      header: i18n.tableTicketIDTitle,
      cell: item => item.ticketId,
    },
    {
      id: 'userId',
      header: i18n.tableMemberIDTitle,
      cell: item => <> {
        !!item.userId &&
        <CopyText
          copyText={item.userId ?? ''}
          copyButtonLabel={i18n.copyButtonLabel}
          successText={i18n.copySuccess}
          errorText={i18n.copyError} />
      } </>,
      sortingField: 'userId',
    },
    {
      id: 'userEmail',
      header: i18n.tableMemberEMailTitle,
      cell: item => <> {
        !!item.userEmail &&
        <CopyText
          copyText={item.userEmail ?? ''}
          copyButtonLabel={i18n.copyButtonLabel}
          successText={i18n.copySuccess}
          errorText={i18n.copyError} />
      } </>,
      sortingField: 'userEmail',
    },
    {
      id: 'createDate',
      header: i18n.tableReceivedTitle,
      cell: item => {
        if (!item.createDate) {
          return '';
        }

        return format(parseISO(item.createDate), 'dd.MM.yyyy, HH:mm');
      },
      sortingField: 'createDate',
      sortingComparator: (
        a: EnhancedProjectEnrolmentResponseItem,
        b: EnhancedProjectEnrolmentResponseItem) => CompareDates(a.createDate, b.createDate)
    },
    {
      id: 'status',
      header: i18n.tableStatusTitle,
      cell: item => <StatusIndicator type={getEnrolmentStatusType(item.status)}>
        {item.status}
      </StatusIndicator>,
      sortingField: 'status',
    },
    {
      id: 'resolveDate',
      header: i18n.tableResolvedTitle,
      cell: item => {
        if (!item.resolveDate) {
          return '';
        }

        return format(parseISO(item.resolveDate), 'dd.MM.yyyy, HH:mm');
      },
      sortingField: 'resolveDate',
      sortingComparator: (
        a: EnhancedProjectEnrolmentResponseItem,
        b: EnhancedProjectEnrolmentResponseItem) => CompareDates(a.resolveDate, b.resolveDate)
    },
    {
      id: 'approver',
      header: i18n.tableManagerTitle,
      cell: item => item.approver,
      sortingField: 'approver',
    },
    {
      id: 'source',
      header: i18n.tableSource,
      cell: item => {
        if (item.sourceSystem === 'RTC') {
          return 'RTC';
        }
        return 'WEB UI';
      },
      sortingField: 'source',
    }
  ];

  const createDateColumnIndex = 4;

  const { items, actions, filterProps, collectionProps, paginationProps } = useCollection(
    enrolments,
    {
      filtering: {
        empty: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => resetFilter()}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle}
        />,
        noMatch: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonAction={() => resetFilter()}
          buttonText={i18n.tableFilterNoResultActionText}
          subtitle={i18n.tableFilterNoResultSubtitle} />,
      },
      selection: {},
      sorting: { defaultState: { sortingColumn: columnDefinitions[createDateColumnIndex] } },
      pagination: { pageSize: DEFAULT_PAGE_SIZE },
    }
  );

  function resetFilter() {
    actions.setFiltering('');
    setStatus(defaultStatus);
  }

  const selectedEnrolmentIds = useMemo(
    () => collectionProps.selectedItems?.map(item => String(item.id)) ?? [],
    [collectionProps.selectedItems]
  );

  const selectedUserIds = useMemo(
    () => collectionProps.selectedItems?.map(item => String(item.userId)) ?? [],
    [collectionProps.selectedItems]
  );

  const handleSubmitReject = useCallback((reason: string) => {
    handleRejectEnrolments(selectedEnrolmentIds, reason);
    setIsOpenDeclineModal(false);
  }, [selectedEnrolmentIds, setIsOpenDeclineModal]);

  const handleSubmitApprove = useCallback((roleOption: SelectProps.Option) => {
    handleApproveEnrolments(selectedEnrolmentIds, selectedUserIds, roleOption);
    setIsOpenApproveModal(false);
  }, [selectedUserIds, setIsOpenApproveModal]);

  return (
    <>
      <Table
        {...collectionProps}
        columnDefinitions={columnDefinitions}
        header={
          <Header
            counter={`(${enrolments.length})`}
            actions={
              <SpaceBetween direction="horizontal" size="m">
                <Button
                  loading={isLoading}
                  onClick={() => reloadEnrolments()}
                  iconName='refresh' />
                <Button
                  onClick={() => { setIsOpenDeclineModal(true); }}
                  disabled={!canDecline()}
                  data-test="decline-btn"
                >
                  {i18n.declineRequestButton}
                </Button>
                <Button
                  variant="primary"
                  onClick={() => setIsOpenApproveModal(true)}
                  loading={isApproveLoading}
                  disabled={!canApprove()}
                  data-test="approve-btn"
                >
                  {i18n.approveRequestButton}
                </Button>
              </SpaceBetween>
            }
          >
            {i18n.registrationRequests}
          </Header>
        }
        isItemDisabled={item => item.status !== 'Pending'}
        items={items}
        selectionType="multi"
        pagination={<Pagination {...paginationProps} />}
        filter={
          <SpaceBetween size="m" direction="horizontal">
            <TextFilter
              {...filterProps}
              filteringAriaLabel={i18n.filterEnrolmentsPlaceholder}
              filteringPlaceholder={i18n.filterEnrolmentsPlaceholder}
            />
            <Select
              options={selectStatusOptions}
              selectedAriaLabel="Selected"
              selectedOption={status}
              onChange={event => {
                setStatus(event.detail.selectedOption);
              }}
              expandToViewport={true}
              data-test="enrolment-status-filter"
            />
          </SpaceBetween>
        }
        loading={isLoading}
        visibleColumns={[
          'duplicate',
          'userId',
          'userEmail',
          'createDate',
          'status',
          'resolveDate',
          'approver',
          'source'
        ]}
        data-test="enrolments-table"
      />
      <DeclineModal
        isOpen={isOpenDeclineModal}
        onClose={() => setIsOpenDeclineModal(false)}
        onSubmit={handleSubmitReject}
        isLoading={isDeclineLoading}
      />
      <ApproveModal
        isOpen={isOpenApproveModal}
        onClose={() => setIsOpenApproveModal(false)}
        onSubmit={handleSubmitApprove}
        isLoading={isApproveLoading}
        data-test="enrolments-approve-modal"
      />
    </>
  );

  function canApprove() {
    return selectedEnrolmentIds.length > EMPTY_COUNT;
  }

  function canDecline() {
    return selectedEnrolmentIds.length > EMPTY_COUNT;
  }
};