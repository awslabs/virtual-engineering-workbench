import { mockClient } from 'aws-sdk-client-mock';
import {
  CloudWatchLogsClient,
  DescribeLogGroupsCommand,
  CreateLogGroupCommand,
  PutSubscriptionFilterCommand,
  DeleteSubscriptionFilterCommand,
  DescribeSubscriptionFiltersCommand,
} from '@aws-sdk/client-cloudwatch-logs';

import {
  EC2Client,
  DescribeRegionsCommand,
} from '@aws-sdk/client-ec2';

import {
  LambdaClient,
  AddPermissionCommand,
  GetPolicyCommand,
} from '@aws-sdk/client-lambda';
import { handler } from './lambda-edge-monitoring.handler';


const cwMock = mockClient(CloudWatchLogsClient);
const ec2Mock = mockClient(EC2Client);
const lambdaMock = mockClient(LambdaClient);

describe('lambda-edge-monitoring.handler', () => {

  const customResourceCreateRequest = {
    RequestType: 'Create',
    ServiceToken: 'fake-arn',
    ResponseURL: 'fake-resp-url',
    StackId: 'fake-stack-id',
    RequestId: 'e7de5b2a-62ca-4099-bd99-c94cb79d65ff',
    LogicalResourceId: 'webappcdnlambdaatedgemonitorcr4EEF43E0',
    ResourceType: 'AWS::CloudFormation::CustomResource',
    ResourceProperties: {
      ServiceToken: 'service-token',
      SubscriptionFilterDestinationArn: 'arn:aws:lambda:us-east-1:001234567890:function:log-handler',
      AccountId: '001234567890',
      SubscriptionFilterPatterns: [
        'Unable to fetch tokens from grant code',
        'Unable to fetch tokens from refreshToken'
      ],
      SubscriptionFilterName: 'test',
      LogGroupName: '/aws/lambda/us-east-1.lambda-at-edge'
    }
  };

  const customResourceDeleteRequest = {
    RequestType: 'Delete',
    ServiceToken: 'fake-arn',
    ResponseURL: 'fake-resp-url',
    StackId: 'fake-stack-id',
    RequestId: 'e7de5b2a-62ca-4099-bd99-c94cb79d65ff',
    LogicalResourceId: 'webappcdnlambdaatedgemonitorcr4EEF43E0',
    ResourceType: 'AWS::CloudFormation::CustomResource',
    ResourceProperties: {
      ServiceToken: 'service-token',
      SubscriptionFilterDestinationArn: 'arn:aws:lambda:us-east-1:001234567890:function:log-handler',
      AccountId: '001234567890',
      SubscriptionFilterPatterns: [
        'Unable to fetch tokens from grant code',
        'Unable to fetch tokens from refreshToken'
      ],
      SubscriptionFilterName: 'test',
      LogGroupName: '/aws/lambda/us-east-1.lambda-at-edge'
    }
  };

  beforeEach(() => {
    cwMock.reset().
      on(DescribeLogGroupsCommand).resolves({}).
      on(DescribeSubscriptionFiltersCommand).resolves({});
    ec2Mock.reset().on(DescribeRegionsCommand).resolves({
      Regions: [{ RegionName: 'us-east-1' }, { RegionName: 'eu-central-1' }]
    });
    lambdaMock.reset().
      on(AddPermissionCommand).resolves({}).
      on(GetPolicyCommand).resolves({});
  });

  test('create: puts lambda permissions to receive subscription filter events from all regions', async () => {
    // ARRANGE

    // ACT
    await handler(customResourceCreateRequest);

    // ASSERT
    const calls = lambdaMock.commandCalls(AddPermissionCommand);
    expect(calls.length).toBe(2);
    expect(calls.map(c => c.args[0].input)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          FunctionName: 'arn:aws:lambda:us-east-1:001234567890:function:log-handler',
          Action: 'lambda:InvokeFunction',
          Principal: 'logs.us-east-1.amazonaws.com',
          StatementId: 'SubscriptionFilterLambdaEdge-us-east-1',
          SourceArn: 'arn:aws:logs:us-east-1:001234567890:log-group:/aws/lambda/us-east-1.lambda-at-edge:*',
        }),
        expect.objectContaining({
          FunctionName: 'arn:aws:lambda:us-east-1:001234567890:function:log-handler',
          Action: 'lambda:InvokeFunction',
          Principal: 'logs.eu-central-1.amazonaws.com',
          StatementId: 'SubscriptionFilterLambdaEdge-eu-central-1',
          SourceArn: 'arn:aws:logs:eu-central-1:001234567890:log-group:/aws/lambda/us-east-1.lambda-at-edge:*',
        })
      ])
    );

  });

  test('create: does not put permissions when it already exists', async () => {
    // ARRANGE
    lambdaMock.reset().
      on(GetPolicyCommand).resolves({
        Policy: JSON.stringify({
          Statement: [{
            Sid: 'SubscriptionFilterLambdaEdge-us-east-1',
            Effect: 'Allow',
            Action: 'lambda:InvokeFunction',
            Resource: 'arn:aws:lambda:us-east-1:001234567890:test'
          }, {
            Sid: 'SubscriptionFilterLambdaEdge-eu-central-1',
            Effect: 'Allow',
            Action: 'lambda:InvokeFunction',
            Resource: 'arn:aws:lambda:us-east-1:001234567890:test'
          }]
        })
      });

    // ACT
    await handler(customResourceCreateRequest);

    // ASSERT
    const calls = lambdaMock.commandCalls(AddPermissionCommand);
    expect(calls.length).toBe(0);

  });

  test('create: raises when cannot put lambda permissions', async () => {
    // ARRANGE
    lambdaMock.reset().on(AddPermissionCommand).rejects();

    // ACT
    await expect(handler(customResourceCreateRequest)).rejects.toThrow();

    // ASSERT
    const createLogGroupCalls = cwMock.commandCalls(CreateLogGroupCommand);
    const createSubscriptionCalls = cwMock.commandCalls(PutSubscriptionFilterCommand);
    expect(createLogGroupCalls.length).toBe(0);
    expect(createSubscriptionCalls.length).toBe(0);
  });

  test('create: creates log groups for Lambda@Edge in all regions', async () => {
    // ARRANGE

    // ACT
    await handler(customResourceCreateRequest);

    // ASSERT
    const calls = cwMock.commandCalls(CreateLogGroupCommand);
    expect(calls.length).toBe(2);
    expect(calls.map(c => c.args[0].input)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          logGroupName: '/aws/lambda/us-east-1.lambda-at-edge',
        }),
        expect.objectContaining({
          logGroupName: '/aws/lambda/us-east-1.lambda-at-edge',
        })
      ])
    );

  });

  test('create: raises when cannot create log groups', async () => {
    // ARRANGE
    cwMock.on(CreateLogGroupCommand).rejects();

    // ACT
    await expect(handler(customResourceCreateRequest)).rejects.toThrow();

    // ASSERT
    const createSubscriptionCalls = cwMock.commandCalls(PutSubscriptionFilterCommand);
    expect(createSubscriptionCalls.length).toBe(0);

  });

  test('create: creates subscription filters for Lambda@Edge in all regions', async () => {
    // ARRANGE

    // ACT
    await handler(customResourceCreateRequest);

    // ASSERT
    const calls = cwMock.commandCalls(PutSubscriptionFilterCommand);
    expect(calls.length).toBe(4);
    expect(calls.map(c => c.args[0].input)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          logGroupName: '/aws/lambda/us-east-1.lambda-at-edge',
          destinationArn: 'arn:aws:lambda:us-east-1:001234567890:function:log-handler',
          filterName: 'test-0',
          filterPattern: 'Unable to fetch tokens from grant code',
        }),
        expect.objectContaining({
          logGroupName: '/aws/lambda/us-east-1.lambda-at-edge',
          destinationArn: 'arn:aws:lambda:us-east-1:001234567890:function:log-handler',
          filterName: 'test-1',
          filterPattern: 'Unable to fetch tokens from refreshToken',
        })
      ])
    );
  });

  test('create: raises when cannot create subscription filters', async () => {
    // ARRANGE
    cwMock.on(PutSubscriptionFilterCommand).rejects();

    // ACT
    await expect(handler(customResourceCreateRequest)).rejects.toThrow();

  });

  test('delete: removes all subscription filters', async () => {
    // ARRANGE
    cwMock.on(DescribeSubscriptionFiltersCommand).resolves({
      subscriptionFilters: [
        { filterName: 'test-0', logGroupName: '/aws/lambda/us-east-1.lambda-at-edge' },
      ]
    });

    // ACT
    await handler(customResourceDeleteRequest);

    // ASSERT
    const calls = cwMock.commandCalls(DeleteSubscriptionFilterCommand);
    expect(calls.length).toBe(2);
    expect(calls.map(c => c.args[0].input)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          logGroupName: '/aws/lambda/us-east-1.lambda-at-edge',
          filterName: 'test-0',
        }),
        expect.objectContaining({
          logGroupName: '/aws/lambda/us-east-1.lambda-at-edge',
          filterName: 'test-0',
        })
      ])
    );
  });

});