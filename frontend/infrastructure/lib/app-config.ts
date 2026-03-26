import { App } from 'aws-cdk-lib';

export class AppConfig {

  private constructor(
    public readonly customLoginDNSEnabled: boolean,
    public readonly logoutUrl?: string,
    public readonly certArn?: string,
    public readonly certArnLogin?: string,
    public readonly domainName?: string,
    public readonly domainNameLogin?: string,
    public readonly oidcSecretName?: string,
    public readonly vpcName?: string,
    public readonly privateDeployment?: boolean,
    public readonly allowCustomUserLogin?: boolean,
    public readonly requireCustomUserLogin2FA?: boolean,
  ) {

  }

  public static loadForEnvironment(app: App, environment: string) : AppConfig {

    const environmentConfig = AppConfig._getConfig(app, environment);

    const certArn = app.node.tryGetContext('cert-arn');
    const certArnLogin = app.node.tryGetContext('cert-arn-login');
    const domainName = app.node.tryGetContext('use-custom-domain');
    const domainNameLogin = app.node.tryGetContext('use-custom-domain-login');

    return new AppConfig(
      environmentConfig.CustomLoginDNSEnabled || false,
      environmentConfig.LogoutUrl,
      certArn,
      certArnLogin,
      domainName,
      domainNameLogin,
      environmentConfig.OIDCSecretName,
      environmentConfig.VPCName,
      environmentConfig.PrivateDeployment,
      environmentConfig.AllowCustomUserLogin,
      environmentConfig.RequireCustomUserLogin2FA,
    );
  }

  private static _getConfig(app: App, environment: string) {
    const config = app.node.tryGetContext('config');
    if (config === undefined || !(environment in config)) {
      throw new Error('CDK app is missing configuration.');
    }
    return config[environment];
  }
}
