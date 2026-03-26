import {
  Box,
  Button,
  Header,
  SpaceBetween,
} from '@cloudscape-design/components';
import { MandatoryComponentsList } from '../../../../../services/API/proserve-wb-packaging-api';
import { i18n } from './view-mandatory-components-list.translations';
import { RoleBasedFeature } from '../../../../../state';
import { RoleAccessToggle } from '../../../shared/role-access-toggle';

export const ViewMandatoryComponentsListHeader = ({
  mandatoryComponentsList,
  viewMandatoryComponentsLists,
  updateMandatoryComponentsList,
}: {
  mandatoryComponentsList?: MandatoryComponentsList,
  viewMandatoryComponentsLists: () => void,
  updateMandatoryComponentsList: () => void,
}) => {
  function renderActions() {
    return (
      <Box float="right">
        <SpaceBetween size="s" direction="horizontal">
          <Button variant="link" onClick={viewMandatoryComponentsLists}>
            {i18n.headerActionReturn}
          </Button>
          <RoleAccessToggle feature={RoleBasedFeature.ManageMandatoryComponents}>
            <Button onClick={updateMandatoryComponentsList}>
              {i18n.headerActionUpdate}
            </Button>
          </RoleAccessToggle>
        </SpaceBetween>
      </Box>
    );
  }

  return (
    <Header variant="awsui-h1-sticky" actions={renderActions()}>
      {mandatoryComponentsList?.mandatoryComponentsListPlatform &&
      mandatoryComponentsList.mandatoryComponentsListArchitecture &&
      mandatoryComponentsList.mandatoryComponentsListOsVersion
        ? i18n.pageHeader(
          mandatoryComponentsList?.mandatoryComponentsListPlatform,
          mandatoryComponentsList?.mandatoryComponentsListArchitecture,
          mandatoryComponentsList?.mandatoryComponentsListOsVersion
        )
        : '...'}
    </Header>
  );
};
