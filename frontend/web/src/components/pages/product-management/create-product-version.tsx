import {
  Box,
  HelpPanel,
  SpaceBetween,
} from '@cloudscape-design/components';
import { useParams } from 'react-router-dom';
import { useState } from 'react';
import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import { i18n } from './create-product-version.translations';
import { useRecoilValue } from 'recoil';
import { selectedProjectState } from '../../../state';
import { useCreateProductVersion } from './create-product-version.logic';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { ProductVersionWizard } from './shared/product-version-wizard';

const EMPTY_ARRAY_LENGTH = 0;

export const CreateProductVersion = () => {
  const selectedProject = useRecoilValue(selectedProjectState);
  if (selectedProject.projectId === undefined) {
    return <div>No program selected</div>;
  }
  const { id } = useParams();

  const {
    createProductVersion,
    productVersionCreationInProgress,
  } = useCreateProductVersion({ projectId: selectedProject.projectId, productId: id! });

  const { getPathFor, navigateTo } = useNavigationPaths();
  const productPath = getPathFor(RouteNames.Product, { ':id': id });
  const [activeStepIndex, setActiveStepIndex] = useState(EMPTY_ARRAY_LENGTH);

  return (
    <>
      <WorkbenchAppLayout
        breadcrumbItems={[
          { path: i18n.breadcrumbLevel1, href: getPathFor(RouteNames.Products) },
          { path: i18n.breadcrumbLevel2, href: productPath },
          { path: i18n.breadcrumbLevel3, href: '#' },
        ]}
        content={renderContent()}
        tools={renderTools()}
      />
    </>
  );


  function renderContent() {
    return <>
      <ProductVersionWizard
        projectId={selectedProject.projectId || ''}
        productId={id!}
        wizardCancelAction={() =>
          navigateTo(RouteNames.Product, {
            ':id': id!,
          })
        }
        wizardSubmitAction={createProductVersion}
        wizardSubmitInProgress={productVersionCreationInProgress}
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
          <Box variant="p">{i18n.infoPanelMessage3}</Box>
          <Box>
            <p>{i18n.infoPanelMessage4}</p>
            <ul>
              <li>{i18n.infoPanelPoint1}</li>
              <li>{i18n.infoPanelPoint2}</li>
              <li>{i18n.infoPanelPoint3}</li>
            </ul>
          </Box>
        </SpaceBetween>
      </HelpPanel>
    );
  }
};
