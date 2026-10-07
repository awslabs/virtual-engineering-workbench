import { Construct } from 'constructs';
import {
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

// WAFv2 accepts a CLOUDFRONT-scoped web ACL only in us-east-1, so it cannot sit
// in the deployment stack unless the deployment itself is there. The ARN is
// handed back through crossRegionReferences rather than SSM, because the
// consumer is the distribution in this same app rather than a separate repo.
export class WafCloudFrontStack extends Stack {
  public readonly aclArn: string;

  constructor(
    scope: Construct, id: string, props: StackProps & {
      appName: string,
      appEnvironment: string,
      formatResourceName: (rn: string) => string,
    }
  ) {
    super(scope, id, props);

    const fmt = props.formatResourceName;
    const acl = new AccessControlList(this, 'cloudfront-acl', {
      name: fmt('cloudfront-acl'),
      scope: 'CLOUDFRONT',
      metricName: 'CloudFrontACL',
      formatResourceName: fmt,
      beforeIpEvaluationRules: STANDARD_MANAGED_RULES(fmt('managed')),
      ipSets: [],
    });
    this.aclArn = acl.acl.attrArn;

    Aspects.of(this).add(new AwsSolutionsChecks({ reports: true, verbose: true }));
    Aspects.of(this).add(new NIST80053R4Checks({ reports: true, verbose: true }));
    Aspects.of(this).add(new NIST80053R5Checks({ reports: true, verbose: true }));
  }
}
