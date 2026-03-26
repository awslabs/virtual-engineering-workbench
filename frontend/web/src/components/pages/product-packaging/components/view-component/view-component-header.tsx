import { Button, Header, SpaceBetween } from '@cloudscape-design/components';
import { RouteNames } from '../../../../layout/navigation/navigation.static';
import { i18n } from './view-component.translations';
import { Component } from '../../../../../services/API/proserve-wb-packaging-api';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';

export const ViewComponentHeader = ({
  component,
  setArchivePromptVisible,
  setSharePromptVisible,
}: {
  component?: Component,
  setArchivePromptVisible: (value: boolean) => void,
  setSharePromptVisible: (value: boolean) => void,
}) => {

  const { navigateTo } = useNavigationPaths();
  function preventAnyAction() {
    return !component || component?.status === 'ARCHIVED';
  }

  return (
    <Header
      variant="awsui-h1-sticky"
      description={component?.componentDescription || '...'}
      actions={
        <>
          <SpaceBetween size="xs" direction="horizontal">
            <Button
              onClick={() => history.back()}
              variant="normal"
              data-test="back-btn"
              disabled={!component}
            >
              {i18n.returnButtonText}
            </Button>
            <Button
              onClick={() => setArchivePromptVisible(true)}
              variant="normal"
              data-test="archive-component-btn"
              disabled={preventAnyAction()}
            >
              {i18n.archiveButtonText}
            </Button>
            <Button
              onClick={() => setSharePromptVisible(true)}
              variant="normal"
              data-test="share-component-btn"
              disabled={preventAnyAction()}
            >
              {i18n.shareButtonText}
            </Button>
            <Button
              onClick={() => {
                navigateTo(RouteNames.UpdateComponent, {
                  ':componentId': component?.componentId,
                });
              }}
              variant="normal"
              data-test="edit-component-btn"
              disabled={preventAnyAction()}
            >
              {i18n.editButtonText}
            </Button>
            <Button
              onClick={() => {
                navigateTo(RouteNames.CreateComponentVersion, {
                  ':componentId': component?.componentId,
                }, {
                  componentName: component?.componentName,
                  componentPlatform: component?.componentPlatform,
                }
                );
              }}
              variant="primary"
              data-test="create-component-version-btn"
              disabled={preventAnyAction()}
            >
              {i18n.createButtonText}
            </Button>
          </SpaceBetween>
        </>
      }
    >
      {component?.componentName || '...'}
    </Header>
  );
};
