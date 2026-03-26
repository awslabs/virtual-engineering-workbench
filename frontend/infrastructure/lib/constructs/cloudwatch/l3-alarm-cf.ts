import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import {
  aws_sns as sns,
  aws_cloudwatch as cloudwatch,
  aws_cloudwatch_actions as actions
} from 'aws-cdk-lib';

export interface CfAlarmProps {
  alarmName: string,
  alarmActions?: string[],
  alarmDescription?: string,
  metrics?: cloudwatch.CfnAlarm.MetricDataQueryProperty[],
}

export class CfAlarm extends Construct {
  constructor(scope: Construct, id: string, props: CfAlarmProps) {
    super(scope, id);

    new cloudwatch.CfnAlarm(this, 'Alarm', {
      alarmName: props.alarmName,
      alarmActions: props.alarmActions,
      alarmDescription: props.alarmDescription,
      metrics: props.metrics,
      comparisonOperator: 'GreaterThanUpperThreshold',
      datapointsToAlarm: 1,
      evaluationPeriods: 1,
      actionsEnabled: true,
      thresholdMetricId: 'ad1',
      treatMissingData: 'notBreaching',
    });
  }
}
