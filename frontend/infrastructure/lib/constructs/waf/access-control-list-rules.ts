import { aws_wafv2 as wafv2 } from 'aws-cdk-lib';

interface Config {
  environment?: string,
  testEnvironments?: Set<string>,
  standardRuleActionOverrides?:
  wafv2.CfnWebACL.RuleActionOverrideProperty[],
}

const anonymousIpRule: (
  name: string
) => wafv2.CfnWebACL.RuleProperty = (name) => ({
  name,
  priority: 0,
  visibilityConfig: {
    sampledRequestsEnabled: true,
    cloudWatchMetricsEnabled: true,
    metricName: 'CloudFrontAnonymousIpList',
  },
  statement: {
    managedRuleGroupStatement: {
      vendorName: 'AWS',
      name: 'AWSManagedRulesAnonymousIpList',
    },
  },
  overrideAction: { none: {} },
});

const reputationIpRule: (
  name: string
) => wafv2.CfnWebACL.RuleProperty = (name) => ({
  name,
  priority: 0,
  visibilityConfig: {
    sampledRequestsEnabled: true,
    cloudWatchMetricsEnabled: true,
    metricName: 'CloudFrontReputationIpList',
  },
  statement: {
    managedRuleGroupStatement: {
      vendorName: 'AWS',
      name: 'AWSManagedRulesAmazonIpReputationList',
    },
  },
  overrideAction: { none: {} },
});

const badInputsRule: (
  name: string
) => wafv2.CfnWebACL.RuleProperty = (name) => ({
  name,
  priority: 0,
  visibilityConfig: {
    sampledRequestsEnabled: true,
    cloudWatchMetricsEnabled: true,
    metricName: 'CloudFrontBadInputs',
  },
  statement: {
    managedRuleGroupStatement: {
      vendorName: 'AWS',
      name: 'AWSManagedRulesKnownBadInputsRuleSet',
    },
  },
  overrideAction: { none: {} },
});

const commonRule: (
  name: string, config?: Config
) => wafv2.CfnWebACL.RuleProperty = (name, config) => {
  const overrides:
  wafv2.CfnWebACL.RuleActionOverrideProperty[] =
    config?.standardRuleActionOverrides || [];

  if (isTestEnvironment(config)) {
    overrides.push({
      name: 'EC2MetaDataSSRF_QUERYARGUMENTS',
      actionToUse: { allow: {} },
    });
  }

  return {
    name,
    priority: 0,
    visibilityConfig: {
      sampledRequestsEnabled: true,
      cloudWatchMetricsEnabled: true,
      metricName: 'CloudFrontCommon',
    },
    statement: {
      managedRuleGroupStatement: {
        vendorName: 'AWS',
        name: 'AWSManagedRulesCommonRuleSet',
        ruleActionOverrides: overrides,
      },
    },
    overrideAction: { none: {} },
  };
};

export const STANDARD_MANAGED_RULES: (
  name: string, config?: Config
) => wafv2.CfnWebACL.RuleProperty[] = (name, config) => [
  anonymousIpRule(`${name}-anonymous`),
  reputationIpRule(`${name}-reputation`),
  badInputsRule(`${name}-bad-inputs`),
  commonRule(`${name}-common`, config),
];

function isTestEnvironment(config?: Config): boolean {
  return !!config
    && !!config.testEnvironments
    && !!config.environment
    && config.testEnvironments.has(
      config.environment.toLowerCase()
    );
}
