import { Logger } from '@aws-lambda-powertools/logger';
import {
  CloudWatchLogsClient,
  DescribeLogGroupsCommand,
  CreateLogGroupCommand,
  PutSubscriptionFilterCommand,
  DeleteSubscriptionFilterCommand,
  DescribeSubscriptionFiltersCommand,
  DescribeLogGroupsCommandOutput
} from '@aws-sdk/client-cloudwatch-logs';

import {
  EC2Client,
  DescribeRegionsCommand,
} from '@aws-sdk/client-ec2';

import {
  LambdaClient,
  AddPermissionCommand,
  GetPolicyCommand,
  GetPolicyCommandOutput,
} from '@aws-sdk/client-lambda';

/* eslint @typescript-eslint/naming-convention: "off" */

const logger = new Logger();
const ec2Client = new EC2Client();
const lambdaClient = new LambdaClient();

interface LogGroupSubscriptionFilterProps {
  LogGroupName: string,
  SubscriptionFilterName: string,
  SubscriptionFilterDestinationArn: string,
  SubscriptionFilterPatterns: string[],
  AccountId: string,
}

interface CustomResourceEvent {
  RequestType: string,
  ResourceProperties: LogGroupSubscriptionFilterProps,
  PhysicalResourceId?: string,
}

interface LambdaPolicyItem {
  Sid: string,
}

interface LambdaPolicy {
  Statement: LambdaPolicyItem[],
}

export async function handler(event: CustomResourceEvent) {

  logger.debug(JSON.stringify({
    receivedEventBody: event
  }));

  const requestType = event.RequestType;
  if (requestType === 'Create') {
    return upsertEdgeMonitoringInfra(event);
  }
  if (requestType === 'Update') {
    return upsertEdgeMonitoringInfra(event);
  }
  if (requestType === 'Delete') {
    return deleteEdgeMonitoringInfra(event);
  }
  throw Error(`Invalid request type: ${requestType}`);
}

async function upsertEdgeMonitoringInfra(evt: CustomResourceEvent) {
  const props = evt.ResourceProperties;

  const regions = await ec2Client.send(new DescribeRegionsCommand({}));

  const enabledRegions = (regions.Regions || []).filter(r => r.RegionName !== undefined);

  const lambdaStatementIds = await getAllLambdaResourcePolicyStatementIds(props);
  const lambdaPermissionsResponse = await Promise.allSettled(enabledRegions.map(r => putLambdaPermissions(props, r.RegionName || '', lambdaStatementIds)));

  if (lambdaPermissionsResponse.some(x => x.status === 'rejected')) {
    logger.error(JSON.stringify(lambdaPermissionsResponse.filter(x => x.status === 'rejected')));
    throw Error('Failed to put lambda permissions');
  }

  logger.debug(`Regions: ${JSON.stringify(enabledRegions.map(r => r.RegionName))}`);

  const regionConfigResponse = await Promise.allSettled(enabledRegions.map(r => configureRegion(props, r.RegionName || '')));
  if (regionConfigResponse.some(r => r.status === 'rejected')) {
    logger.error(JSON.stringify(regionConfigResponse.filter(x => x.status === 'rejected')));
    throw Error('Some regions failed configuration.');
  }

  return {
    PhysicalResourceId: props.LogGroupName,
  };

}

async function getAllLambdaResourcePolicyStatementIds(props: LogGroupSubscriptionFilterProps): Promise<Set<string>> {

  let lambdaPolicy: GetPolicyCommandOutput | null = null;

  try {
    lambdaPolicy = await lambdaClient.send(new GetPolicyCommand({
      FunctionName: props.SubscriptionFilterDestinationArn,
    }));
  } catch (e) {
    logger.warn(`Failed to get lambda policy: ${JSON.stringify(e)}`);
    return new Set<string>();
  }

  if (!lambdaPolicy.Policy) {
    return new Set<string>();
  }
  const policyObj: LambdaPolicy = JSON.parse(lambdaPolicy.Policy);

  return new Set<string>(policyObj.Statement?.map(s => s.Sid) || []);
}

async function putLambdaPermissions(props: LogGroupSubscriptionFilterProps, region: string, lambdaPolicyStatementSIDs: Set<string>) {
  const statementId = `SubscriptionFilterLambdaEdge-${region}`;
  if (lambdaPolicyStatementSIDs.has(statementId)) {
    logger.debug(`${region}: Lambda permission already exists.`);
    return;
  }

  logger.debug(`${region}: Adding lambda permissions.`);
  await lambdaClient.send(new AddPermissionCommand({
    FunctionName: props.SubscriptionFilterDestinationArn,
    Action: 'lambda:InvokeFunction',
    Principal: `logs.${region}.amazonaws.com`,
    StatementId: statementId,
    SourceArn: `arn:aws:logs:${region}:${props.AccountId}:log-group:${props.LogGroupName}:*`,
  }));
}

