import { CloudFrontRequestEvent, CloudFrontRequest, CloudFrontResultResponse } from 'aws-lambda';
import { AuthenticatorWithRedirect } from './authenticator-with-redirect';

/* eslint @typescript-eslint/naming-convention: "off" */

describe('AuthenticatorWithRedirect', () => {

  function makeCloudFrontRequestEvent(uri = ''): CloudFrontRequestEvent {
    return {
      Records: [
        {
          cf: {
            config: {
              distributionDomainName: 'dist.cloudfront.net',
              distributionId: 'EFYOB5NDL712J',
              eventType: 'viewer-request',
              requestId: '81e6YRPfzQyFIH4OewmWsllFxyEI92FbOPl9Yx7oYI5UmMj0D4dptA=='
            },
            request: {
              clientIp: '0.0.0.0',
              headers: {},
              method: 'GET',
              querystring: '',
              uri: uri
            }
          }
        }
      ]
    };
  }

  function makeCloudFrontRequest(uri = '') {
    return {
      clientIp: '0.0.0.0',
      headers: {},
      method: 'GET',
      querystring: '',
      uri: uri
    };
  }

  function makeCloudFrontResultResponse(
    locationHeaderValue = ''
  ) {
    return {
      status: '302',
      headers: {
        location: [
          {
            key: 'Location',
            value: locationHeaderValue
          }
        ],
        'cache-control': [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, max-age=0, must-revalidate'
          }
        ],
        pragma: [
          {
            key: 'Pragma',
            value: 'no-cache'
          }
        ]
      }
    };
  }

  function makeCloudFrontSuccessfulAuthResponse() {
    return {
      status: '302',
      headers: {
        location: [
          {
            key: 'Location',
            value: '/whatever'
          }
        ],
        'cache-control': [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, max-age=0, must-revalidate'
          }
        ],
        pragma: [
          {
            key: 'Pragma',
            value: 'no-cache'
          }
        ],
        'set-cookie': [
          { key: 'value' }
        ]
      }
    };
  }

  test('can forward client to original request when user is authenticated', async () => {
    // ARRANGE
    const handlerMock = jest.fn();
    const passThroughResponse = makeCloudFrontRequest('/some/random/path');
    handlerMock.mockReturnValue(Promise.resolve(passThroughResponse));

    const decorator = AuthenticatorWithRedirect.decorate({
      handle: handlerMock
    });

    // ACT
    const response = await decorator.handle(makeCloudFrontRequestEvent('/some/path'));

    // ASSERT
    expect((response as CloudFrontRequest).uri).toEqual('/some/random/path');

  });

  test('can redirect to login when user is not authenticated and requests login page', async () => {
    // ARRANGE
    const handlerMock = jest.fn();
    const redirectResponse = makeCloudFrontResultResponse('/loginURI');
    handlerMock.mockReturnValue(Promise.resolve(redirectResponse));

    const decorator = AuthenticatorWithRedirect.decorate({
      handle: handlerMock
    });

    // ACT
    const response = await decorator.handle(makeCloudFrontRequestEvent('/login'));

    // ASSERT
    expect((response as CloudFrontResultResponse).status).toEqual('302');
    expect((response as CloudFrontResultResponse).headers?.location[0].value).toEqual('/loginURI');

  });

  test('passes through non authenticated user on non-login path', async () => {
    // ARRANGE
    const handlerMock = jest.fn();
    const redirectResponse = makeCloudFrontResultResponse('/landing/index.html');
    handlerMock.mockReturnValue(Promise.resolve(redirectResponse));

    const decorator = AuthenticatorWithRedirect.decorate({
      handle: handlerMock
    });

    // ACT
    const response = await decorator.handle(makeCloudFrontRequestEvent('/'));

    // ASSERT
    expect((response as CloudFrontRequest).uri).toEqual('/');
  });

  test('can access landing page directly', async () => {
    // ARRANGE
    const handlerMock = jest.fn();
    const redirectResponse = makeCloudFrontRequest('/landing/index.html');
    handlerMock.mockReturnValue(Promise.resolve(redirectResponse));

    const decorator = AuthenticatorWithRedirect.decorate({
      handle: handlerMock
    });

    // ACT
    const response = await decorator.handle(makeCloudFrontRequestEvent('/landing/index.html'));

    // ASSERT
    expect((response as CloudFrontRequest).uri).toEqual('/landing/index.html');
  });

  test('returns successfull Cognito@Edge auth response', async () => {
    // ARRANGE
    const handlerMock = jest.fn();
    const successfulAuthResponse = makeCloudFrontSuccessfulAuthResponse();
    handlerMock.mockReturnValue(Promise.resolve(successfulAuthResponse));

    const decorator = AuthenticatorWithRedirect.decorate({
      handle: handlerMock
    });

    const request = makeCloudFrontRequestEvent('/some/path');

    // ACT
    const response = await decorator.handle(request);

    // ASSERT
    expect(response).toStrictEqual(successfulAuthResponse);
  });

});
