import { PostAuthenticationTriggerHandler, PostAuthenticationTriggerEvent } from 'aws-lambda';
import { Logger } from '@aws-lambda-powertools/logger';
import { injectLambdaContext } from '@aws-lambda-powertools/logger/middleware';
import middy from '@middy/core';

const logger = new Logger();

export const lambdaHandler: PostAuthenticationTriggerHandler =
  async (event: PostAuthenticationTriggerEvent) => {

    const { userName } = event;
    const userTid = event.request.userAttributes['custom:user_tid'];

    if (userTid === undefined) {
      logger.warn('User TID not in the context.');
      return event;
    }

    const logObject = {
      action: 'login',
      username: userName,
      tid: userTid,
    };

    logger.info('Login successful', logObject);

    return Promise.resolve(event);
  };


export const handler = middy(lambdaHandler)
  .use(injectLambdaContext(logger, { logEvent: true }));
