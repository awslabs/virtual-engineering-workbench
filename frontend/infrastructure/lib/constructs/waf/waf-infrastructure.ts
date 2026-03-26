import { Construct } from 'constructs';
import { aws_ssm as ssm } from 'aws-cdk-lib';
import { AccessControlList } from './access-control-list';
import { STANDARD_MANAGED_RULES } from './access-control-list-rules';

const TEST_ENVIRONMENTS = new Set(['dev', 'qa']);

export interface WafInfrastructureProps {
  appEnvironment: string,
  formatResourceName: (rn: string) => string,
  provisionApiAcl: boolean,
}

export class WafInfrastructure extends Construct {
  public readonly cloudfrontAclArn: string;
  public readonly cognitoAclArn: string;
  public readonly apiAclArn?: string;

  constructor(scope: Construct, id: string, props: WafInfrastructureProps) {
    super(scope, id);

    this.cloudfrontAclArn = this._createCloudfrontAcl(props);
    this.cognitoAclArn = this._createCognitoAcl(props);

    if (props.provisionApiAcl) {
      this.apiAclArn = this._createApiAcl(props);
    }
  }

  private _createCloudfrontAcl(props: WafInfrastructureProps): string {
    const fmt = props.formatResourceName;
    const acl = new AccessControlList(this, 'cloudfront-acl', {
      name: fmt('cloudfront-acl'),
      scope: 'CLOUDFRONT',
      metricName: 'CloudFrontACL',
      formatResourceName: fmt,
      beforeIpEvaluationRules: STANDARD_MANAGED_RULES(fmt('managed')),
      ipSets: [],
    });
    return acl.acl.attrArn;
  }

  private _createCognitoAcl(props: WafInfrastructureProps): string {
    const fmt = props.formatResourceName;
    const acl = new AccessControlList(this, 'cognito-acl', {
      name: fmt('cognito-acl'),
      scope: 'REGIONAL',
      metricName: 'CognitoACL',
      formatResourceName: fmt,
      beforeIpEvaluationRules: STANDARD_MANAGED_RULES(fmt('managed'), {
        environment: props.appEnvironment,
        testEnvironments: TEST_ENVIRONMENTS,
      }),
      ipSets: [],
    });
    return acl.acl.attrArn;
  }

  private _createApiAcl(props: WafInfrastructureProps): string {
    const fmt = props.formatResourceName;
    const acl = new AccessControlList(this, 'api-acl', {
      name: fmt('api-acl'),
      scope: 'REGIONAL',
      metricName: 'RESTApiACL',
      formatResourceName: fmt,
      beforeIpEvaluationRules: STANDARD_MANAGED_RULES(fmt('managed'), {
        standardRuleActionOverrides: [{
          name: 'SizeRestrictions_BODY',
          actionToUse: { allow: {} },
        }],
      }),
      ipSets: [],
    });

    new ssm.StringParameter(this, 'api-acl-ssm', {
      parameterName: `/virtual-workbench/${props.appEnvironment}/ui/waf-api-acl-arn`,
      stringValue: acl.acl.attrArn,
    });

    return acl.acl.attrArn;
  }
}
