import axios from 'axios';
import { CognitoJwtVerifier } from 'aws-jwt-verify';
/* eslint @typescript-eslint/naming-convention: "off" */
/* eslint @typescript-eslint/no-explicit-any: "off" */
jest.mock('axios');
jest.mock('aws-jwt-verify', () => ({
  CognitoJwtVerifier: {
    create: () => ({
      verify: jest.fn().mockResolvedValue({ 'cognito:username': 'T0011AA' }),
    }),
  }
}));

import { handler } from './app-cdn.auth-handler';
import { mockClient } from 'aws-sdk-client-mock';
import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';
import { CloudFrontRequestEvent, CloudFrontResultResponse } from 'aws-lambda';
jest.mock('./app-cdn.auth-handler.config.json');

const ssmMock = mockClient(SSMClient);
const mAxios = axios as jest.MockedFunction<typeof axios>;

describe('app-cdn.auth-handler', () => {

  beforeEach(() => {

    ssmMock.reset().on(GetParameterCommand, {
      Name: '/unit-test-app/user-pool-id'
    }).resolves({
      Parameter: {
        Value: 'us-east-1_000000000'
      }
    }).on(GetParameterCommand, {
      Name: '/unit-test-app/user-pool-client-id'
    }).resolves({
      Parameter: {
        Value: 'test-client-id'
      }
    }).on(GetParameterCommand, {
      Name: '/unit-test-app/user-pool-domain'
    }).resolves({
      Parameter: {
        Value: 'example.com'
      }
    });

  });

  test('navigates user to Cognito if path is /login', async () => {
    // Arrange 
    const req: CloudFrontRequestEvent = {
      Records: [{
        cf: {
          config: {
            distributionDomainName: 'dist.cloudfront.net',
            distributionId: 'DIST123',
            eventType: 'viewer-request',
            requestId: 'req-id'
          },
          request: {
            clientIp: '0.0.0.0',
            headers: {
              host: [{
                key: 'Host',
                value: 'dist.cloudfront.net',
              }]
            },
            method: 'GET',
            querystring: '',
            uri: '/login',
          },
        }
      }]
    };
    axios.request = jest.fn().mockResolvedValue({ });

    // Act
    const resp = await handler(req, {
      ...{} as any
    }, () => ({}));

    // Assert
    const cfResponse: CloudFrontResultResponse = resp as CloudFrontResultResponse;
    expect(cfResponse.status).toBe('302');
    expect(cfResponse.headers?.location[0].value || '').toBe('https://example.com/authorize?redirect_uri=https%3A%2F%2Fdist.cloudfront.net&response_type=code&client_id=test-client-id&state=%2Flogin');

  });

  test('returns request as-is if user is unauthenticated', async () => {
    // Arrange 
    const req: CloudFrontRequestEvent = {
      Records: [{
        cf: {
          config: {
            distributionDomainName: 'dist.cloudfront.net',
            distributionId: 'DIST123',
            eventType: 'viewer-request',
            requestId: 'req-id'
          },
          request: {
            clientIp: '0.0.0.0',
            headers: {
              host: [{
                key: 'Host',
                value: 'dist.cloudfront.net',
              }]
            },
            method: 'GET',
            querystring: '',
            uri: '/some/path',
          },
        }
      }]
    };
    axios.request = jest.fn().mockResolvedValue({ });

    // Act
    const resp = await handler(req, {
      ...{} as any
    }, () => ({}));

    // Assert
    const cfResponse: CloudFrontResultResponse = resp as CloudFrontResultResponse;
    expect(cfResponse.status).toBe('302');
  });

  test('navigates user to to initial path if auth is successfull', async () => {
    // Arrange 
    const req: CloudFrontRequestEvent = {
      Records: [{
        cf: {
          config: {
            distributionDomainName: 'dist.cloudfront.net',
            distributionId: 'DIST123',
            eventType: 'viewer-request',
            requestId: 'req-id'
          },
          request: {
            clientIp: '0.0.0.0',
            headers: {
              host: [{
                key: 'Host',
                value: 'dist.cloudfront.net',
              }]
            },
            method: 'GET',
            querystring: 'code=54fe5f4e&state=/lol',
            uri: '/some/path',
          },
        }
      }]
    };
    // mAxios.request = jest.fn().mockRejectedValue({});
    mAxios.request = jest.fn().mockResolvedValue({
      data: {
        access_token: 'eyJz9sdfsdfsdfsd',
        refresh_token: 'dn43ud8uj32nk2je',
        id_token: 'dmcxd329ujdmkemkd349r',
        token_type: 'Bearer',
        expires_in: 3600,
      }
    });

    // Act
    const resp = await handler(req, {
      ...{} as any
    }, () => ({}));

    // Assert
    const cfResponse: CloudFrontResultResponse = resp as CloudFrontResultResponse;
    expect(cfResponse.status).toBe('302');
    expect(cfResponse.headers?.location[0].value || '').toBe('https://dist.cloudfront.net/lol');

  });

  test('returns website content if user is authenticated', async () => {
    // Arrange 
    const req: CloudFrontRequestEvent = {
      Records: [{
        cf: {
          config: {
            distributionDomainName: 'dist.cloudfront.net',
            distributionId: 'DIST123',
            eventType: 'viewer-request',
            requestId: 'req-id'
          },
          request: {
            clientIp: '0.0.0.0',
            headers: {
              host: [{
                key: 'Host',
                value: 'dist.cloudfront.net',
              }],
              cookie: [
                {
                  key: 'cookie',
                  value: 'CognitoIdentityServiceProvider.test-client-id.toto.idToken=abc;'
                }
              ]
            },
            method: 'GET',
            querystring: '',
            uri: '/some/path',
          },
        }
      }]
    };

    // Act
    const resp = await handler(req, {
      ...{} as any
    }, () => ({}));

    // Assert
    expect(resp).toBe(req.Records[0].cf.request);
  });

  test('throws if there is an unhandled exception', async () => {
    // Arrange 
    const req: CloudFrontRequestEvent = {
      Records: [{
        cf: {
          config: {
            distributionDomainName: 'dist.cloudfront.net',
            distributionId: 'DIST123',
            eventType: 'viewer-request',
            requestId: 'req-id'
          },
          request: {
            clientIp: '0.0.0.0',
            headers: {
              host: [{
                key: 'Host',
                value: 'dist.cloudfront.net',
              }]
            },
            method: 'GET',
            querystring: 'code=54fe5f4e&state=/lol',
            uri: '/some/path',
          },
        }
      }]
    };
    mAxios.request = jest.fn().mockRejectedValue({
      Msg: 'Something Happened'
    });

    // Act & Assert
    await expect(handler(req, {
      ...{} as any
    }, () => ({}))).rejects.toEqual({ Msg: 'Something Happened' });

  });

  test('clears Cognito cookies if there are duplicates', async () => {
    // Arrange 
    const req: CloudFrontRequestEvent = {
      Records: [{
        cf: {
          config: {
            distributionDomainName: 'dist.cloudfront.net',
            distributionId: 'DIST123',
            eventType: 'viewer-request',
            requestId: 'req-id'
          },
          request: {
            clientIp: '0.0.0.0',
            headers: {
              host: [{
                key: 'Host',
                value: 'dist.cloudfront.net',
              }],
              cookie: [
                {
                  key: 'cookie',
                  value: 'CognitoIdentityServiceProvider.test-client-id.toto.idToken=abc;'
                },
                {
                  key: 'cookie',
                  value: 'CognitoIdentityServiceProvider.test-client-id.tonto.idToken=def;'
                },
                {
                  key: 'cookie',
                  value: 'CognitoIdentityServiceProvider.test-client-id.toto.accessToken=cba;'
                },
                {
                  key: 'cookie',
                  value: 'CognitoIdentityServiceProvider.test-client-id.tonto.accessToken=fed;'
                },
              ]
            },
            method: 'GET',
            querystring: '',
            uri: '/some/path',
          },
        }
      }]
    };

    // Act
    const resp = await handler(req, {
      ...{} as any
    }, () => ({}));

    // Assert
    const cfResponse: CloudFrontResultResponse = resp as CloudFrontResultResponse;
    expect(cfResponse.status).toBe('302');
    expect(cfResponse.headers?.location[0].value || '').toBe('/some/path');
    expect(cfResponse.headers?.['set-cookie']).toHaveLength(4);
  });
});
