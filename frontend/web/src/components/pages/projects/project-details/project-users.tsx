import { useCollection } from '@cloudscape-design/collection-hooks';
import {
  Badge,
  Button,
  Header,
  Pagination, PropertyFilter, PropertyFilterProps,
  SpaceBetween,
  Table,
  TableProps,
} from '@cloudscape-design/components';
import { useState } from 'react';
import { GetProjectAssignmentsResponseItem } from '../../../../services/API/proserve-wb-projects-api';
import { ProjectRoles, RoleBasedFeature, selectedProjectState } from '../../../../state';
import { CopyText } from '../../shared';
import { RoleAccessToggle } from '../../shared/role-access-toggle';
import { UserPrompt } from '../../shared/user-prompt';
import { NoMatchTableNotification } from '../../shared/no-match-table-notification';
import { USER_ROLE_MAP, USER_ROLE_LEVEL_MAP } from './project-users.static';
import { useNavigationPaths } from '../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../layout/navigation/navigation.static';
import { ProjectUserAssignmentRoles } from '../project-user-assignment/project-user-assignment-roles';
import { useProjectUserReAssignment } from '../project-user-reassignment/project-user-reassignment.logic';
import { useRecoilValue } from 'recoil';
import { useRoleAccessToggle } from '../../../../hooks/role-access-toggle';
import { useCloudscapeTablePersisentState } from '../../../../hooks';


const DEFAULT_PAGE_SIZE = 100;
const EMPTY = 0;
const LESS_THAN = -1;
const GREATER_THAN = 1;
const EQUAL = 0;

const i18n = {
  tableHeaderUserId: 'User ID',
  tableHeaderRoles: 'Member role',
  tableEmptyTitle: 'No users',
  tableEmptySubtitle: 'Program has no users.',
  tableEmptyActionText: 'Add new user',
  tableFilterNoResultTitle: 'No users found',
  tableFilterNoResultSubtitle: 'No users were found using your search criteria.',
  tableFilterNoResultActionText: 'Clear filter',
  tableLoading: 'Loading users',
  copyButtonLabel: 'Copy',
  copySuccess: 'Copied',
  copyError: 'Unable to copy',
  buttonEditUserRole: 'Update member roles',
  buttonRemoveUser: 'Offboard member(s)',
  tableHeader: 'Program members',
  filterPlaceholder: 'Find members',
  tableHeaderEmail: 'Member email',
  unassignModalHeader: 'Offboard member',
  reassignModalHeader: 'Update member roles',
  unassignModalOK: 'Continue',
  reassignModalOK: 'Confirm',
  unassignModalCancel: 'Cancel',
  reassignModalCancel: 'Cancel',
  unassignModalText1: 'You are about to offboard:',
  reassignModalText1: 'You are about to update the roles for ',
  unassignModalText2: 'If you continue, their assigned roles and access to the program will be revoked.',
  unassignModalText3: 'Do you want to proceed?',
  reassignModalText2: 'members.',
  reassignModalText3: ` Selecting a new role will apply to all of the members 
  currently selected and may result in an increase or decrease in permissions.`,
};

const propertyFilterI18nStrings: PropertyFilterProps.I18nStrings = {
  filteringAriaLabel: 'Filter',
  dismissAriaLabel: 'Dismiss',
  filteringPlaceholder: 'Find members',
  groupValuesText: 'Values',
  groupPropertiesText: 'Properties',
  operatorsText: 'Operators',
  operationAndText: 'and',
  operationOrText: 'or',
  operatorLessText: 'Less than',
  operatorLessOrEqualText: 'Less than or equal',
  operatorGreaterText: 'Greater than',
  operatorGreaterOrEqualText: 'Greater than or equal',
  operatorContainsText: 'Contains',
  operatorDoesNotContainText: 'Does not contain',
  operatorEqualsText: 'Equals',
  operatorDoesNotEqualText: 'Does not equal',
  editTokenHeader: 'Edit filter',
  propertyText: 'Property',
  operatorText: 'Operator',
  valueText: 'Value',
  cancelActionText: 'Cancel',
  applyActionText: 'Apply',
  allPropertiesLabel: 'All properties',
  tokenLimitShowMore: 'Show more',
  tokenLimitShowFewer: 'Show fewer',
  clearFiltersText: 'Clear filters',
  removeTokenButtonAriaLabel: token => `Remove token ${token.propertyKey} ${token.operator} ${token.value}`,
  enteredTextLabel: text => `Use: "${text}"`,
};

type ProjectUsersProps = {
  projectUsers: GetProjectAssignmentsResponseItem[],
  usersLoading: boolean,
  loadProjectUsers: (token?: object) => void,
  unassignUsers: (ids: string[]) => void,
  userUnassignInProgress: boolean,
};

