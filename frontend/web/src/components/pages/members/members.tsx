import { useCallback, useEffect, useMemo } from 'react';
import {
  Button,
  ContentLayout,
  Container,
  Header,
  ColumnLayout,
  Box,
  Tabs,
  HelpPanel,
  SpaceBetween
} from '@cloudscape-design/components';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { Enrolments } from './enrolments';
import { i18n } from './members.translations';
import { useEnrolments } from './members.logic';
import { RoleAccessToggle } from '../shared/role-access-toggle';
import { ProjectUsers } from '../projects/project-details/project-users';
import { useRecoilValue } from 'recoil';
import { selectedProjectState, RoleBasedFeature } from '../../../state';
import { useProjectUsers } from '../projects/project-details/project-users.logic';
import { useLocalStorage } from '../../../hooks';
import { GetProjectEnrolmentsResponseItem } from '../../../services/API/proserve-wb-projects-api';

const TAB_ID_MEMBERS = 'members';
const TAB_ID_REQUESTS = 'requests';

export type EnhancedProjectEnrolmentResponseItem = GetProjectEnrolmentsResponseItem
& { isDuplicate: boolean };

export const Members = () => {
  const [selectedTab, setSelectedTab] = useLocalStorage('project-members#last-selected-tab');
  const selectedProject = useRecoilValue(selectedProjectState);

  const {
    projectUsers,
    usersLoading,
    loadProjectUsers,
    unassignUsers,
    userUnassignInProgress,
  } = useProjectUsers({ projectId: selectedProject.projectId ?? '' });

  const { navigateTo, getPathFor } = useNavigationPaths();
  const {
    enrolments,
    status,
    defaultStatus,
    setStatus,
    handleApproveEnrolments,
    handleRejectEnrolments,
    isLoading,
    loadEnrolments,
    isApproveLoading,
    isDeclineLoading,
  } = useEnrolments({ onApprovalSuccess: loadProjectUsers });

  const isTabPreSelected = useCallback(() => {
    return !!selectedTab && new Set([TAB_ID_MEMBERS, TAB_ID_REQUESTS]).has(selectedTab);
  }, [selectedTab]);

  useEffect(() => {
    if (!isTabPreSelected()) {
      setSelectedTab(TAB_ID_MEMBERS);
    }
  }, [isTabPreSelected, setSelectedTab]);

  const enhancedEnrolments: EnhancedProjectEnrolmentResponseItem[] = useMemo(() => {
    // hashmap to contain with string as key and enrolment as value
    const memberIndex: Set<string> = new Set(projectUsers.filter(
      user => user.userEmail
    ).map(user => {
      return user.userEmail ?? '';
    }));

    return enrolments.map(enrolment => {
      const enhancedEnrolment: EnhancedProjectEnrolmentResponseItem = { isDuplicate: false, ...enrolment };
      // eslint-disable-next-line @stylistic/max-len
      if (enhancedEnrolment.userEmail && memberIndex.has(enhancedEnrolment.userEmail) && enhancedEnrolment.status === 'Pending') {
        enhancedEnrolment.isDuplicate = true;
      }
      return enhancedEnrolment;
    });
  }, [enrolments, projectUsers]);

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.ProjectMembers) },
        ]}
        content={
          <ContentLayout header={renderHeader()}>
            <Container header={<Header variant="h2">{i18n.overview}</Header>}>
              <ColumnLayout columns={2} variant="text-grid">
                <div>
                  <Box variant="awsui-key-label" fontWeight="bold">{i18n.membersOverviewCardMemberSum}</Box>
                  <Box
                    color="text-status-info"
                    fontSize="heading-xl"
                    fontWeight="bold"
                  >
                    <b>{projectUsers.length}</b>
                  </Box>
                </div>
                <div>
                  <Box
                    variant="awsui-key-label"
                    fontWeight="bold"
                  >
                    {i18n.membersOverviewCardEnrolmentSum}
                  </Box>
                  <Box
                    color="text-status-info"
                    fontSize="heading-xl"
                    fontWeight="bold"
                  >
                    <b>{enrolments.length}</b>
                  </Box>
                </div>
              </ColumnLayout>
            </Container>
            <Tabs
              activeTabId={selectedTab || TAB_ID_MEMBERS}
              onChange={(e) => setSelectedTab(e.detail.activeTabId)}
              tabs={[
                {
                  label: i18n.tabMembers,
                  id: TAB_ID_MEMBERS,
                  content: <ProjectUsers
                    projectUsers={projectUsers}
                    usersLoading={usersLoading}
                    loadProjectUsers={loadProjectUsers}
                    unassignUsers={unassignUsers}
                    userUnassignInProgress={userUnassignInProgress}
                  />
                },
                {
                  label: i18n.tabRequests,
                  id: TAB_ID_REQUESTS,
                  content: <Enrolments
                    enrolments={enhancedEnrolments}
                    status={status}
                    defaultStatus={defaultStatus}
                    setStatus={setStatus}
                    handleApproveEnrolments={handleApproveEnrolments}
                    handleRejectEnrolments={handleRejectEnrolments}
                    isLoading={isLoading}
                    isApproveLoading={isApproveLoading}
                    isDeclineLoading={isDeclineLoading}
                    reloadEnrolments={loadEnrolments}
                  />
                }
              ]}
              ariaLabel={i18n.tabsAriaLabel}
            />
          </ContentLayout>
        }
        contentType="default"
        tools={renderTools()}
      />
    </>
  );

  function renderHeader() {
    return <Header
      variant='awsui-h1-sticky'
      actions={
        <RoleAccessToggle feature={RoleBasedFeature.AddUserToProgram}>
          <Button
            onClick={navigateToAssignUserScreen}
            variant='primary' data-test="onboard-button">{i18n.buttonAddUser}</Button>
        </RoleAccessToggle>
      }
    >{i18n.layoutHeader}</Header>;
  }

  function navigateToAssignUserScreen() {
    navigateTo(RouteNames.ProjectUserAssignment);
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
            </ul>
          </Box>
          <Box>
            <p>{i18n.infoPanelMessage3}</p>
            <ul>
              <li><b>{i18n.infoPanelPoint4}</b><br />{i18n.infoPanelPoint4Message}</li>
              <li><b>{i18n.infoPanelPoint5}</b><br />{i18n.infoPanelPoint5Message}</li>
              <li><b>{i18n.infoPanelPoint6}</b><br />{i18n.infoPanelPoint6Message}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }

};
