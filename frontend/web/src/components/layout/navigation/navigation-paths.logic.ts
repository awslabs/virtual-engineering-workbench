import { useNavigate } from 'react-router-dom';
import { ROUTES } from './navigation-paths-map';
import { RouteNames, USER_NAVIGATION_MAP } from './navigation.static';

const NAVIGATE_BACKWARDS = -1;

type RouteParamsDict = { [key: string]: string | undefined };
type RouteStateDict = { [key: string]: string | string[] | undefined | boolean | object };

export function useNavigationPaths() {

  const navigate = useNavigate();

  return {
    getActiveItem,
    getPathFor,
    navigateTo,
    goBack,
  };

  function getActiveItem(pathname: string) {
    const activeNavItem = USER_NAVIGATION_MAP.find(x => new RegExp(x.pathRegexMatcher, 'giu').test(pathname));
    if (activeNavItem) {
      return getPathFor(activeNavItem.routeName);
    }
    return undefined;
  }

  function getPathFor(route: RouteNames, routeParams?: RouteParamsDict): string {
    let path = ROUTES[route].path;
    if (routeParams !== undefined) {
      path = replacePathParams(path, routeParams);
    }
    return path;
  }

  function replacePathParams(path: string, routeParams: RouteParamsDict) {
    let innerPath = path;
    for (const param in routeParams) {
      if (Object.prototype.hasOwnProperty.call(routeParams, param)) {
        innerPath = innerPath.replace(param, routeParams[param] || '');
      }
    }
    return innerPath;
  }

  function navigateTo(route: RouteNames, routeParams?: RouteParamsDict, routeState?: RouteStateDict) {
    const path = getPathFor(route, routeParams);
    navigateToInternal(path, routeState);
  }

  function navigateToInternal(
    path: string,
    routeState?: RouteStateDict
  ) {
    if (routeState !== undefined) {
      navigate(path, {
        state: routeState
      });
    } else {
      navigate(path, {});
    }
  }

  function goBack() {
    navigate(NAVIGATE_BACKWARDS);
  }
}