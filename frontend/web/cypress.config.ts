/* eslint-disable @typescript-eslint/no-magic-numbers */
import { defineConfig } from 'cypress';
import vitePreprocessor from 'cypress-vite'

export default defineConfig({
  projectId: 'proserve-wb-web-app-frontend',
  viewportHeight: 1080,
  viewportWidth: 1920,
  waitForAnimations: true,
  retries: {
    runMode: 5,
    openMode: 1,
  },
  e2e: {
    baseUrl: 'http://localhost:3000',
    specPattern: 'cypress/e2e/**/*.cy.ts',
    testIsolation: true,
    experimentalRunAllSpecs: true,
    setupNodeEvents(on, config) {
      on('file:preprocessor', vitePreprocessor())
    },
  },
  video: false,
  screenshotOnRunFailure: true,
});