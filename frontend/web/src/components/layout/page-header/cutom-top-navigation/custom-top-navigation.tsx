import {
  Button,
  ButtonDropdown,
  ButtonDropdownProps,
  Icon,
  TopNavigationProps,
} from '@cloudscape-design/components';
import { v4 as uuid } from 'uuid';
import styles from './custom-page-header.module.scss';
import { useNavigationPaths } from '../../navigation/navigation-paths.logic';
import { RouteNames } from '../../navigation/navigation.static';

interface InternalCustomUtility {
  type: 'custom',
  container: JSX.Element,
  onClick?: () => void,
  dataTest?: string,
}
export type CustomUtility =
  | TopNavigationProps.MenuDropdownUtility & {
    dataTest?: string,
  }
  | TopNavigationProps.ButtonUtility & {
    dataTest?: string,
  }
  | InternalCustomUtility;

export interface CustomTopNavigationProps {
  utilities: CustomUtility[],
  identity: Omit<TopNavigationProps.Identity, 'href'> & {
    hrefRoute: RouteNames,
  },
  envrionmenName: string,
}
/* eslint complexity: "off", @typescript-eslint/no-magic-numbers: "off" */
export default function CustomTopNavigation({
  utilities,
  ...restProps
}: CustomTopNavigationProps): JSX.Element {
  const { navigateTo } = useNavigationPaths();

  function renderUtilities(utilities: CustomUtility[]) {
    return (
      <ul className={styles.utilitiesList} data-test="custom-header-utilities">
        {utilities.map((utility) => {
          let button = null;
          if (utility.type === 'menu-dropdown') {
            let items: ButtonDropdownProps.Items = [];
            if (utility.description) {
              items = [{ text: utility.description, items: utility.items }];
            } else {
              items = utility.items;
            }
            button =
              <span className={styles.dropDownButton}>
                <ButtonDropdown
                  onItemClick={utility.onItemClick}
                  items={items}
                  data-custom-button
                  data-test={utility.dataTest || uuid()}
                >
                  {utility.iconName ?
                    <span className={styles.utilitiesListItemIconContainer}>
                      <Icon name={utility.iconName} />
                    </span>
                    : null}
                  <span>{utility.text}</span>
                </ButtonDropdown>
              </span>
            ;
          }
          if (utility.type === 'button') {
            button =
              <Button
                variant="inline-link"
                onClick={utility.onClick}
                data-custom-button
                data-test={utility.dataTest || uuid()}
              >
                <span className={styles.utilitiesListItemIconContainer}>
                  <Icon name={utility.iconName} />
                </span>
                <span className={styles.utilitiesListItemText}>
                  {utility.text}
                </span>
              </Button>
            ;
          }
          if (utility.type === 'custom') {
            button =
              <Button
                variant="inline-link"
                data-custom-button
                onClick={utility.onClick}
                data-test={utility.dataTest || uuid()}
              >
                {utility.container}
              </Button>
            ;
          }
          return (
            <li
              className={styles.utilitiesListItem}
              key={uuid()}
              data-test="custom-header-utilities-item"
            >
              <span>{button}</span>
            </li>
          );
        })}
      </ul>
    );
  }

  return (
    <div className={`${styles.customHeader} awsui-context-top-navigation`}>
      <div className={styles.logoContainer}>
        <div id="logo" data-test="custom-header-logo">
          <img
            className={styles.logoImg}
            onClick={() => navigateTo(restProps.identity.hrefRoute)}
            src={restProps.identity.logo?.src}
            alt={restProps.identity.logo?.alt}
          />
        </div>
        {restProps.envrionmenName !== 'prod' ?
          <span className={styles.environmentLabel}>
            {restProps.envrionmenName}
          </span>
          : null}
      </div>
      <div
        className={styles.utilities}
        data-test="custom-header-utilities-container"
      >
        {renderUtilities(utilities)}
      </div>
    </div>
  );
}
