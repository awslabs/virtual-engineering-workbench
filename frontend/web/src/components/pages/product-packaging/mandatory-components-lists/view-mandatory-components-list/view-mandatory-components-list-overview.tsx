import {
  ColumnLayout,
  Container,
  Header,
  SpaceBetween,
  Spinner,
} from '@cloudscape-design/components';
import { MandatoryComponentsList } from '../../../../../services/API/proserve-wb-packaging-api';
import { ValueWithLabel } from '../../../shared/value-with-label';
import { i18n } from './view-mandatory-components-list.translations';

export const ViewMandatoryComponentsListOverview = ({
  mandatoryComponentsList,
  mandatoryComponentsListLoading,
}: {
  mandatoryComponentsList?: MandatoryComponentsList,
  mandatoryComponentsListLoading: boolean,
}) => {
  if (mandatoryComponentsListLoading) {
    return <Spinner />;
  }
  if (!mandatoryComponentsList) {
    return <></>;
  }

  return (
    <Container
      header={<Header>{i18n.detailsHeader}</Header>}
      data-test="mandatory-components-list-details"
    >
      <ColumnLayout columns={3} variant="text-grid">
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsPlatform} data-test="platform">
            {mandatoryComponentsList.mandatoryComponentsListPlatform}
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel
            label={i18n.detailsArchitecture}
            data-test="architecture"
          >
            {mandatoryComponentsList.mandatoryComponentsListArchitecture}
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsOsVersion} data-test="os-version">
            {mandatoryComponentsList.mandatoryComponentsListOsVersion}
          </ValueWithLabel>
        </SpaceBetween>
      </ColumnLayout>
    </Container>
  );
};
