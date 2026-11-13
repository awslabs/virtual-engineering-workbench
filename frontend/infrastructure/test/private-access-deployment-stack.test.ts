import { Template } from 'aws-cdk-lib/assertions';
import { App } from 'aws-cdk-lib';
import { PrivateAccessDeploymentStack } from '../lib/private-access-deployment-stack';
import { AppConfig } from '../lib/app-config';

/* eslint jest/expect-expect: "off" */
/* eslint @typescript-eslint/naming-convention: "off" */

const DOMAIN_NAME = 'vew.example.internal';
const CERT_ARN = 'arn:aws:acm:eu-north-1:111111111111:certificate/00000000-0000-0000-0000-000000000000';
const PRIVATE_CA_ARN =
  'arn:aws:acm-pca:eu-north-1:222222222222:certificate-authority/11111111-1111-1111-1111-111111111111';
const LOGIN_DOMAIN_NAME = 'login.vew.example.internal';
const LOGIN_CERT_ARN = 'arn:aws:acm:us-east-1:111111111111:certificate/22222222-2222-2222-2222-222222222222';

function privateStack(
  context: { [key: string]: string },
  environmentConfig: { [key: string]: unknown } = {}
) {
  const app = new App({
    context: {
      'use-custom-domain': DOMAIN_NAME,
      ...context,
      config: {
        dev: { PrivateDeployment: true, VPCName: 'test-vpc', ...environmentConfig },
      },
    },
  });

  return new PrivateAccessDeploymentStack(app, 'PrivateTestStack', {
    stackName: 'ui-test',
    deploymentQualifier: 'abc',
    env: { account: '111111111111', region: 'eu-north-1' },
    appName: 'my-app',
    appEnvironment: 'dev',
    formatResourceName: (resourceName: string) => `test-${resourceName}`,
    appConfig: AppConfig.loadForEnvironment(app, 'dev'),
  });
}

test('private deployment should request its certificate from the private CA', () => {
  const template = Template.fromStack(privateStack({ 'private-ca-arn': PRIVATE_CA_ARN }));

  template.resourceCountIs('AWS::CertificateManager::Certificate', 1);
  template.hasResourceProperties('AWS::CertificateManager::Certificate', {
    DomainName: DOMAIN_NAME,
    CertificateAuthorityArn: PRIVATE_CA_ARN,
    KeyAlgorithm: 'RSA_2048',
  });
});

test('private deployment should serve the private CA certificate on the ALB and the API domain', () => {
  const template = Template.fromStack(privateStack({ 'private-ca-arn': PRIVATE_CA_ARN }));
  const [certificateId] = Object.keys(template.findResources('AWS::CertificateManager::Certificate'));

  template.hasResourceProperties('AWS::ElasticLoadBalancingV2::Listener', {
    Certificates: [{ CertificateArn: { Ref: certificateId } }],
  });
  template.hasResourceProperties('AWS::ApiGateway::DomainName', {
    DomainName: DOMAIN_NAME,
    RegionalCertificateArn: { Ref: certificateId },
  });
});

test('private deployment should serve a given certificate without requesting one', () => {
  const template = Template.fromStack(privateStack({ 'cert-arn': CERT_ARN }));

  template.resourceCountIs('AWS::CertificateManager::Certificate', 0);
  template.hasResourceProperties('AWS::ElasticLoadBalancingV2::Listener', {
    Certificates: [{ CertificateArn: CERT_ARN }],
  });
  template.hasResourceProperties('AWS::ApiGateway::DomainName', {
    RegionalCertificateArn: CERT_ARN,
  });
});

test('private deployment with a private CA should output its custom login domain', () => {
  const template = Template.fromStack(privateStack({
    'private-ca-arn': PRIVATE_CA_ARN,
    'use-custom-domain-login': LOGIN_DOMAIN_NAME,
    'cert-arn-login': LOGIN_CERT_ARN,
  }, { CustomLoginDNSEnabled: true }));

  template.hasOutput('*', { Export: { Name: 'ui-test-UserPoolCustomDomain' } });
  template.hasOutput('*', { Export: { Name: 'ui-test-UserPoolCustomDomainCloudFront' } });
});

test('private deployment should require a certificate or a private CA', () => {
  expect(() => privateStack({})).toThrow('Certificate ARN or private CA ARN is required');
});

test('private deployment should refuse both a certificate and a private CA', () => {
  expect(() => privateStack({ 'cert-arn': CERT_ARN, 'private-ca-arn': PRIVATE_CA_ARN }))
    .toThrow('Give either a certificate ARN or a private CA ARN, not both.');
});
