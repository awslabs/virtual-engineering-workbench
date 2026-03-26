import { WorkbenchAppLayout } from '../../layout/workbench-app-layout/workbench-app-layout';
import {
  Cards,
  CardsProps,
  Header,
  Button,
  Box,
  ContentLayout,
  SpaceBetween,
  Icon,
  Link,
} from '@cloudscape-design/components';
import { useNavigate } from 'react-router-dom';
import { HelpUrls } from './constants';

interface CardItem {
  id: string,
  name: string,
  alt: string,
  description: string,
  link: string,
}

const i18n = {
  headerTitle: 'Help',
  infoDescription: 'Browse through this screen to find all the help you need.',
  returnButton: 'Return',
  incidentHeader: 'Submit incident',
  incidentDescription: 'Open an incident ticket to describe your issue and obtain targeted help.',
  needMoreHelpHeader: 'Incident management',
};

const helpPage = () => {
  const navigate = useNavigate();

  const handleButtonClick = (item: CardItem & { link?: string }) => {
    window.open(
      item.link,
      '_blank'
    );
  };

  const cardLayoutDefinitionTwoCards: CardsProps.CardsLayout[] = [
    /* eslint @typescript-eslint/no-magic-numbers: "off" */
    { cards: 1 },
    { minWidth: 600, cards: 2 },
  ];

  const cardDefinition = {
    header: (item: CardItem) =>
      <Button
        variant="inline-link"
        data-test="open-button"
        onClick={() => handleButtonClick(item)}>
        <Link fontSize='heading-m'>{item.name}</Link>
      </Button>,
    sections: [
      {
        id: 'description',
        header: 'Description',
        content: (item: CardItem) => <>{item.description}</>
      }
    ]
  };

  return (
    <WorkbenchAppLayout
      breadcrumbItems={[]}
      navigationHide
      content={
        <ContentLayout
          disableOverlap
          header={
            <Header
              description={i18n.infoDescription}
              actions={
                <Button onClick={() => navigate(-1)}>
                  {i18n.returnButton}
                </Button>
              }>
              {i18n.headerTitle}
            </Header>
          }>
          <Box variant="h2" padding={{ top: 'm' }}>
            <SpaceBetween size={'s'}>
              <Box variant='h2'>
                <SpaceBetween size={'xs'} direction='horizontal'>
                  <Icon name='envelope' size="medium"></Icon>
                  {i18n.needMoreHelpHeader}
                </SpaceBetween>
              </Box>
              <Cards data-test="cards"
                items={[
                  {
                    name: i18n.incidentHeader,
                    id: 'incident',
                    alt: '1',
                    description: i18n.incidentDescription,
                    link: HelpUrls.incidentLinkRaise,
                  },
                ]}
                cardDefinition={cardDefinition}
                cardsPerRow={cardLayoutDefinitionTwoCards}
                variant='container'
              />
            </SpaceBetween>
          </Box>
        </ContentLayout>
      }
    />
  );
};

export { helpPage as HelpPage };