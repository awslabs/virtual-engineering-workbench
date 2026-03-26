import { useEffect } from 'react';
import $ from 'jquery';
import { CollectorConfig, i18n } from '../shared';

declare global {
  interface Window {
    ATL_JQ_PAGE_PROPS: any, // eslint-disable-line
    jQuery: any,
    $: any,
  }
}

type JiraCollectorProps = {
  setShowCollectorDialogFunc: (func: () => void) => void,
  username: string,
  email: string,
} & CollectorConfig;

export function useJiraCollector({
  collectorUrl,
  collectorId,
  setShowCollectorDialogFunc,
  username,
  email,
}: JiraCollectorProps) {

  useEffect(() => {
    initialiseCollector();
  }, []);

  function initialiseCollector() {
    if (window.ATL_JQ_PAGE_PROPS === undefined) {
      window.$ = window.jQuery = $;

      const collectorConfig: { [key: string]: any } = {};
      collectorConfig[collectorId] = {
        triggerFunction: function (showJiraCollectorDialog: () => void) {
          setShowCollectorDialogFunc(() => showJiraCollectorDialog);
        },
        fieldValues: {
          fullname: username,
          email: email,
          summary: i18n.jiraIssueSummaryTemplate(username),
        }
      };

      window.ATL_JQ_PAGE_PROPS = {
        ...window.ATL_JQ_PAGE_PROPS,
        ...collectorConfig,
      };

      const appElement = document.querySelector('body');
      if (appElement) {
        const snippet = document.createElement('script');
        snippet.type = 'text/javascript';
        snippet.src = collectorUrl;
        appElement.appendChild(snippet);
      }
    }
  }

  return {};
}