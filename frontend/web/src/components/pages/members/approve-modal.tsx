import { FC, useState } from 'react';
import { Box, SpaceBetween, Button, Modal, SelectProps } from '@cloudscape-design/components';
import { i18n } from './members.translations';
// eslint-disable-next-line @stylistic/max-len
import { ProjectUserAssignmentRoles, DEFAULT_SELECT_ROLE_OPTION } from '../projects/project-user-assignment/project-user-assignment-roles';
import { useRoleAccessToggle } from '../../../hooks/role-access-toggle';
import { RoleBasedFeature } from '../../../state';

type Props = {
  isOpen: boolean,
  onClose: () => void,
  onSubmit: (roleId: SelectProps.Option) => void,
  isLoading: boolean,
  'data-test'?: string, // eslint-disable-line @typescript-eslint/naming-convention
};


export const ApproveModal: FC<Props> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
  'data-test': dataTest,
}) => {
  const isFeatureAccessible = useRoleAccessToggle();
  const [optionRole, setRoleoption] = useState<SelectProps.Option>(DEFAULT_SELECT_ROLE_OPTION);

  const closeModal = () => {
    onClose();
    setRoleoption(DEFAULT_SELECT_ROLE_OPTION);
  };

  return (
    <Modal
      size='medium'
      visible={isOpen}
      onDismiss={closeModal}
      header={i18n.approveModalHeader}
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xxl">
            <Button variant="link" onClick={closeModal}>{i18n.approveModalButtonBack}</Button>
            <Button
              variant="primary"
              data-test="approve-modal-submit"
              onClick={() => {
                onSubmit(optionRole);
                setRoleoption(DEFAULT_SELECT_ROLE_OPTION);
              }}
              loading={isLoading}
            >
              {i18n.approveModalButtonSubmit}
            </Button>
          </SpaceBetween>
        </Box>
      }
      data-test={dataTest}
    >
      <p>{i18n.approveModalDescriptionTop}</p>
      <ProjectUserAssignmentRoles
        setMemberRoleLevel={setRoleoption}
        memberRoleLevel={optionRole}
        restrictOptions={!isFeatureAccessible(RoleBasedFeature.ManageRoleFrontendAdmin)}
      />
    </Modal>
  );
};