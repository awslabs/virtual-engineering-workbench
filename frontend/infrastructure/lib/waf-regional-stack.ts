import { Construct } from 'constructs';
import {
  aws_ssm as ssm,
  Stack,
  StackProps,
  Aspects,
} from 'aws-cdk-lib';
import { AccessControlList } from './constructs/waf/access-control-list';
import { STANDARD_MANAGED_RULES } from './constructs/waf/access-control-list-rules';
import {
  AwsSolutionsChecks,
  NIST80053R4Checks,
  NIST80053R5Checks,
} from 'cdk-nag';

export class WafRegionalStack extends Stack {
  constructor(
    scope: Construct, id: string, props: StackProps & {
      appName: string,
      appEnvironment: string,
      formatResourceName: (rn: string) => string,
    }
  ) {
    super(scope, id, props);

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

    Aspects.of(this).add(new AwsSolutionsChecks({ reports: true, verbose: true }));
    Aspects.of(this).add(new NIST80053R4Checks({ reports: true, verbose: true }));
    Aspects.of(this).add(new NIST80053R5Checks({ reports: true, verbose: true }));
  }
}
