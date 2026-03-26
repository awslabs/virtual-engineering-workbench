import constructs
from aws_cdk import aws_logs as logs
from aws_cdk import aws_wafv2 as wafv2
from cdk_nag import NagSuppressions


class BackendAppWaf(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        name: str,
        short_name: str,
        scope_name: str = "REGIONAL",
        encryption_key=None,
    ) -> None:
        super().__init__(scope, id)

        self.__acl = wafv2.CfnWebACL(
            self,
            "waf-acl",
            name=name,
            scope=scope_name,
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name=short_name,
            ),
            rules=self.__standard_managed_rules(name=name, metric_prefix=short_name),
        )

        log_group = logs.LogGroup(
            self,
            "waf-acl-log-group",
            log_group_name=f"aws-waf-logs-{name}",
            retention=logs.RetentionDays.TWO_MONTHS,
            encryption_key=encryption_key,
        )

        wafv2.CfnLoggingConfiguration(
            self,
            "waf-acl-log",
            log_destination_configs=[log_group.log_group_arn],
            resource_arn=self.__acl.attr_arn,
            logging_filter={
                "DefaultBehavior": "DROP",
                "Filters": [
                    {
                        "Behavior": "KEEP",
                        "Conditions": [{"ActionCondition": {"Action": "BLOCK"}}],
                        "Requirement": "MEETS_ANY",
                    }
                ],
            },
            redacted_fields=[
                wafv2.CfnLoggingConfiguration.FieldToMatchProperty(
                    query_string={}  # Redacting query string because it contains access tokens.
                )
            ],
        )

        NagSuppressions.add_resource_suppressions(
            log_group,
            [
                {
                    "id": "NIST.800.53.R4-CloudWatchLogGroupEncrypted",
                    "reason": "Currently we are not using KMS for log encryption.",
                },
                {
                    "id": "NIST.800.53.R5-CloudWatchLogGroupEncrypted",
                    "reason": "Currently we are not using KMS for log encryption.",
                },
                {
                    "id": "PCI.DSS.321-CloudWatchLogGroupEncrypted",
                    "reason": "Currently we are not using KMS for log encryption.",
                },
            ],
        )

    def __standard_managed_anonymous_ip_list_rule(self, name: str, metric_prefix: str) -> wafv2.CfnWebACL.RuleProperty:
        return wafv2.CfnWebACL.RuleProperty(
            name=name,
            priority=10,
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name=f"{metric_prefix}AnonymousIpList",
            ),
            statement=wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    vendor_name="AWS",
                    name="AWSManagedRulesAnonymousIpList",
                )
            ),
            override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
        )

    def __standard_managed_reputation_ip_list_rule(self, name: str, metric_prefix: str) -> wafv2.CfnWebACL.RuleProperty:
        return wafv2.CfnWebACL.RuleProperty(
            name=name,
            priority=20,
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name=f"{metric_prefix}ReputationIpList",
            ),
            statement=wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    vendor_name="AWS",
                    name="AWSManagedRulesAmazonIpReputationList",
                )
            ),
            override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
        )

    def __standard_managed_bad_inputs_rule(self, name: str, metric_prefix: str) -> wafv2.CfnWebACL.RuleProperty:
        return wafv2.CfnWebACL.RuleProperty(
            name=name,
            priority=30,
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name=f"{metric_prefix}BadInputs",
            ),
            statement=wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    vendor_name="AWS",
                    name="AWSManagedRulesKnownBadInputsRuleSet",
                )
            ),
            override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
        )

    def __standard_managed_common_rule(self, name: str, metric_prefix: str) -> wafv2.CfnWebACL.RuleProperty:
        return wafv2.CfnWebACL.RuleProperty(
            name=name,
            priority=40,
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name=f"{metric_prefix}Common",
            ),
            statement=wafv2.CfnWebACL.StatementProperty(
                managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                    vendor_name="AWS",
                    name="AWSManagedRulesCommonRuleSet",
                )
            ),
            override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
        )

    def __standard_managed_rules(self, name: str, metric_prefix: str) -> list[wafv2.CfnWebACL.RuleProperty]:
        return [
            self.__standard_managed_anonymous_ip_list_rule(f"{name}-anonymous", metric_prefix),
            self.__standard_managed_reputation_ip_list_rule(f"{name}-reputation", metric_prefix),
            self.__standard_managed_bad_inputs_rule(f"{name}-bad-inputs", metric_prefix),
            self.__standard_managed_common_rule(f"{name}-common", metric_prefix),
        ]

    @property
    def acl(self) -> wafv2.CfnWebACL:
        return self.__acl
