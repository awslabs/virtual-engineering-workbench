import { Header } from '@cloudscape-design/components';
import { i18n } from './create-component-version.translations';

export const CreateComponentVersionHeader = () => {

  return <Header
    variant='awsui-h1-sticky'
    description={i18n.headerDescription}
  >{i18n.header}</Header>;
};