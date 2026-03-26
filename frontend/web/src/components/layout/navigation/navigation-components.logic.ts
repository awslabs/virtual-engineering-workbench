import React from 'react';
import { ROUTES } from './navigation-component-map';
import { RouteNames } from './navigation.static';

const useNavigationComponents = () => {

  return {
    getComponentFor,
  };

  function getComponentFor(route: RouteNames): React.ReactNode {
    return ROUTES[route].component;
  }
};

export { useNavigationComponents };