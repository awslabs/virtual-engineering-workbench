import { FC } from 'react';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import { AppConfig } from '../../../utils/app-config';
import { fetchAuthSession } from 'aws-amplify/auth';
import { useParams } from 'react-router-dom';
import awsExports from '../../../aws-exports';

const SwaggerUIComponent: FC<unknown> = () => {

  const { boundedContextName } = useParams();

  const apiEndpoint = Object.values(
    awsExports.API.REST
  ).find(x => x.endpoint.endsWith(`/${boundedContextName}`));

  if (
    !apiEndpoint ||
    AppConfig.Environment.trim().toLowerCase() === 'prod'
  ) {
    return <></>;
  }

  return <SwaggerUI
    url={`${apiEndpoint.endpoint}/_swagger?format=json`}
    requestInterceptor={async (req) => {
      const session = await fetchAuthSession();
      req.headers.Authorization = `Bearer ${session.tokens?.accessToken?.toString()}`;
      return req;
    }}
    tryItOutEnabled
  />;

};

export default SwaggerUIComponent;