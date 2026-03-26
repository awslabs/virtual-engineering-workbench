import {
  CodeEditor,
} from '@cloudscape-design/components';
import { i18nForEditor } from './yaml-code-editor.translations';
import 'ace-builds/css/ace.css';
import 'ace-builds/css/theme/dawn.css';
import 'ace-builds/css/theme/twilight.css';

import { useEffect, useRef, useState } from 'react';

const EMPTY_COUNT = 0;

interface Props {
  yamlDefinition: string,
  setYamlDefinition: (x: string) => void,
  setYamlDefinitionValid: (x: boolean) => void,
  disabled?: boolean,
  cfCompatible?: boolean,
  isLoading?: boolean,
}

export const YamlCodeEditor = ({
  yamlDefinition,
  setYamlDefinition,
  setYamlDefinitionValid,
  disabled,
  cfCompatible = false,
  isLoading
}: Props) => {
  const [preferences, setPreferences] = useState({ wrapLines: false });
  const [ace, setAce] = useState<object>();
  const [aceLoading, setAceLoading] = useState(true);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!disabled || !wrapperRef.current || aceLoading) { return; }
    const textarea = wrapperRef.current.querySelector('.ace_editor') as HTMLElement | null;
    if (textarea) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const editor = (window as any).ace?.edit?.(textarea) ?? (textarea as any).env?.editor;
      if (editor) {
        editor.setReadOnly(true);
        editor.renderer.$cursorLayer.element.style.display = 'none';
      }
    }
  }, [disabled, aceLoading, ace]);


  useEffect(() => {
    async function loadAce() {
      const ace = await import('ace-builds');
      if (cfCompatible) {
        const cfYamlWorkerUrl = await import('./worker-cf-yaml.js?url');
        return { ace, yamlWorkerUrl: cfYamlWorkerUrl };
      }

      const yamlWorkerUrl = await import('ace-builds/src-noconflict/worker-yaml.js?url');
      return { ace, yamlWorkerUrl };
    }

    // make yaml editor bigger and wider

    loadAce().
      then(({ ace, yamlWorkerUrl }) => {
        ace.config.setModuleLoader(
          'ace/theme/dawn',
          () => import('ace-builds/src-noconflict/theme-dawn.js')
        );
        ace.config.setModuleLoader(
          'ace/mode/yaml',
          () => import('ace-builds/src-noconflict/mode-yaml.js')
        );
        ace.config.setModuleUrl('ace/mode/yaml_worker', yamlWorkerUrl.default);
        ace.config.setModuleLoader(
          'ace/snippets/yaml',
          () => import('ace-builds/src-noconflict/snippets/yaml.js')
        );
        ace.config.setModuleLoader(
          'ace/theme/twilight',
          () => import('ace-builds/src-noconflict/theme-twilight.js')
        );
        ace.config.setModuleLoader(
          'ace/ext/language_tools',
          () => import('ace-builds/src-noconflict/ext-language_tools.js')
        );
        ace.config.setModuleLoader(
          'ace/ext/searchbox',
          () => import('ace-builds/src-noconflict/ext-searchbox.js')
        );
        ace.config.set('useStrictCSP', true);
        setAce(ace);
      }).
      finally(() => setAceLoading(false));
  }, [disabled]);

  return <div ref={wrapperRef}><CodeEditor
    ace={ace}
    value={yamlDefinition}
    language="yaml"
    onDelayedChange={event => !disabled && setYamlDefinition(event.detail.value)}
    preferences={preferences}
    onPreferencesChange={event => setPreferences(event.detail)}
    loading={aceLoading || isLoading}
    i18nStrings={i18nForEditor}
    themes={{ light: ['dawn'], dark: ['twilight'] }}
    onValidate={({ detail }) => setYamlDefinitionValid(detail.annotations.length === EMPTY_COUNT)}
    data-test="component-version-yaml"
  /></div>;
};
