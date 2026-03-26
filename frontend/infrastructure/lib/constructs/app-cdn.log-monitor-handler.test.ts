import { gzipSync } from 'zlib';
import { CloudWatchLogsDecodedData } from 'aws-lambda';

/* eslint @typescript-eslint/no-explicit-any: "off" */

const mockAddMetric = jest.fn();
const mockPublishStoredMetrics = jest.fn();

// Mock the entire module
jest.mock('@aws-lambda-powertools/metrics', () => ({
  Metrics: jest.fn().mockImplementation(() => ({
    addMetric: mockAddMetric,
    publishStoredMetrics: mockPublishStoredMetrics
  })),
  MetricUnit: {
    Count: 'Count'
  }
}));

import { handler } from './app-cdn.log-monitor-handler';

describe('app-cdn.log-monitor-handler', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('produces CodegrantExchangeFailure metric', async () => {
    // ARRANGE
    process.env.POWERTOOLS_DEV = 'true';
    const payload: CloudWatchLogsDecodedData = {
      owner: '',
      logGroup: '',
      logStream: '',
      subscriptionFilters: [],
      messageType: '',
      logEvents: [{
        id: '',
        timestamp: 1,
        message: 'Unable to fetch tokens from grant code'
      }],
    };

    const zipped = gzipSync(Buffer.from(JSON.stringify(payload)));
    const base64 = zipped.toString('base64');
    const event = { awslogs: { data: base64 } };

    // ACT
    await handler(event, {
      ...{} as any
    }, () => ({}));

    // ASSERT
    expect(mockAddMetric).toHaveBeenCalledWith('CodegrantExchangeFailure', 'Count', 1);
    expect(mockPublishStoredMetrics).toHaveBeenCalled();
  });

  test('produces JWTTokenRefreshFailure metric', async () => {
    // ARRANGE
    const payload: CloudWatchLogsDecodedData = {
      owner: '',
      logGroup: '',
      logStream: '',
      subscriptionFilters: [],
      messageType: '',
      logEvents: [{
        id: '',
        timestamp: 1,
        message: 'Unable to fetch tokens from refreshToken'
      }],
    };

    const zipped = gzipSync(Buffer.from(JSON.stringify(payload)));
    const base64 = zipped.toString('base64');
    const event = { awslogs: { data: base64 } };

    // ACT
    await handler(event, {
      ...{} as any
    }, () => ({}));

    // ASSERT
    expect(mockAddMetric).toHaveBeenCalledWith('JWTTokenRefreshFailure', 'Count', 1);
    expect(mockPublishStoredMetrics).toHaveBeenCalled();
  });
});