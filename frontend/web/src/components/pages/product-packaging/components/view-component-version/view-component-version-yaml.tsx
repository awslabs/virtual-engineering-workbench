import { Container, FormField, Header, Spinner } from '@cloudscape-design/components';
import { ComponentVersion } from '../../../../../services/API/proserve-wb-packaging-api';
import { i18n } from './view-component-version.translations';
import { YamlCodeEditor } from '../../../shared';

export const ViewComponentVersionYaml = ({
  componentVersion,
  componentVersionLoading,
  yamlDefinition
}: { componentVersion?: ComponentVersion, componentVersionLoading: boolean, yamlDefinition: string }) => {

  if (componentVersionLoading) { return <Spinner />; }
  if (!componentVersion) { return <></>; }

  return (
    <Container header={<Header>{i18n.yamlHeader}</Header>} data-test="yaml-config">
      <FormField stretch>
        <YamlCodeEditor
          yamlDefinition={yamlDefinition}
          setYamlDefinition={e=> e}
          setYamlDefinitionValid={e=>e}
          disabled={true}
        />
      </FormField>
    </Container>
  );
};
