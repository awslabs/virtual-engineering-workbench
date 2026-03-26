const esModules = ["@middy", "aws-sdk-client-mock"].join("|");

module.exports = {
  preset: 'ts-jest',
  roots: ['<rootDir>/test','<rootDir>/lib'],
  setupFiles: ['<rootDir>/.jest/setEnvVars.js'],
  testMatch: ['**/*.test.ts'],
  transform: {
    '^.+\\.ts?$': ['ts-jest', {
        useESM: true
      }]
  },
  moduleNameMapper: {
    "^axios$": require.resolve('axios'),
    "^aws-sdk-client-mock$": require.resolve('aws-sdk-client-mock'),
  },
  transformIgnorePatterns: [`node_modules/(?!${esModules})`],
};