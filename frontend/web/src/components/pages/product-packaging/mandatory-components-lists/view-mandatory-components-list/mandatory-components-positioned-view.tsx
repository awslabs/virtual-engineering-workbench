import { FC } from 'react';
import { ComponentVersionEntry } from '../../../../../services/API/proserve-wb-packaging-api';
import { ColumnLayout, Container, Header, Link, Table } from '@cloudscape-design/components';
import { useNavigationPaths } from '../../../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../../../layout/navigation/navigation.static';

interface MandatoryComponentsPositionedViewProps {
  prependedComponents: ComponentVersionEntry[],
  appendedComponents: ComponentVersionEntry[],
}

export const MandatoryComponentsPositionedView: FC<MandatoryComponentsPositionedViewProps> = ({
  prependedComponents = [],
  appendedComponents = [],
}) => {
  const { getPathFor } = useNavigationPaths();

  const columnDefinitions = [
    {
      id: 'component',
      header: 'Component',
      cell: (e: ComponentVersionEntry) =>
        <Link
          href={getPathFor(RouteNames.ViewComponent, { ':componentId': e.componentId })}
          external
        >
          {e.componentName}
        </Link>
    },
    {
      id: 'componentVersion',
      header: 'Version',
      cell: (e: ComponentVersionEntry) =>
        <Link
          href={getPathFor(RouteNames.ViewComponentVersion, {
            ':componentId': e.componentId,
            ':versionId': e.componentVersionId,
          })}
          external
        >
          {e.componentVersionName}
        </Link>
    },
  ];

  return (
    <ColumnLayout columns={2} variant="text-grid">
      <Container
        header={
          <Header variant="h2">
            Prepended Components
          </Header>
        }
      >
        <Table
          data-test="prepended-components-table"
          items={prependedComponents}
          columnDefinitions={columnDefinitions}
          variant="embedded"
          empty="No prepended components configured"
        />
      </Container>

      <Container
        header={
          <Header variant="h2">
            Appended Components
          </Header>
        }
      >
        <Table
          data-test="appended-components-table"
          items={appendedComponents}
          columnDefinitions={columnDefinitions}
          variant="embedded"
          empty="No appended components configured"
        />
      </Container>
    </ColumnLayout>
  );
};
