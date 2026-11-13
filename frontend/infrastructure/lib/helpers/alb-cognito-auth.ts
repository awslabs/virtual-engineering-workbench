import middy from '@middy/core';
import {
  CloudFrontRequestEvent,
  CloudFrontRequest,
  CloudFrontResultResponse,
  APIGatewayProxyEvent,
  APIGatewayProxyResult,
  APIGatewayProxyEventMultiValueHeaders,
  CloudFrontHeaders,
  APIGatewayProxyEventMultiValueQueryStringParameters
} from 'aws-lambda';
import { AsyncHandler, LogLevel } from '../helpers/async-handler';
import { Logger } from '@aws-lambda-powertools/logger';

/* eslint consistent-return: "off" */

interface ALBCognitoAuthProps {
  dnsName: string,
  region: string,
  logLevel: string,
  cookieExpirationDays: number,
  userPoolId: string,
  userPoolClientId: string,
  userPoolDomain: string,
  logger: Logger,
}

class DefaultIfNull<T> {
  /**
   *
   */
  constructor(
    private readonly _realValue: T | undefined | null,
    private readonly _default: T,
  ) {}

  get value(): T {
    return this._realValue || this._default;
  }
}

/*
  This middleware for middy adds Cognito authentication to the request handling pipeline.
  Cognito auth handling reuses the Lambda@Edge implementation that is used for CloudFront deployment.
*/
const cognitoAuth = ({
  dnsName,
  region,
  logLevel,
  cookieExpirationDays,
  userPoolId,
  userPoolClientId,
  userPoolDomain,
  logger,
}: ALBCognitoAuthProps): middy.MiddlewareObj<APIGatewayProxyEvent, APIGatewayProxyResult> => {

  const before: middy.MiddlewareFn<APIGatewayProxyEvent, APIGatewayProxyResult> = async (
    request
  ): Promise<APIGatewayProxyResult | void> => {

    const cfRequest: CloudFrontRequest = {
      clientIp: getHeaderValues(request.event.multiValueHeaders, 'X-Forwarded-For').pop() || '',
      headers: mapGWHeaderValuesToCF(request.event.multiValueHeaders),
      method: request.event.httpMethod,
      querystring: mapGWQueryStringToCF(request.event.multiValueQueryStringParameters),
      uri: request.event.path,
    };

    const cfEvt: CloudFrontRequestEvent = {
      Records: [{
        cf: {
          config: {
            distributionDomainName: dnsName,
            distributionId: 'n/a',
            eventType: 'viewer-request',
            requestId: 'n/a'
          },
          request: cfRequest,
        }
      }]
    };

    // Logs the shape of the mapped request, not the request itself: cfRequest
    // carries the inbound Cookie header, which holds the Cognito session
    // cookies. Header names are enough to diagnose a mapping problem.
    logger.debug({
      message: 'Lambda@Edge mapped CloudFront request',
      method: cfRequest.method,
      uri: cfRequest.uri,
      headerNames: Object.keys(cfRequest.headers).sort(),
    });

    const cfResponse = await AsyncHandler.handleAsync(
      cfEvt,
      {
        region,
        logLevel: (logLevel.toLowerCase()) as LogLevel,
        cookieExpirationDays,
        userPoolIdResolver: () => Promise.resolve(userPoolId),
        userPoolClientIdResolver: () => Promise.resolve(userPoolClientId),
        userPoolDomainResolver: () => Promise.resolve(userPoolDomain),
      });

    if (cfResponse !== cfRequest) {
      const fcTypedResponse = cfResponse as CloudFrontResultResponse;
      const response = {
        statusCode: parseInt(fcTypedResponse.status),
        isBase64Encoded: false,
        multiValueHeaders: mapCFHeaderValuesToGW(fcTypedResponse.headers),
        body: new DefaultIfNull(fcTypedResponse.body, '').value,
      };

      // Logs the shape of the response, not the response itself: on the
      // auth-redirect path multiValueHeaders carries Set-Cookie, which is
      // where the session cookie is issued, and body can carry a token.
      logger.debug({
        message: 'Lambda@Edge mapped API Gateway response:',
        statusCode: response.statusCode,
        headerNames: Object.keys(response.multiValueHeaders).sort(),
        bodyLength: response.body.length,
      });

      return response;
    }
    logger.debug({
      message: 'User is authenticated.',
    });
  };

  return {
    before,
  };

  function getHeaderValues(headers: APIGatewayProxyEventMultiValueHeaders, headerName: string): string[] {
    return Object.
      entries(headers || {}).
      filter(([key, val]) => key.toLowerCase() === headerName).
      flatMap(([key, val]) => val?.map(x => x || '') || []) || [];
  }

  function mapGWHeaderValuesToCF(headers: APIGatewayProxyEventMultiValueHeaders): CloudFrontHeaders {
    return Object.entries(headers || {}).reduce((prev, curr) => ({
      ...prev,
      [curr[0].toLowerCase()]: (curr[1] || []).map(value => ({
        key: curr[0],
        value
      }))
    }), {});
  }

  function mapCFHeaderValuesToGW(headers: CloudFrontHeaders | undefined) {
    return Object.entries(headers || {}).reduce((prev, curr) => ({
      ...prev,
      [curr[0]]: curr[1].map(x => x.value)
    }), {});
  }

  function mapGWQueryStringToCF(params: APIGatewayProxyEventMultiValueQueryStringParameters | null): string {
    return Object.entries(params || {}).flatMap(([key, val]) => (val || []).map(v => `${key}=${v}`)).join('&');
  }
};

export { cognitoAuth };
