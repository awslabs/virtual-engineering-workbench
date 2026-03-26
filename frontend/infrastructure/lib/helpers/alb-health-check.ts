import middy from '@middy/core';
import { ALBEvent, ALBEventMultiValueHeaders, ALBResult } from 'aws-lambda';

/* eslint consistent-return: "off" */

const albHealthCheck = (): middy.MiddlewareObj<ALBEvent, ALBResult> => {

  const before: middy.MiddlewareFn<ALBEvent, ALBResult> = (
    request
  ): ALBResult | void => {

    const userAgent = getHeaderValues(request.event.multiValueHeaders || {}, 'user-agent');

    if (userAgent.some(x => x === 'ELB-HealthChecker/2.0')) {
      return {
        statusCode: 200,
        body: ''
      };
    }
  };

  return {
    before,
  };

  function getHeaderValues(headers: ALBEventMultiValueHeaders, headerName: string): string[] {
    return Object.
      entries(headers || {}).
      filter(([key, val]) => key.toLowerCase() === headerName).
      flatMap(([key, val]) => val?.map(x => x || '') || []) || [];
  }
};

export { albHealthCheck };
