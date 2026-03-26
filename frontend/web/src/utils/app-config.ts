function getEnvironmentName(): string {
  if (!import.meta.env.REACT_APP_ENVIRONMENT) {
    throw new Error('REACT_APP_ENVIRONMENT environment variable is not set.');
  }
  return import.meta.env.REACT_APP_ENVIRONMENT;
}

const appConfig = {
  Environment: getEnvironmentName()
};

export { appConfig as AppConfig };
