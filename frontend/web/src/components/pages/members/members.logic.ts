import { useEffect, useState } from 'react';
import { useRecoilValue } from 'recoil';
import { projectsAPI } from '../../../services';
import { useNotifications } from '../../layout';
import { extractErrorResponseMessage } from '../../../utils/api-helpers';
import {
  GetProjectEnrolmentsResponseItem
} from '../../../services/API/proserve-wb-projects-api';
import { ProjectRoles, selectedProjectState } from '../../../state';
import { i18n } from './members.translations';
import { SelectProps } from '@cloudscape-design/components';
import { DEFAULT_MEMBER_PAGE_SIZE } from '../../../constants/paging';

type Props = {
  onApprovalSuccess?: () => void,
};

export const useEnrolments = ({
  onApprovalSuccess,
}: Props) => {
  const { showErrorNotification, showSuccessNotification } = useNotifications();
  const selectedProject = useRecoilValue(selectedProjectState);
  const [pagingToken, setPagingToken] = useState<object | undefined | null>();
  const [isLoading, setIsLoading] = useState(false);
  const [enrolments, setEnrolments] = useState<GetProjectEnrolmentsResponseItem[]>([]);
  const [isApproveLoading, setIsApproveLoading] = useState(false);
  const [isDeclineLoading, setIsDeclineLoading] = useState(false);
  const defaultStatus = { value: '1', label: 'Pending' };
  const [status, setStatus] = useState<SelectProps.Option>(defaultStatus);

  const loadEnrolments = (pagingToken?: object) => {
    if (!selectedProject.projectId) {
      return;
    }

    let enrolmentStatus = undefined;
    if (status.label !== 'All') {
      enrolmentStatus = status.label;
    }

    setIsLoading(true);

    projectsAPI.getProjectEnrolments(
      selectedProject.projectId,
      DEFAULT_MEMBER_PAGE_SIZE.toString(),
      JSON.stringify(pagingToken),
      enrolmentStatus
    )
    // eslint-disable-next-line complexity
      .then((response) => {
        if (pagingToken) {
          let distinctEnrolments: GetProjectEnrolmentsResponseItem [] = [];

          if (response.enrolments) {
            distinctEnrolments = response.enrolments?.filter(
              a => !enrolments?.some(item => item.id === a.id));
          }

          setEnrolments([...enrolments, ...distinctEnrolments]);
        } else {
          setEnrolments(response.enrolments ?? []);
        }

        if (response.nextToken) {
          setPagingToken(response.nextToken);
        }
      }).catch(async e => {
        showErrorNotification({
          header: i18n.enrolmentsFetchErrorTitle,
          content: await extractErrorResponseMessage(e)
        });
      }).finally(() => {
        setIsLoading(false);
      });
  };

  useEffect(() => {
    loadEnrolments();
  }, [selectedProject, status]);

  useEffect(() => {
    if (pagingToken) {
      loadEnrolments(pagingToken);
    }
  }, [pagingToken]);

  const handleApproveEnrolments = async (
    enrolmentIds: string[], userIds: string[], roleOption: SelectProps.Option
  ) => {
    try {
      if (!selectedProject.projectId) {
        return;
      }

      setIsApproveLoading(true);
      await projectsAPI.updateEnrolments(
        selectedProject.projectId,
        { enrolmentIds, status: 'Approved' }
      );

      if (roleOption.value !== '1') {
        await projectsAPI.reassignProjectUsers(
          selectedProject.projectId,
          { roles: getSelectedRoles(roleOption), userIds: userIds }
        );
      }
      await loadEnrolments();
      await onApprovalSuccess?.();
      showSuccessNotification({
        header: i18n.enrolmentsApproveSuccessTitle,
        content: i18n.enrolmentsApproveContent
      });
    } catch (error) {
      showErrorNotification({
        header: i18n.enrolmentsApproveErrorTitle,
        content: await extractErrorResponseMessage(error)
      });
    } finally {
      setIsApproveLoading(false);
    }
  };

  const handleRejectEnrolments = async (enrolmentIds: string[], reason: string) => {
    try {
      if (!selectedProject.projectId) {
        return;
      }

      setIsDeclineLoading(true);
      await projectsAPI.updateEnrolments(
        selectedProject.projectId,
        { enrolmentIds, status: 'Rejected', reason }
      );
      await loadEnrolments();
      showSuccessNotification({
        header: i18n.enrolmentsRejectSuccessTitle,
        content: i18n.enrolmentsRejectContent
      });
    } catch (error) {
      showErrorNotification({
        header: i18n.enrolmentsRejectErrorTitle,
        content: await extractErrorResponseMessage(error)
      });
    } finally {
      setIsDeclineLoading(false);
    }
  };

  return {
    enrolments,
    status,
    defaultStatus,
    setStatus,
    isLoading,
    handleApproveEnrolments,
    handleRejectEnrolments,
    loadEnrolments,
    isApproveLoading,
    isDeclineLoading
  };
};

// eslint-disable-next-line complexity
function getSelectedRoles(roleOption: SelectProps.Option) {
  switch (roleOption.value) {
    case '1':
      return [ProjectRoles.PlatformUser];
    case '2':
      return [ProjectRoles.BetaUser];
    case '3':
      return [ProjectRoles.ProductContributor];
    case '4':
      return [ProjectRoles.PowerUser];
    case '5':
      return [ProjectRoles.ProgramOwner];
    case '6':
      return [ProjectRoles.Admin];
    default:
      return [];
  }
}