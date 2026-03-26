import { lambdaHandler, handler } from './app-elb.alb-target';
const { mockClient } = require('aws-sdk-client-mock');
import { S3Client, GetObjectCommand } from '@aws-sdk/client-s3';
import { APIGatewayProxyEvent, CloudFrontRequestEvent } from 'aws-lambda';
import { Readable } from 'stream';
import { sdkStreamMixin } from '@smithy/util-stream';
import { AsyncHandler } from '../helpers/async-handler';

/* eslint @typescript-eslint/naming-convention: "off" */
/* eslint @typescript-eslint/no-require-imports: "off" */
/* eslint @typescript-eslint/no-explicit-any: "off" */
const s3Mock = mockClient(S3Client);


jest.mock('../helpers/async-handler', () => {
  const originalModule = jest.requireActual('../helpers/async-handler');
  return {
    __esModule: true,
    ...originalModule,
    AsyncHandler: {
      handleAsync: jest.fn()
    },
  };
});

const sampleRequest: APIGatewayProxyEvent = {
  body: null,
  headers: {},
  multiValueHeaders: {},
  httpMethod: 'GET',
  isBase64Encoded: false,
  path: '/',
  pathParameters: {},
  queryStringParameters: {},
  multiValueQueryStringParameters: {},
  stageVariables: {},
  requestContext: { ...{} as any },
  resource: ''
};
const ctx = {
  ...{} as any
};

describe('ALB Lambda Target', () => {

  const APP_BUCKET_NAME = 'test-bucket';

  beforeEach(() => {
    const stream = new Readable();
    stream.push('hello world');
    stream.push(null); // end of stream
    const sdkStream = sdkStreamMixin(stream);

    s3Mock.reset().on(GetObjectCommand, {
      Bucket: APP_BUCKET_NAME,
      Key: 'index.html',
    }).resolves({
      Body: sdkStream,
      ContentType: 'text/html'
    }).on(GetObjectCommand, {
      Bucket: APP_BUCKET_NAME,
      Key: 'bla',
    }).rejects('Test');

  });

  it('returns index.html for a root path', async () => {
    // ARRANGE

    // ACT
    const response = await lambdaHandler(sampleRequest, ctx);

    // ASSERT
    expect(response.statusCode).toBe(200);
    expect(response.body).toBe(Buffer.from('hello world').toString('base64'));
    expect(response.isBase64Encoded).toBe(true);

  });

  it('tries to fetch index.html if file is not found in S3', async () => {
    // ARRANGE
    const request: APIGatewayProxyEvent = {
      ...sampleRequest,
      path: 'bla'
    };

    // ACT
    const response = await lambdaHandler(request, ctx);

    // ASSERT
    expect(response.statusCode).toBe(200);
    expect(response.body).toBe(Buffer.from('hello world').toString('base64'));
    expect(response.isBase64Encoded).toBe(true);
  });

  it('returns 404 if index.html is not found after retry', async () => {
    // ARRANGE
    const request: APIGatewayProxyEvent = {
      ...sampleRequest,
      path: 'bla'
    };
    s3Mock.reset().on(GetObjectCommand, {
      Bucket: APP_BUCKET_NAME,
      Key: 'index.html',
    }).rejects('Test').on(GetObjectCommand, {
      Bucket: APP_BUCKET_NAME,
      Key: 'bla',
    }).rejects('Test');

    // ACT
    const response = await lambdaHandler(request, ctx);

    // ASSERT
    expect(response.statusCode).toBe(404);
  });

  it('does not retry if index.html is requested', async () => {
    // ARRANGE

    // ACT
    const response = await lambdaHandler(sampleRequest, ctx);

    // ASSERT
    expect(s3Mock.calls()).toHaveLength(1);
  });

  it('sets content type', async () => {
    // ARRANGE
    const request: APIGatewayProxyEvent = {
      ...sampleRequest,
    };

    // ACT
    const response = await lambdaHandler(request, ctx);

    // ASSERT
    expect(response.multiValueHeaders?.['Content-Type'][0]).toBe('text/html');
  });
});

describe('ALB Lambda Target Cognito Middleware', () => {
  const APP_BUCKET_NAME = 'test-bucket';

  beforeEach(() => {
    const stream = new Readable();
    stream.push('hello world');
    stream.push(null); // end of stream
    const sdkStream = sdkStreamMixin(stream);

    s3Mock.reset().on(GetObjectCommand, {
      Bucket: APP_BUCKET_NAME,
      Key: 'index.html',
    }).resolves({
      Body: sdkStream,
      ContentType: 'text/html'
    });
  });

  it('redirects when user is unauthenticated', async () => {
    // ARRANGE
    const asyncHandlerMock = AsyncHandler.handleAsync as jest.MockedFunction<typeof AsyncHandler.handleAsync>;

    asyncHandlerMock.mockImplementation((fcEvt: CloudFrontRequestEvent) => {
      return Promise.resolve({
        status: '302',
        headers: {
          location: [{
            key: 'location',
            value: '/test'
          }]
        }
      });
    });

    // ACT
    const response = await handler(sampleRequest, ctx);

    // ASSERT
    expect(response.statusCode).toBe(302);
    expect(response.multiValueHeaders?.location[0]).toBe('/test');

  });

  it('forwards when user is authenticated', async () => {
    // ARRANGE
    const asyncHandlerMock = AsyncHandler.handleAsync as jest.MockedFunction<typeof AsyncHandler.handleAsync>;

    asyncHandlerMock.mockImplementation((fcEvt: CloudFrontRequestEvent) => {
      return Promise.resolve(fcEvt.Records[0].cf.request);
    });

    // ACT
    const response = await handler(sampleRequest, ctx);

    // ASSERT
    expect(response.statusCode).toBe(200);
  });
});