async function configureRegion(props: LogGroupSubscriptionFilterProps, region: string) {
  const cloudwatchClient = new CloudWatchLogsClient({ region });

  await upsertLogGroup(cloudwatchClient, props.LogGroupName);
  await upsertSubscriptions(cloudwatchClient, props.LogGroupName, props.SubscriptionFilterName, props.SubscriptionFilterDestinationArn, props.SubscriptionFilterPatterns);
}

async function upsertLogGroup(cloudwatchClient: CloudWatchLogsClient, logGroupName: string) {
  const logGroups = await cloudwatchClient.send(new DescribeLogGroupsCommand({
    logGroupNamePrefix: logGroupName,
  }));
  const regionName = await cloudwatchClient.config.region();

  raiseForInvalidLogGroups(logGroups, regionName, logGroupName);

  if (!logGroups.logGroups || logGroups.logGroups.length === 0) {
    logger.info(`${regionName}: Creating log group ${logGroupName}`);

    await cloudwatchClient.send(new CreateLogGroupCommand({
      logGroupName: logGroupName,
    }));
  }
}

function raiseForInvalidLogGroups(logGroups: DescribeLogGroupsCommandOutput, regionName: string, logGroupName: string) {
  if (logGroups.logGroups && logGroups.logGroups.length > 1) {
    logger.error(`${regionName}: More than one log group found with prefix ${logGroupName}`);
    throw Error(`${regionName}: More than one log group found with prefix ${logGroupName}`);
  }
}

async function upsertSubscriptions(
  cloudwatch_client: CloudWatchLogsClient,
  logGroupName: string,
  filterName: string,
  destinationArn: string,
  subscriptionFilterPatterns: string[],
) {
  const subscriptioFilters = await cloudwatch_client.send(new DescribeSubscriptionFiltersCommand({
    logGroupName: logGroupName,
    filterNamePrefix: filterName,
  }));

  const region_name = await cloudwatch_client.config.region();

  if (subscriptioFilters.subscriptionFilters && subscriptioFilters.subscriptionFilters.length > 0) {
    logger.debug(`${region_name}: Subscription filters already exist (log group: ${logGroupName}, filter: ${filterName})`);
    return Promise.resolve();
  }

  logger.debug(`${region_name}: Filter patterns: ${JSON.stringify(subscriptionFilterPatterns)}`);

  const responses = await Promise.allSettled(
    subscriptionFilterPatterns.map((filterPattern, i) => {
      const cmd = new PutSubscriptionFilterCommand({
        logGroupName: logGroupName,
        destinationArn,
        filterName: `${filterName}-${i}`,
        filterPattern,
      });
      logger.debug(JSON.stringify({
        message: `${region_name}: Creating subscription filter for ${logGroupName}`,
        payload: cmd,
      }));
      return cloudwatch_client.send(cmd);
    }),
  );

  if (responses.some(r => r.status === 'rejected')) {
    logger.error(JSON.stringify({
      message: `${region_name}: Failed to create subscription filter`,
      error: responses.filter(x => x.status === 'rejected'),
    }));
    throw Error('Failed to create subscription filters.');
  }

  return Promise.resolve();
}

async function deleteEdgeMonitoringInfra(evt: CustomResourceEvent) {
  const regions = await ec2Client.send(new DescribeRegionsCommand({}));

  logger.debug(`Regions: ${JSON.stringify(regions.Regions?.map(r => r.RegionName))}`);

  await Promise.allSettled((regions.Regions || []).filter(r => r.RegionName !== undefined).map(r => deleteSubscriptionFiltersInRegion(evt.ResourceProperties, r.RegionName || '')));
}

async function deleteSubscriptionFiltersInRegion(props: LogGroupSubscriptionFilterProps, region: string) {
  const cloudwatch_client = new CloudWatchLogsClient({ region });

  const subscriptioFilters = await cloudwatch_client.send(new DescribeSubscriptionFiltersCommand({
    logGroupName: props.LogGroupName,
    filterNamePrefix: props.SubscriptionFilterName,
  }));

  logger.info(`${cloudwatch_client.config.region}: Deleting filters: ${JSON.stringify(subscriptioFilters.subscriptionFilters?.map(f => f.filterName))}`);

  await Promise.allSettled((subscriptioFilters.subscriptionFilters || []).map(s => cloudwatch_client.send(new DeleteSubscriptionFilterCommand({
    logGroupName: s.logGroupName,
    filterName: s.filterName,
  }))));
}