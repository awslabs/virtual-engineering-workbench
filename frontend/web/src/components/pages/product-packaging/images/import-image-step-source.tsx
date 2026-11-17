import { Container, Header, Tiles } from '@cloudscape-design/components';
import { FC } from 'react';
import { ImageSource } from './import-image-wizard.logic';
import { i18n } from './import-image-wizard.translations';

interface Props {
  imageSource: ImageSource,
  setImageSource: (value: ImageSource) => void,
}

export const ImportImageStepSource: FC<Props> = ({ imageSource, setImageSource }) =>
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
      ]}
    />
  </Container>
;
