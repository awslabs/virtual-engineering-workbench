import { Box, Button, Header, SpaceBetween } from '@cloudscape-design/components';
import { ComponentVersion } from '../../../../../services/API/proserve-wb-packaging-api';
import { i18n } from './view-component-version.translations';
import {
  COMPONENT_VERSION_STATES_FOR_FORCE_RELEASE,
  COMPONENT_VERSION_STATES_FOR_RELEASE,
  COMPONENT_VERSION_STATES_FOR_RETIRE,
  COMPONENT_VERSION_STATES_FOR_UPDATE,
  ComponentVersionState
} from '..';
import { useRoleAccessToggle } from '../../../../../hooks/role-access-toggle';
import { RoleBasedFeature } from '../../../../../state';

export const ViewComponentVersionHeader = ({
  componentVersion,
  viewComponent,
  updateComponentVersion,
  openReleaseComponentVersionModal,
  openRetireComponentVersionModal
}: {
  componentVersion?: ComponentVersion,
  viewComponent: () => void,
  updateComponentVersion: () => void,
  openReleaseComponentVersionModal: () => void,
  openRetireComponentVersionModal: () => void,
}) => {

  const isFeatureAccessible = useRoleAccessToggle();

  function preventUpdate() {
    return !componentVersion?.status ||
      !COMPONENT_VERSION_STATES_FOR_UPDATE.has(componentVersion.status as ComponentVersionState);
  }

  function preventRelease() {
    let acceptedStatuses = COMPONENT_VERSION_STATES_FOR_RELEASE;
    if (isFeatureAccessible(RoleBasedFeature.ProductPackagingForceReleaseComponent)) {
      acceptedStatuses = COMPONENT_VERSION_STATES_FOR_FORCE_RELEASE;
    }
    return !componentVersion?.status ||
      !acceptedStatuses.has(componentVersion.status as ComponentVersionState);
  }

  function preventRetire() {
    return !componentVersion?.status ||
      !COMPONENT_VERSION_STATES_FOR_RETIRE.has(componentVersion.status as ComponentVersionState);
  }

  function renderActions() {
    return <Box float='right'>
      <SpaceBetween size='s' direction='horizontal'>
        <Button
          variant="link"
          onClick={viewComponent}>
          {i18n.headerActionReturn}
        </Button>
        <Button
          onClick={openRetireComponentVersionModal}
          disabled= {preventRetire()}>
          {i18n.headerActionRetire}
        </Button>
        <Button
          onClick={updateComponentVersion}
          disabled= {preventUpdate()}>
          {i18n.headerActionUpdate}
        </Button>
        <Button
          variant='primary'
          onClick={openReleaseComponentVersionModal}
          disabled= {preventRelease()}>
          {i18n.headerActionRelease}
        </Button>
      </SpaceBetween>
    </Box>;
  }

  return <Header
    variant='awsui-h1-sticky'
    description={
      componentVersion?.componentVersionDescription
    }
    actions = {renderActions()}
  >{componentVersion?.componentVersionName || '...'}</Header>;
};