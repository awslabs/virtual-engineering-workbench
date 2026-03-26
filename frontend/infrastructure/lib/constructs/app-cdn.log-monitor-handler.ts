

import { gunzipSync } from 'zlib';
import { CloudWatchLogsEvent, CloudWatchLogsHandler, Context, CloudWatchLogsDecodedData } from 'aws-lambda';
import { MetricUnit, Metrics } from '@aws-lambda-powertools/metrics';

const metrics = new Metrics();

export const handler: CloudWatchLogsHandler = (event: CloudWatchLogsEvent) => {
  const zippedInput = Buffer.from(event.awslogs.data, 'base64');

  const result = gunzipSync(zippedInput);

  const decodedResult: CloudWatchLogsDecodedData = JSON.parse(result.toString());

  if (decodedResult.logEvents.some(x => x.message.includes('Unable to fetch tokens from grant code'))) {
    metrics.addMetric('CodegrantExchangeFailure', MetricUnit.Count, 1);
  }

  if (decodedResult.logEvents.some(x => x.message.includes('Unable to fetch tokens from refreshToken'))) {
    metrics.addMetric('JWTTokenRefreshFailure', MetricUnit.Count, 1);
  }

  metrics.publishStoredMetrics();

  return Promise.resolve();
};
