import { App } from 'aws-cdk-lib';

/**
 * An app client in VEW's user pool besides the web client, for an application
 * that calls VEW's API with its users' own tokens. Its id is added to the list
 * VEW's API authorizer accepts.
 */
export interface AdditionalAppClient {
  name: string,
  callbackUrls: string[],
  logoutUrls: string[],
  generateSecret: boolean,
  refreshTokenValidityHours?: number,
}

const MAX_REFRESH_TOKEN_VALIDITY_HOURS = 87600;

export class AppConfig {

  private constructor(
    public readonly customLoginDNSEnabled: boolean,
    public readonly logoutUrl?: string,
    public readonly certArn?: string,
    public readonly certArnLogin?: string,
    public readonly domainName?: string,
    public readonly domainNameLogin?: string,
    public readonly oidcSecretName?: string,
    public readonly oidcUserIdClaim: string = 'sub',
    public readonly vpcName?: string,
    public readonly adoptedVpc?: boolean,
    public readonly privateDeployment?: boolean,
    public readonly allowCustomUserLogin?: boolean,
    public readonly requireCustomUserLogin2FA?: boolean,
    public readonly additionalAppClients: AdditionalAppClient[] = [],
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
      environmentConfig.OIDCUserIdClaim || 'sub',
      environmentConfig.VPCName,
      environmentConfig.AdoptedVPC,
      environmentConfig.PrivateDeployment,
      environmentConfig.AllowCustomUserLogin,
      environmentConfig.RequireCustomUserLogin2FA,
      AppConfig._parseAdditionalAppClients(environmentConfig.AdditionalAppClients),
    );
  }

  private static _parseAdditionalAppClients(raw: unknown): AdditionalAppClient[] {
    if (raw === undefined) {
      return [];
    }
    if (!Array.isArray(raw)) {
      throw new Error('AdditionalAppClients must be a list.');
    }

    const clients = raw.map(AppConfig._parseAdditionalAppClient);
    // Stack outputs are keyed on the name without its dashes, so 'my-app' and
    // 'myapp' would collide there rather than here.
    const names = new Map<string, string>();
    for (const { name } of clients) {
      const key = name.replace(/-/gu, '');
      const other = names.get(key);
      if (other !== undefined) {
        throw new Error(`AdditionalAppClients: Name ${name} collides with ${other}.`);
      }
      names.set(key, name);
    }
    return clients;
  }

  private static _parseAdditionalAppClient(entry: unknown): AdditionalAppClient {
    if (typeof entry !== 'object' || entry === null || Array.isArray(entry)) {
      throw new Error(`AdditionalAppClients: each entry must be an object, got ${JSON.stringify(entry)}.`);
    }
    const fields = entry as Record<string, unknown>;
    const name = AppConfig._parseName(fields.Name);

    const callbackUrls = AppConfig._parseUrls(name, 'CallbackUrls', fields.CallbackUrls);
    if (callbackUrls.length === 0) {
      throw new Error(`AdditionalAppClients ${name}: CallbackUrls must not be empty.`);
    }

    return {
      name,
      callbackUrls,
      logoutUrls: AppConfig._parseUrls(name, 'LogoutUrls', fields.LogoutUrls ?? []),
      generateSecret: AppConfig._parseGenerateSecret(name, fields.GenerateSecret),
      refreshTokenValidityHours: AppConfig._parseRefreshTokenValidityHours(
        name, fields.RefreshTokenValidityHours
      ),
    };
  }

  private static _parseName(raw: unknown): string {
    // The name becomes part of a construct id and of the Cognito client name,
    // and 'web-client' is the web app's own client.
    if (typeof raw !== 'string' || !/^[a-z0-9-]{1,64}$/u.test(raw) || raw === 'web-client') {
      throw new Error(`AdditionalAppClients: invalid Name ${JSON.stringify(raw)}.`);
    }
    return raw;
  }

  private static _parseGenerateSecret(clientName: string, raw: unknown): boolean {
    // Strict, because a mistyped "true" would otherwise create a public client,
    // and correcting it later replaces the client with a new id.
    if (raw !== undefined && typeof raw !== 'boolean') {
      throw new Error(`AdditionalAppClients ${clientName}: GenerateSecret must be true or false.`);
    }
    return raw ?? false;
  }

  private static _parseRefreshTokenValidityHours(clientName: string, raw: unknown): number | undefined {
    if (raw === undefined) {
      return undefined;
    }
    const max = MAX_REFRESH_TOKEN_VALIDITY_HOURS;
    if (typeof raw !== 'number' || !Number.isInteger(raw) || raw < 1 || raw > max) {
      throw new Error(
        `AdditionalAppClients ${clientName}: RefreshTokenValidityHours must be an integer from 1 to ${max}.`
      );
    }
    return raw;
  }

  private static _parseUrls(clientName: string, field: string, raw: unknown): string[] {
    if (!Array.isArray(raw)) {
      throw new Error(`AdditionalAppClients ${clientName}: ${field} must be a list.`);
    }
    return raw.map(url => {
      // Cognito allows http only for localhost.
      if (typeof url !== 'string' || !/^(?:https:\/\/|http:\/\/localhost(?:[:/]|$))/u.test(url)) {
        throw new Error(
          `AdditionalAppClients ${clientName}: ${field} has an invalid URL ${JSON.stringify(url)}.`
        );
      }
      return url;
    });
  }

  private static _getConfig(app: App, environment: string) {
    const config = app.node.tryGetContext('config');
    if (config === undefined || !(environment in config)) {
      throw new Error('CDK app is missing configuration.');
    }
    return config[environment];
  }
}
