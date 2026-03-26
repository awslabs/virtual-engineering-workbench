// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { CloudFrontResponseEvent, CloudFrontResponseHandler } from 'aws-lambda';

export const handler: CloudFrontResponseHandler = async (event: CloudFrontResponseEvent) => {
  const request = event.Records[0].cf.request;
  const response = event.Records[0].cf.response;
  const responseHeaders = response.headers;

  if (request.clientIp) {
    responseHeaders['client-ip'] = [{
      key: 'Client-Ip',
      value: request.clientIp,
    }];
  }

  return Promise.resolve(response);
};
