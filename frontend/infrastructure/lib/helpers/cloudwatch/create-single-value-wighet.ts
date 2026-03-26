// // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// // SPDX-License-Identifier: MIT-0

import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import { Construct } from 'constructs';

export function createCustomCloudWatchMetric(
  scope: Construct,
  metricName: string,
  dimensionsMap: Record<string, string>,
  statistic: cloudwatch.Statistic,
  unit: cloudwatch.Unit,
  period: cdk.Duration
): cloudwatch.Metric {
  return new cloudwatch.Metric({
    namespace: 'YourNamespace', // Replace with your desired namespace
    metricName,
    dimensionsMap,
    statistic,
    unit,
    period,
  }).attachTo(scope);
}
