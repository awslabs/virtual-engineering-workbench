import { FC, useMemo, useCallback } from 'react';
import {
  Box,
  Button,
  Cards,
  Header,
  TextFilter,
  SegmentedControl,
  SpaceBetween,
  CardsProps
} from '@cloudscape-design/components';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { useRecoilValue } from 'recoil';
import { EmptyGridNotification, NoMatchGridNotification } from '../shared';
import { useProjectsSwitch } from '../../../hooks';
import { useFeatureToggles } from '../../feature-toggles/feature-toggle.hook';
import {
  Project,
  filteredProjectsWithAnyRole,
  projectsLoadingState,
  RoleBasedFeature
} from '../../../state';
import { Feature } from '../../feature-toggles/feature-toggle.state';
import { i18n } from './programs.translations';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { RoleAccessToggle } from '../shared/role-access-toggle';
import { getHomePage } from '../../../routes';

type Props = {
  selectedTab: string,
  setSelectedTab: (arg: string) => void,
};

const myPrograms: FC<Props> = ({ selectedTab, setSelectedTab }) => {
  const { isFeatureEnabled } = useFeatureToggles();
  const userProjects = useRecoilValue(filteredProjectsWithAnyRole);
  const projectsLoading = useRecoilValue(projectsLoadingState);
  const { switchToProject, projects } = useProjectsSwitch({ skipFetch: true });
  const { navigateTo } = useNavigationPaths();

  const handleProgramSelect = useCallback((id: string) => {
    switchToProject(id);
    navigateTo(getHomePage());
  }, [navigateTo, switchToProject]);

  const cardDefinition: CardsProps.CardDefinition<Project> = useMemo(() => ({
    header: item => <Box fontSize="heading-m" fontWeight="bold">{item.name}</Box>,
    sections: [
      {
        id: 'description',
        header: '',
        content: item => item.description,
      },
      {
        id: 'status',
        header: 'Status',
        content: () => <span
          className="status-enrolled"
          data-test="program-status">
          {i18n.statusEnrolled}
        </span>
      },
      {
        id: 'actions',
        content: item => item.roles &&
          <Box float="right">
            <SpaceBetween size="xxl" direction="horizontal">
              {isFeatureEnabled(Feature.WithdrawFromProgram) &&
                <Button variant="link">{i18n.withdrawButtonText}</Button>
              }
              <Button
                variant="primary"
                onClick={() => handleProgramSelect(item.id)}
                data-test="access-button">
                {i18n.accessButtonText}
              </Button>
            </SpaceBetween>
          </Box>
      }
    ],
  }), [projects]);

  const { items, actions, collectionProps, filterProps } = useCollection(
    userProjects,
    {
      filtering: {
        empty: <EmptyGridNotification
          title={i18n.noProgramsTitle}
          subTitle={i18n.noProgramsSubtitle}
          actionButtonText={i18n.noProgramsButtonText}
          actionButtonOnClick={() => setSelectedTab('all-programs')}
        />,
        noMatch: <NoMatchGridNotification
          title={i18n.noProgramsFound}
          clearButtonAction={() => actions.setFiltering('')}
          clearButtonText={i18n.clearFilter}
        />
      },
      selection: {},
    }
  );

  return (
    <Cards
      {...collectionProps}
      stickyHeader
      cardDefinition={cardDefinition}
      // eslint-disable-next-line @typescript-eslint/no-magic-numbers
      cardsPerRow={[{ cards: 3 }]}
      filter={
        <TextFilter
          {...filterProps}
          filteringPlaceholder={i18n.filterPlaceholder}
          onChange={({ detail }) => actions.setFiltering(detail.filteringText)}
        />
      }
      header={renderHeader()}
      items={items}
      loading={projectsLoading}
      loadingText={i18n.loadingText}
      preferences={
        <SegmentedControl
          selectedId={selectedTab}
          onChange={({ detail }) => setSelectedTab(detail.selectedId)}
          options={[
            { text: i18n.segmentLabelAllPrograms, id: 'all-programs' },
            { text: i18n.segmentLabelMyPrograms, id: 'my-programs' }
          ]}
          data-test="programs-switch"
        />
      }
      selectionType={isFeatureEnabled(Feature.WithdrawFromProgram) ? 'multi' : undefined}
      variant="full-page"
    />
  );

  function renderHeader() {
    return <>
      <Header
        variant='h1'
        actions={
          <RoleAccessToggle feature={RoleBasedFeature.ProgramAdministration}>
            <Button onClick={() => {
              navigateTo(RouteNames.CreateProgram);
            }}
            variant='primary'
            data-test="create-program-btn"
            >
              {i18n.createProgram}
            </Button>
          </RoleAccessToggle>
        }
      >
        {i18n.header}
      </Header>
    </>;
  }

};

export { myPrograms as MyPrograms };