import { Construct } from 'constructs';
import { aws_wafv2 as wafv2, aws_logs as logs } from 'aws-cdk-lib';
import { RetentionDays } from 'aws-cdk-lib/aws-logs';
import { NagSuppressions } from 'cdk-nag';
import { CfnWebACL } from 'aws-cdk-lib/aws-wafv2';

export class AccessControlList extends Construct {

  public readonly acl: wafv2.CfnWebACL;
  private _rules: wafv2.CfnWebACL.RuleProperty[] = [];

  constructor(
    scope: Construct, id: string, props: {
      formatResourceName: (rn: string) => string,
      name: string,
      scope: string,
      metricName: string,
      ipSets: wafv2.CfnIPSet[],
      beforeIpEvaluationRules?: wafv2.CfnWebACL.RuleProperty[],
      afterIpEvaluationRules?: wafv2.CfnWebACL.RuleProperty[],
      defaultAction?: CfnWebACL.DefaultActionProperty,
    }
  ) {
    super(scope, id);

    this._rules.push(
      ...this._processSortedRules(props.beforeIpEvaluationRules)
    );
    this._rules.push(
      ...this._processIpSetRules(props.ipSets, props.metricName)
    );
    this._rules.push(
      ...this._processSortedRules(props.afterIpEvaluationRules)
    );

    const defaultAction: CfnWebACL.DefaultActionProperty =
      props.defaultAction ?? { allow: {} };

    this.acl = new wafv2.CfnWebACL(this, 'waf-acl', {
      name: props.name,
      scope: props.scope,
      defaultAction,
      visibilityConfig: {
        sampledRequestsEnabled: true,
        cloudWatchMetricsEnabled: true,
        metricName: props.metricName,
      },
      rules: this._rules,
    });

    const logGroup = new logs.LogGroup(this, 'waf-acl-log-group', {
      logGroupName: `aws-waf-logs-${props.name}`,
      retention: RetentionDays.TWO_MONTHS,
    });

    new wafv2.CfnLoggingConfiguration(this, 'waf-acl-log', {
      logDestinationConfigs: [logGroup.logGroupArn],
      resourceArn: this.acl.attrArn,
      loggingFilter: {
        DefaultBehavior: 'DROP',
        Filters: [{
          Behavior: 'KEEP',
          Conditions: [{
            ActionCondition: { Action: 'BLOCK' },
          }],
          Requirement: 'MEETS_ANY',
        }],
      },
    });

    NagSuppressions.addResourceSuppressions(logGroup, [{
      id: 'NIST.800.53.R4-CloudWatchLogGroupEncrypted',
      reason: 'Not using KMS for log encryption.',
    }, {
      id: 'NIST.800.53.R5-CloudWatchLogGroupEncrypted',
      reason: 'Not using KMS for log encryption.',
    }]);
  }

  private _processSortedRules(
    rules?: wafv2.CfnWebACL.RuleProperty[]
  ) {
    let priority = this._rules.length;
    return (rules ?? []).map(r => ({
      ...r,
      priority: priority++,
    }));
  }

  private _processIpSetRules(
    ipSets: wafv2.CfnIPSet[], metricName: string
  ) {
    let priority = this._rules.length;
    return ipSets.map(ipSet => ({
      name: ipSet.name || '',
      priority: priority++,
      action: { allow: {} },
      visibilityConfig: {
        sampledRequestsEnabled: true,
        cloudWatchMetricsEnabled: true,
        metricName,
      },
      statement: {
        ipSetReferenceStatement: { arn: ipSet.attrArn },
      },
    }));
  }
}
