import {
  FormField,
} from '@cloudscape-design/components';
import { FC } from 'react';
import { i18n } from './component-version-wizard.translations';
import { YamlCodeEditor } from '../../../../shared';

export interface ComponentVersionWizardStep2Props {
  projectId: string,
  componentId: string,
  yamlDefinition: string,
  setYamlDefinition: (yamlDefinition: string) => void,
  isYamlDefinitionValid: boolean,
  setIsYamlDefinitionValid: (isYamlDefinitionValid: boolean) => void,
}

export const ComponentVersionWizardStep2: FC<ComponentVersionWizardStep2Props> = ({
  yamlDefinition,
  setYamlDefinition,
  isYamlDefinitionValid,
  setIsYamlDefinitionValid,
}) => {

  function getYamlDefinitionError() {
    return !isYamlDefinitionValid && yamlDefinition.trim() === ''
      ? i18n.step2InputYamlDefinitionError
      : '';
  }

  return <FormField
    errorText={getYamlDefinitionError()}
    data-test="component-version-yaml"
    stretch
  >
    <YamlCodeEditor
      yamlDefinition={yamlDefinition}
      setYamlDefinition={setYamlDefinition}
      setYamlDefinitionValid={setIsYamlDefinitionValid}
      disabled={false}
    />
  </FormField>;
};
