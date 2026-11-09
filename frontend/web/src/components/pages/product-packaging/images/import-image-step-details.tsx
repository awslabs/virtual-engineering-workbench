import { Container, FormField, Header, Input, SpaceBetween, Textarea } from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './import-image-wizard.translations';

interface Props {
  imageName: string,
  setImageName: (value: string) => void,
  imageDescription: string,
  setImageDescription: (value: string) => void,
}

export const ImportImageStepDetails: FC<Props> = ({
  imageName, setImageName, imageDescription, setImageDescription,
}) =>
  <Container header={<Header variant="h2">{i18n.step3Header}</Header>}>
    <SpaceBetween size="m">
      <FormField label={i18n.imageNameLabel} constraintText={i18n.imageNameConstraint}>
        <Input data-test="image-name-input" value={imageName}
          onChange={({ detail }) => setImageName(detail.value)} />
      </FormField>
      <FormField label={i18n.imageDescriptionLabel} constraintText={i18n.imageDescriptionConstraint}>
        <Textarea value={imageDescription}
          onChange={({ detail }) => setImageDescription(detail.value)} />
      </FormField>
    </SpaceBetween>
  </Container>
;
