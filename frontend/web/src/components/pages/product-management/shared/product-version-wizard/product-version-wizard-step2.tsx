
import {
  Container,
  FormField,
  Header,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './product-version-wizard.translations';
import { YamlCodeEditor } from '../../../shared/yaml-code-editor';

export interface ProductVersionWizardStep2Props {
  yamlDefinition: string,
  setYamlDefinition: (yamlDefinition: string) => void,
  isYamlDefinitionValid: boolean,
  setIsYamlDefinitionValid: (isYamlDefinitionValid: boolean) => void,
  isYamlDefinitionLoading: boolean,
}

export const ProductVersionWizardStep2: FC<ProductVersionWizardStep2Props> = ({
  yamlDefinition,
  setYamlDefinition,
  isYamlDefinitionValid,
  setIsYamlDefinitionValid,
  isYamlDefinitionLoading
}) => {


  function getYamlDefinitionError() {
    return !isYamlDefinitionValid && yamlDefinition.trim() === ''
      ? i18n.step2InputYamlDefinitionError
      : '';
  }

  return <Container
    header={<Header variant="h2">
      {i18n.step2Header}
    </Header>}
  >
    <FormField
      errorText={getYamlDefinitionError()}
      data-test="product-version-yaml"
      stretch
    >
      <YamlCodeEditor
        yamlDefinition={yamlDefinition}
        setYamlDefinition={setYamlDefinition}
        setYamlDefinitionValid={setIsYamlDefinitionValid}
        disabled={false}
        cfCompatible
        isLoading={isYamlDefinitionLoading}
      />
    </FormField>
  </Container>;
};
