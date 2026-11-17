import {
  AttributeEditor, Container, Header, Input, SpaceBetween,
} from '@cloudscape-design/components';
import { FC } from 'react';
import {
  ComponentVersionDetailInput as ComponentVersionDetail,
} from '../../../../services/API/proserve-wb-packaging-api';
import { i18n } from './import-image-wizard.translations';

interface Props {
  componentVersionDetails: ComponentVersionDetail[],
  setComponentVersionDetails: (value: ComponentVersionDetail[]) => void,
  updateComponentDetail: (index: number, field: keyof ComponentVersionDetail, value: string) => void,
}

export const ImportImageStepSoftware: FC<Props> = ({
  componentVersionDetails, setComponentVersionDetails, updateComponentDetail,
}) =>
  <Container header={<Header variant="h2" description={i18n.step5Description}>{i18n.step5Header}</Header>}>
    <SpaceBetween size="m">
      <AttributeEditor
        items={componentVersionDetails}
        onAddButtonClick={() =>
          setComponentVersionDetails([
            ...componentVersionDetails,
            { softwareVendor: '', softwareName: '', softwareVersion: '' },
          ])}
        onRemoveButtonClick={({ detail }) =>
          setComponentVersionDetails(
            componentVersionDetails.filter((_, i) => i !== detail.itemIndex),
          )}
        removeButtonText="Remove"
        addButtonText={i18n.addSoftwareButton}
        definition={[
          {
            label: i18n.softwareNameLabel,
            control: (item: ComponentVersionDetail, i: number) =>
              <Input value={item.softwareName}
                onChange={({ detail }) => updateComponentDetail(i, 'softwareName', detail.value)} />,
          },
          {
            label: i18n.softwareVendorLabel,
            control: (item: ComponentVersionDetail, i: number) =>
              <Input value={item.softwareVendor || ''}
                onChange={({ detail }) => updateComponentDetail(i, 'softwareVendor', detail.value)} />,
          },
          {
            label: i18n.softwareVersionLabel,
            control: (item: ComponentVersionDetail, i: number) =>
              <Input value={item.softwareVersion}
                onChange={({ detail }) => updateComponentDetail(i, 'softwareVersion', detail.value)} />,
          },
        ]}
      />
    </SpaceBetween>
  </Container>
;
