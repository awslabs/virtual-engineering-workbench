#!/usr/bin/env node
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import 'source-map-support/register';
import { App } from 'aws-cdk-lib';
import { PublicAccessDeploymentStack } from '../lib/public-access-deployment-stack';
import { getResourceName, getStackName } from './conventions';
import { AppConfig } from '../lib/app-config';
import { PrivateAccessDeploymentStack } from '../lib/private-access-deployment-stack';
import { PublicAccessDeploymentParamsStack } from '../lib/public-access-deployment-stack-params';
import { WafRegionalStack } from '../lib/waf-regional-stack';

const app = new App();
const appName = app.node.tryGetContext('app-name');
const deploymentQualifier = app.node.tryGetContext('deployment-qualifier');
const appEnvironment = app.node.tryGetContext('environment');
const account = app.node.tryGetContext('account');
const region = app.node.tryGetContext('region');
const beRegion = app.node.tryGetContext('be-region');

const allowedEnvironments = new Set(['dev', 'qa', 'prod']);

if (appName === undefined ||
  appName === '') {
  throw new Error('Must specify app name: -c app-name=my-web-app');
}

if (deploymentQualifier === undefined ||
  deploymentQualifier === '') {
  throw new Error('Must specify deployment qualifier: -c deployment-qualifier=hash');
}

if (account === undefined ||
  account === '') {
  throw new Error('Must specify deployment account.');
}

if (region === undefined ||
  region === '') {
  throw new Error('Must specify deployment region.');
}

if (appEnvironment === undefined ||
  appEnvironment === '' ||
  !allowedEnvironments.has(appEnvironment)) {
  throw new Error(`Must specify environment (one of ${Array.from(allowedEnvironments)}): -c environment=dev`);
}

const config = AppConfig.loadForEnvironment(app, appEnvironment);

if (config.privateDeployment) {
  new PrivateAccessDeploymentStack(app, 'PrivateDeploymentStack', {
    stackName: getStackName(appName, appEnvironment),
    appName,
    deploymentQualifier,
    appEnvironment,
    env: {
      region,
      account,
    },
    formatResourceName: (resourceName: string) => getResourceName(appName, resourceName, appEnvironment),
    appConfig: config,
  });
}

if (!config.privateDeployment) {
  const isBackendInSameRegion = beRegion === undefined || beRegion === 'us-east-1';

  const infraStack = new PublicAccessDeploymentStack(app, 'InfrastructureStack', {
    stackName: getStackName(appName, appEnvironment),
    appName,
    deploymentQualifier,
    appEnvironment,
    env: {
      region,
      account,
    },
    formatResourceName: (resourceName: string) => getResourceName(appName, resourceName, appEnvironment),
    appConfig: config,
    wafProps: {
      provisionApiAcl: isBackendInSameRegion,
    },
  });

  if (!isBackendInSameRegion) {
    const wafRegionalStack = new WafRegionalStack(app, 'WafRegionalStack', {
      stackName: getStackName(`${appName}-waf`, appEnvironment),
      appName,
      appEnvironment,
      formatResourceName: (resourceName: string) => getResourceName(appName, resourceName, appEnvironment),
      env: {
        region: beRegion,
        account,
      },
    });
    wafRegionalStack.addDependency(infraStack);

    const paramsStack = new PublicAccessDeploymentParamsStack(app, 'InfrastructureStackParams', {
      stackName: getStackName(`${appName}-params`, appEnvironment),
      appName,
      deploymentQualifier,
      appEnvironment,
      env: {
        region: beRegion,
        account,
      },
      formatResourceName: (resourceName: string) => getResourceName(appName, resourceName, appEnvironment),
      appConfig: config,
    });
    paramsStack.addDependency(infraStack);
  }
}