function getRoleName(role: string) {
  const r = role as ProjectRoles;
  if (r !== undefined) {
    const roleName = USER_ROLE_MAP[r];
    const roleLevel = USER_ROLE_LEVEL_MAP[r];
    return 'Lvl ' + roleLevel + ' - ' + roleName;
  }
  return role;
}

function joinRoleNames(roles?: string[]) {
  return roles?.map(r => getRoleName(r || '').toUpperCase()).join() || '';
}

const COLUMN_DEFINITIONS: TableProps.ColumnDefinition<GetProjectAssignmentsResponseItem>[] = [
  {
    id: 'userId',
    header: i18n.tableHeaderUserId,
    cell: u => <> {
      !!u.userId &&
      <CopyText
        copyText={u.userId ?? ''}
        copyButtonLabel={i18n.copyButtonLabel}
        successText={i18n.copySuccess}
        errorText={i18n.copyError} />
    } </>,
    sortingField: 'userId',
  },
  {
    id: 'userEmail',
    header: i18n.tableHeaderEmail,
    cell: u => <> {
      !!u.userEmail &&
      <CopyText
        copyText={u.userEmail ?? ''}
        copyButtonLabel={i18n.copyButtonLabel}
        successText={i18n.copySuccess}
        errorText={i18n.copyError} />
    } </>,
    sortingField: 'userEmail',
  },
  {
    id: 'userRoles',
    header: i18n.tableHeaderRoles,
    cell: u => <SpaceBetween size={'xs'} direction='horizontal'>
      {/* eslint-disable-next-line @stylistic/max-len */}
      {u.roles?.map(r => <Badge color="blue" key={r}><b>{getRoleName((r || '').toUpperCase())}</b></Badge>) ?? []}
    </SpaceBetween>,
    sortingComparator: (a, b) => {
      const rolesOfA = joinRoleNames(a.roles);
      const rolesOfB = joinRoleNames(b.roles);
      return rolesOfA < rolesOfB ? LESS_THAN : rolesOfA > rolesOfB ? GREATER_THAN : EQUAL;
    }
  },
];

