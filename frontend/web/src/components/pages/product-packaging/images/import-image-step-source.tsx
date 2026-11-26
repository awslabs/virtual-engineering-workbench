import { Container, Header, Tiles } from '@cloudscape-design/components';
import { FC } from 'react';
import { ImageSource } from './import-image-wizard.logic';
import { i18n } from './import-image-wizard.translations';

interface Props {
  imageSource: ImageSource,
  setImageSource: (value: ImageSource) => void,
  // Offered only when the wizard was opened from an AWS-published listing:
  // without a listing there is no AMI to resolve.
  awsPublishedAvailable?: boolean,
}

export const ImportImageStepSource: FC<Props> = ({
  imageSource,
  setImageSource,
  awsPublishedAvailable,
}) =>
  <Container header={<Header variant="h2">{i18n.imageSourceHeader}</Header>}>
    <Tiles
      value={imageSource}
      onChange={({ detail }) => setImageSource(detail.value as ImageSource)}
      items={[
        {
          label: i18n.sourceExistingAmi,
          value: 'EXISTING_AMI',
          description: i18n.sourceExistingAmiDescription,
        },
        {
          label: i18n.sourceMarketplace,
          value: 'MARKETPLACE_PRODUCT',
          description: i18n.sourceMarketplaceDescription,
        },
        ...awsPublishedAvailable
          ? [{
            label: i18n.sourceAwsPublished,
            value: 'AWS_PUBLISHED_AMI',
            description: i18n.sourceAwsPublishedDescription,
          }]
          : [],
      ]}
    />
  </Container>
;
