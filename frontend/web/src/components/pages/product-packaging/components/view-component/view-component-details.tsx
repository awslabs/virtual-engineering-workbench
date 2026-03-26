import { Box, ColumnLayout, Container, Header, SpaceBetween, Spinner } from '@cloudscape-design/components';
import { Component, ComponentMetadata } from '../../../../../services/API/proserve-wb-packaging-api';
import { ValueWithLabel } from '../../../shared/value-with-label';
import { CollapsibleText, CopyText, UserDate } from '../../../shared';
import { i18n } from './view-component.translations';
import { PACKAGING_OS_TRANSLATIONS } from '../../shared';
import { useProjectsSwitch } from '../../../../../hooks';
import { useMemo } from 'react';
import { ComponentStatus } from '../components-status';
export const ViewComponentDetails = ({
  component,
  componentMetadata,
  componentLoading
}: {
  component?: Component, componentMetadata?: ComponentMetadata,
  componentLoading: boolean,
}) => {

  if (componentLoading) { return <Spinner />; }
  if (!component) { return <></>; }
  const { projects } = useProjectsSwitch({ skipFetch: true });

  const userFriendlyProjects = useMemo(() =>
    componentMetadata?.associatedProjects.map(assctPrjc => {
      const prjct = projects.find(prjct => prjct.id === assctPrjc.projectId);
      return prjct?.name || `${assctPrjc.projectId} (unkown project Id)`;
    }) ?? []
  , [componentMetadata?.associatedProjects, projects]);
  return (
    <Container header={<Header>{i18n.detailsHeader}</Header>} data-test="component-details">
      <ColumnLayout columns={3} variant="text-grid">
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsComponentId} data-test="component-id">
            <CopyText
              copyText={component.componentId}
              copyButtonLabel={i18n.copy}
              successText={i18n.copySuccess}
              errorText={i18n.copyError} />
          </ValueWithLabel>
          <ValueWithLabel label={i18n.detailsStatus} data-test="status">
            {<ComponentStatus status={component.status} />}
          </ValueWithLabel>
          <ValueWithLabel label={i18n.detailsPrograms} data-test="programs">
            <CollapsibleText
              items={userFriendlyProjects}
              size="xxxs"
              direction="vertical"
              minLength={2}
            />
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsPlatform} data-test="platform">
            {component.componentPlatform}
          </ValueWithLabel>
          <ValueWithLabel label={i18n.detailsSupportedArchitectures} data-test="supported-architectures">
            <SpaceBetween size="xxxs">
              {component.
                componentSupportedArchitectures.
                map(x => <Box key={x}>{x}</Box>)
              }
            </SpaceBetween>
          </ValueWithLabel>
          <ValueWithLabel label={i18n.detailsSupportedOS} data-test="supported-os">
            <SpaceBetween size="xxxs">
              {component.
                componentSupportedOsVersions.
                map(x => <Box key={x}>{PACKAGING_OS_TRANSLATIONS[x] || x}</Box>)
              }
            </SpaceBetween>
          </ValueWithLabel>
        </SpaceBetween>
        <SpaceBetween size="l">
          <ValueWithLabel label={i18n.detailsAuthor} data-test="author">
            {component.createdBy}
          </ValueWithLabel>
          <ValueWithLabel label={i18n.detailsCreateDate} data-test="create-date">
            <UserDate date={component.createDate} />
          </ValueWithLabel>
        </SpaceBetween>
      </ColumnLayout>
    </Container>
  );
};