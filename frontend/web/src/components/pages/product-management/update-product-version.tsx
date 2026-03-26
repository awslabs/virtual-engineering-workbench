import {
  Box,
  Header,
  HelpPanel,
  Spinner,
  SpaceBetween,
} from '@cloudscape-design/components';
import { useParams } from 'react-router-dom';
import { useState } from 'react';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './update-product-version.translations';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../state';
import { useUpdateProductVersion } from './update-product-version.logic';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { ProductVersionWizard } from './shared/product-version-wizard';

const EMPTY_ARRAY_LENGTH = 0;

export const UpdateProductVersion = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  if (selectedProject.projectId === undefined) {
    return <div>No program selected</div>;
  }
  const { productId, versionId } = useParams();

  const { getPathFor, navigateTo } = useNavigationPaths();
  const productPath = getPathFor(RouteNames.Product, { ':id': productId });
  const [activeStepIndex, setActiveStepIndex] = useState(EMPTY_ARRAY_LENGTH);

  const {
    productVersion,
    isProductVersionLoading,
    productVersionUpdateInProgress,
    updateProductVersion,
  } = useUpdateProductVersion({
    projectId: selectedProject.projectId,
    productId: productId!,
    versionId: versionId!
  });

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Products) },
          { path: i18n.breadcrumbLevel2, href: productPath },
          { path: i18n.breadcrumbLevel3, href: '#' },
        ]}
        content={renderContent()}
        customHeader={renderHeader()}
        tools={renderTools()}
      />
    </>
  );

  function renderHeader() {
    return <Header
      variant='awsui-h1-sticky'
    >{i18n.infoHeader}</Header>;
  }

  function renderContent() {
    if (!productVersion || isProductVersionLoading) {
      return <Spinner/>;
    }
    return <>
      <ProductVersionWizard
        projectId={selectedProject.projectId || ''}
        productId={productId!}
        wizardCancelAction={() =>
          navigateTo(RouteNames.Product, {
            ':id': productId!,
          })
        }
        wizardSubmitAction={updateProductVersion}
        wizardSubmitInProgress={productVersionUpdateInProgress}
        productVersion={productVersion}
        activeStepIndex={activeStepIndex}
        setActiveStepIndex={setActiveStepIndex}
      />
    </>;
  }

  function renderTools() {
    return (
      <HelpPanel header={<h2>{i18n.infoPanelHeader}</h2>}>
        <SpaceBetween size={'s'}>
          <Box variant="awsui-key-label">{i18n.infoPanelLabel1}</Box>
          <Box variant="p">{i18n.infoPanelMessage1}</Box>
          <Box variant="p">{i18n.infoPanelMessage2}</Box>
          <Box>
            <p>{i18n.infoPanelHeader}</p>
            <ul>
              <li>{i18n.infoPanelLabel1}</li>
              <li>{i18n.infoPanelMessage1}</li>
              <li>{i18n.infoPanelMessage2}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};
