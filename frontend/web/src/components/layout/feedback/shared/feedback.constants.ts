/* eslint @stylistic/max-len: off */

import { CollectorConfig } from '.';

export const TEST_COLLECTOR: CollectorConfig = {
  collectorUrl: '',
  collectorId: '6aa1fa69',
};

export const PROD_COLLECTOR: CollectorConfig = {
  collectorUrl: '',
  collectorId: 'f9b7c36c',
};

export function getCollectorFor(environment: string): CollectorConfig {
  if (environment.trim().toLowerCase() === 'prod') {
    return PROD_COLLECTOR;
  }
  return TEST_COLLECTOR;
}