// eslint-disable-next-line complexity
export function projectUsers({
  projectUsers,
  usersLoading,
  loadProjectUsers,
  unassignUsers,
  userUnassignInProgress,
}: ProjectUsersProps) {
  const { navigateTo } = useNavigationPaths();
  const selectedProject = useRecoilValue(selectedProjectState);
  const [unassignConfirmVisible, setUnassignConfirmVisible] = useState(false);
  const [reassignConfirmVisible, setReassignConfirmVisible] = useState(false);
  const isFeatureAccessible = useRoleAccessToggle();

  if (!selectedProject) {
    navigateTo(RouteNames.Programs);
  }
  const {
    items,
    actions,
    collectionProps,
    paginationProps,
    propertyFilterProps
  } = useCollection(
    projectUsers,
    {
      propertyFiltering: {
        empty: <NoMatchTableNotification
          title={i18n.tableEmptyTitle}
          buttonText={i18n.tableEmptyActionText}
          buttonAction={navigateToAssignUserScreen}
          subtitle={i18n.tableEmptySubtitle}
          requiredFeature={RoleBasedFeature.AddUserToProgram}
        />,
        noMatch: <NoMatchTableNotification
          title={i18n.tableFilterNoResultTitle}
          buttonText={i18n.tableFilterNoResultActionText}
          buttonAction={() => actions.setFiltering('')}
          subtitle={i18n.tableFilterNoResultSubtitle} />,
        filteringProperties: [
          {
            key: 'userId',
            operators: ['=', ':', '!='],
            propertyLabel: 'User ID',
            groupValuesLabel: 'User ID values'
          }, {
            key: 'userEmail',
            operators: ['=', ':', '!='],
            propertyLabel: 'Member email',
            groupValuesLabel: 'Member email values'
          }, {
            key: 'roles',
            operators: ['=', ':', '!='],
            propertyLabel: 'Member role',
            groupValuesLabel: 'Member role values'
          }
        ]
      },
      pagination: { pageSize: DEFAULT_PAGE_SIZE },
      sorting: { defaultState: { sortingColumn: COLUMN_DEFINITIONS[0] } },
      selection: {
        keepSelection: true,
        trackBy: 'userId'
      }
    }
  );

  const {
    userReAssignmentInProgress,
    reAssignUsers,
    memberRoleLevel,
    setMemberRoleLevel
  } = useProjectUserReAssignment(
    {
      projectId: selectedProject.projectId || '',
      loadProjectUsers: loadProjectUsers
    }
  );

  const { onSortingChange } = useCloudscapeTablePersisentState<GetProjectAssignmentsResponseItem>({
    key: 'project-user',
    columnDefinitions: COLUMN_DEFINITIONS,
    setSorting: actions.setSorting,
  });


  return <>
    {renderDeprovisionPrompt()}
    {renderReassignedPrompt()}
    <Table
      {...collectionProps}
      columnDefinitions={COLUMN_DEFINITIONS}
      items={items}
      loading={usersLoading || userReAssignmentInProgress || userUnassignInProgress}
      loadingText={i18n.tableLoading}
      trackBy="userId"
      selectionType='multi'
      onSortingChange={onSortingChange}
      header={
        <Header
          counter={`(${projectUsers.length})`}
          actions={
            <SpaceBetween size={'xs'} direction={'horizontal'}>
              <Button
                loading={usersLoading}
                onClick={() => loadProjectUsers()}
                iconName='refresh' />
              <RoleAccessToggle feature={RoleBasedFeature.ReassignRoleOfProgramUser}>
                <Button
                  onClick={handleReassignAction}
                  disabled={!canReassign()}
                  data-test="reonboard-button">{i18n.buttonEditUserRole}</Button>
              </RoleAccessToggle>
              <RoleAccessToggle feature={RoleBasedFeature.RemovePlatformUserFromProgram}>
                <Button
                  onClick={handleUnassignAction}
                  disabled={!canUnassign()}
                  data-test="offboard-button"
                >{i18n.buttonRemoveUser}</Button>
              </RoleAccessToggle>
            </SpaceBetween>
          }
        >
          {i18n.tableHeader}
        </Header>
      }
      pagination={<Pagination {...paginationProps} />}
      filter={
        <PropertyFilter
          {...propertyFilterProps}
          i18nStrings={propertyFilterI18nStrings}
          expandToViewport
          data-test="member-table-filter"
        />
      }
    />
  </>;

  function handleUnassignAction() {
    setUnassignConfirmVisible(true);
  }

  function handleReassignAction() {
    setReassignConfirmVisible(true);
  }

  function renderDeprovisionPrompt() {
    return <>
      <UserPrompt
        onConfirm={handleUnassignConfirm}
        onCancel={() => setUnassignConfirmVisible(false)}
        headerText={i18n.unassignModalHeader}
        content={createUnassignModalText()}
        cancelText={i18n.unassignModalCancel}
        confirmText={i18n.unassignModalOK}
        confirmButtonLoading={userUnassignInProgress}
        visible={unassignConfirmVisible}
        data-test='unassign-user-modal'
      />
    </>;
  }


  function renderReassignedPrompt() {
    return <>
      <UserPrompt
        onConfirm={handleReassignConfirm}
        onCancel={() => setReassignConfirmVisible(false)}
        headerText={i18n.reassignModalHeader}
        content={createReassignModalContent()}
        cancelText={i18n.reassignModalCancel}
        confirmText={i18n.reassignModalOK}
        confirmButtonLoading={userReAssignmentInProgress}
        visible={reassignConfirmVisible}
        data-test='reassign-user-modal'
      />
    </>;
  }

  function handleUnassignConfirm() {
    unassign();
    setUnassignConfirmVisible(false);
    actions.setSelectedItems([]);
  }

  function handleReassignConfirm() {
    reassign();
    setReassignConfirmVisible(false);
    actions.setSelectedItems([]);
  }

  function createUnassignModalText() {
    const listUsersToOffboard = collectionProps.selectedItems?.map((item) =>
      <li key={item.userId}><b>{item.userId} - {item.userEmail}</b></li>
    );
    return <>{i18n.unassignModalText1}<ul>{listUsersToOffboard}</ul>{i18n.unassignModalText2}
      <p>{i18n.unassignModalText3}</p></>;
  }


  function createReassignModalContent() {
    const membersLength = `${collectionProps.selectedItems?.length} ${i18n.reassignModalText2}`;
    return <>
      <SpaceBetween size='l'>
        <p>{i18n.reassignModalText1}<b>{membersLength}</b>{i18n.reassignModalText3}</p>

        <ProjectUserAssignmentRoles
          memberRoleLevel={memberRoleLevel}
          setMemberRoleLevel={setMemberRoleLevel}
          restrictOptions={isFeatureAccessible(RoleBasedFeature.ManageRoleFrontendAdmin) ? false : true}
        />
      </SpaceBetween>
    </>;
  }

  function navigateToAssignUserScreen() {
    navigateTo(RouteNames.ProjectUserAssignment);
  }

  function canUnassign() {
    return (collectionProps.selectedItems?.length || EMPTY) > EMPTY;
  }

  function canReassign() {
    const selectedItemsLengthForReassign = 1;
    if (!collectionProps.selectedItems) {
      return false;
    }
    return collectionProps.selectedItems?.length >= selectedItemsLengthForReassign;
  }

  function unassign() {
    unassignUsers(collectionProps.selectedItems?.map(user => user.userId ?? '') || []);
  }

  function reassign() {
    reAssignUsers(collectionProps.selectedItems?.map(user => user.userId ?? '') || []);
  }
}

export { projectUsers as ProjectUsers };