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

    logger.debug({
      message: 'Lambda@Edge mapped CloudFront request',
      cfEvt
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

      logger.debug({
        message: 'Lambda@Edge mapped API Gateway response:',
        response
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
