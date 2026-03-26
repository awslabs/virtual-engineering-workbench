import { CloudFrontHeaders, CloudFrontRequestEvent, CloudFrontRequestResult } from 'aws-lambda';
import { AuthenticatorWithLogout } from './authenticator-with-logout';

/* eslint @typescript-eslint/naming-convention: "off" */

describe('AuthenticatorWithLogout', () => {

  function getRequestPayload(uri = '/logout'): CloudFrontRequestEvent {
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

  function getPassThroughResponse() {
    return {
      headers: {
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

  function getRedirectResponse(
    locationHeader = 'https://a.b/authorize?redirect_uri=https://a.b&response_type=code&client_id=123&state=/logout'
  ) {
    return {
      status: '302',
      headers: {
        location: [
          {
            key: 'Location',
            value: locationHeader
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

  function getLocationHeaderPathParams(response: CloudFrontRequestResult): string[] {
    const locationHeader = (response?.headers as CloudFrontHeaders).location[0];
    return locationHeader.value.split('&').reverse();
  }

  test('returns unaltered response for non-logout endpoint', async () => {
    // ARRANGE
    const handlerMock = jest.fn();
    const passThroughResponse = getPassThroughResponse();
    handlerMock.mockReturnValue(Promise.resolve(passThroughResponse));

    const decorator = AuthenticatorWithLogout.decorate({
      handle: handlerMock
    });

    // ACT
    const response = await decorator.handle(getRequestPayload('/workbenches'));

    // ASSERT
    expect(response).toBe(passThroughResponse);

  });

  test('returns unaltered redirect response for non-authorize response', async () => {
    // ARRANGE
    const handlerMock = jest.fn();
    const redirectResponse = getRedirectResponse('https://example.com?foo=bar');
    handlerMock.mockReturnValue(Promise.resolve(redirectResponse));

    const decorator = AuthenticatorWithLogout.decorate({
      handle: handlerMock
    });

    // ACT
    const response = await decorator.handle(getRequestPayload());

    // ASSERT
    expect(response).toBe(redirectResponse);

  });

  test('sets state to / for /logout endpoint', async () => {
    // ARRANGE
    const handlerMock = jest.fn();
    const redirectResponse = getRedirectResponse();
    handlerMock.mockReturnValue(Promise.resolve(redirectResponse));

    const decorator = AuthenticatorWithLogout.decorate({
      handle: handlerMock
    });

    // ACT
    const response = await decorator.handle(getRequestPayload());

    // ASSERT
    const locationPathParams = getLocationHeaderPathParams(response);
    expect(locationPathParams[1]).toBe('state=/');
  });

  test('adds fake idp provider for /logout endpoint', async () => {
    // ARRANGE
    const handlerMock = jest.fn();
    const redirectResponse = getRedirectResponse();
    handlerMock.mockReturnValue(Promise.resolve(redirectResponse));

    const decorator = AuthenticatorWithLogout.decorate({
      handle: handlerMock
    });

    // ACT
    const response = await decorator.handle(getRequestPayload());

    // ASSERT
    const locationPathParams = getLocationHeaderPathParams(response);
    expect(locationPathParams[0]).toBe('identity_provider=na');
  });

});
