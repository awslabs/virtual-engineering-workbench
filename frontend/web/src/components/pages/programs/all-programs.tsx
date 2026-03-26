import { FC, useMemo } from 'react';
import {
  Box,
  Button,
  CardsProps,
  Cards,
  Header,
  TextFilter,
  SegmentedControl,
} from '@cloudscape-design/components';
import { useCollection } from '@cloudscape-design/collection-hooks';
import { useRecoilValue } from 'recoil';
import { EmptyGridNotification, NoMatchGridNotification } from '../shared';
import {
  Project,
  filteredAvailableProjectsState,
  projectsLoadingState,
  enrolmentsState,
  RoleBasedFeature
} from '../../../state';
import { usePrograms } from './programs.logic';
import { i18n } from './programs.translations';
import { useNavigationPaths } from '../../layout/navigation/navigation-paths.logic';
import { RouteNames } from '../../layout/navigation/navigation.static';
import { RoleAccessToggle } from '../shared/role-access-toggle';

type Props = {
  selectedTab: string,
  setSelectedTab: (arg: string) => void,
};

const allPrograms: FC<Props> = ({ selectedTab, setSelectedTab }) => {
  const projects = useRecoilValue(filteredAvailableProjectsState);
  const projectsLoading = useRecoilValue(projectsLoadingState);
  const enrolmentsList = useRecoilValue(enrolmentsState);
  const { handleEnrolProgram, isLoading, disabledProjectId } = usePrograms();
  const { navigateTo } = useNavigationPaths();
  const activePrograms = projects.filter(program => {
    return program.isActive === true;
  });

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
        content: item => enrolmentsList.some(enrolment => enrolment.projectId === item.id)
          ? <span className="status-available" data-test="enrolment-status">{i18n.statusPending}</span>
          : <span className="status-available" data-test="enrolment-status">{i18n.statusAvailable}</span>
      },
      {
        id: 'actions',
        content: item => <Box float="right">
          <Button
            variant="primary"
            disabled={
              disabledProjectId === item.id ||
              enrolmentsList.some(enrolment => enrolment.projectId === item.id)
            }
            onClick={() => handleEnrolProgram(item.id)}
            loading={isLoading === item.id}
            data-test="enroll-button">
            {i18n.enrollButtonText}
          </Button>
        </Box>
      }
    ],
  }), [projects, isLoading, enrolmentsList, projectsLoading]);

  const { items, actions, collectionProps, filterProps } = useCollection(
    activePrograms,
    {
      filtering: {
        empty: <EmptyGridNotification
          title={i18n.noAllProgramsTitle}
          subTitle={i18n.noAllProgramsSubtitle}
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
      loading={!items && projectsLoading}
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

export { allPrograms as AllPrograms };