from enum import StrEnum

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_iam, aws_lambda, aws_logs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks

from infra import config


class AdditionalConfigurationRunStatus(StrEnum):
    InProgress = "IN_PROGRESS"
    Success = "SUCCESS"
    Failed = "FAILED"


class ProvisionedProductConfigurationStateMachine(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        provisioned_product_configuration_lambda: aws_lambda.Function,
    ) -> None:
        """
        Sample expected input for the state machine:
        {
            "version": "0",
            "id": "a0fd2d09-02c3-1696-1cee-406e4cc14c86",
            "detail-type": "ProvisionedProductConfigurationRequested",
            "source": "prefix.workbench.provisioning.dev",
            "account": "201223934255",
            "time": "2024-06-27T14:18:48Z",
            "region": "us-east-1",
            "resources": [],
            "detail": {
                "eventName": "ProvisionedProductConfigurationRequested",
                "provisionedProductId": "pp-12345",
            }
        }
        """
        super().__init__(scope, id)

        # Starting state
        start_state: sfn.Pass = sfn.Pass(self, "StartState", output_path="$.detail")

        # Success State
        success_state: sfn.Succeed = sfn.Succeed(self, "SuccessState")

        # Fail State
        fail_state: sfn.Fail = sfn.Fail(self, "FailState")

        # Start configuration Lambda
        start_config_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "StartConfigLambda",
            lambda_function=provisioned_product_configuration_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "StartProvisionedProductConfigurationRequest",
                    "provisionedProductId.$": "$.provisionedProductId",
                }
            ),
            result_selector={"eventType.$": "$.Payload.eventType"},
            result_path="$.startProvisionedProductConfigurationResponse",
        )

        # Is provisioned product ready Lambda
        is_provisioned_product_ready_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "IsProvisionedProductReadyLambda",
            lambda_function=provisioned_product_configuration_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "IsProvisionedProductReadyRequest",
                    "provisionedProductId.$": "$.provisionedProductId",
                }
            ),
            result_selector={
                "eventType.$": "$.Payload.eventType",
                "isReady.$": "$.Payload.isReady",
            },
            result_path="$.isProvisionedProductReadyResponse",
        )

        # Get the status of the configuration Lambda
        get_config_status_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "GetConfigStatusLambda",
            lambda_function=provisioned_product_configuration_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "GetProvisionedProductConfigurationStatusRequest",
                    "provisionedProductId.$": "$.provisionedProductId",
                }
            ),
            result_selector={
                "eventType.$": "$.Payload.eventType",
                "status.$": "$.Payload.status",
                "reason.$": "$.Payload.reason",
            },
            result_path="$.getProvisionedProductConfigurationStatusResponse",
        )

        # Fail configuration Lambda
        fail_config_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "FailConfigLambda",
            lambda_function=provisioned_product_configuration_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "FailProvisionedProductConfigurationRequest",
                    "provisionedProductId.$": "$.provisionedProductId",
                    "reason.$": "$.reason.reason",
                }
            ),
            result_selector={"eventType.$": "$.Payload.eventType"},
            result_path="$.failProvisionedProductConfigurationResponse",
        )

        # Complete configuration Lambda
        complete_config_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CompleteConfigLambda",
            lambda_function=provisioned_product_configuration_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CompleteProvisionedProductConfigurationRequest",
                    "provisionedProductId.$": "$.provisionedProductId",
                }
            ),
            result_selector={"eventType.$": "$.Payload.eventType"},
            result_path="$.completeProvisionedProductConfigurationResponse",
        )

        # Pass state to assign the reason
        pass_reason_assignment: sfn.Pass = sfn.Pass(
            self,
            "PassReasonAssignment",
            parameters={"reason.$": "$.getProvisionedProductConfigurationStatusResponse.reason"},
            result_path="$.reason",
        )

        # Pass state to assign the reason in case of error
        pass_reason_assignment_on_error: sfn.Pass = sfn.Pass(
            self,
            "PassReasonAssignmentOnError",
            parameters={"reason.$": "States.JsonToString($.error)"},
            result_path="$.reason",
        )
        pass_reason_assignment_on_error.next(fail_config_lambda)

        # Wait for the configuration and provisioned product
        config_wait: sfn.Wait = sfn.Wait(self, "ConfigWait", time=sfn.WaitTime.duration(aws_cdk.Duration.seconds(10)))
        provisioned_product_wait = sfn.Wait(
            self,
            "ProvisionedProductWait",
            time=sfn.WaitTime.duration(aws_cdk.Duration.seconds(10)),
        )

        # Check configuration status
        check_config_status_choice: sfn.Choice = sfn.Choice(self, "CheckConfigurationStatusChoice")

        # Check provisioned product ready
        provisioned_product_ready_choice: sfn.Choice = sfn.Choice(self, "ProvisionedProductReadyChoice")

        # Define the chain
        chain = sfn.DefinitionBody.from_chainable(
            sfn.Chain.start(start_state)
            .next(is_provisioned_product_ready_lambda.add_catch(pass_reason_assignment_on_error, result_path="$.error"))
            .next(
                provisioned_product_ready_choice.when(
                    sfn.Condition.boolean_equals("$.isProvisionedProductReadyResponse.isReady", True),
                    start_config_lambda.add_catch(pass_reason_assignment_on_error, result_path="$.error")
                    .next(config_wait)
                    .next(get_config_status_lambda.add_catch(pass_reason_assignment_on_error, result_path="$.error"))
                    .next(
                        check_config_status_choice.when(
                            sfn.Condition.string_equals(
                                "$.getProvisionedProductConfigurationStatusResponse.status",
                                AdditionalConfigurationRunStatus.Success,
                            ),
                            complete_config_lambda.add_catch(
                                pass_reason_assignment_on_error, result_path="$.error"
                            ).next(success_state),
                        )
                        .when(
                            sfn.Condition.string_equals(
                                "$.getProvisionedProductConfigurationStatusResponse.status",
                                AdditionalConfigurationRunStatus.Failed,
                            ),
                            pass_reason_assignment.next(fail_config_lambda).next(fail_state),
                        )
                        .otherwise(config_wait)
                        .afterwards()
                    ),
                )
                .otherwise(provisioned_product_wait.next(is_provisioned_product_ready_lambda))
                .afterwards()
            )
        )

        # Define log group
        log_group = aws_logs.LogGroup(
            self,
            "ProvisionedProductConfigurationStateMachineLogGroup",
            log_group_name=app_config.format_resource_name("pp-configuration-state-machine-log-group"),
            removal_policy=aws_cdk.RemovalPolicy.RETAIN,
            retention=aws_logs.RetentionDays.TWO_MONTHS,
        )

        # Define the state machine
        self._state_machine: sfn.StateMachine = sfn.StateMachine(
            self,
            "ProvisionedProductConfigurationStateMachine",
            state_machine_name=app_config.format_resource_name("pp-configuration-state-machine"),
            logs=sfn.LogOptions(destination=log_group, level=sfn.LogLevel.ALL),
            tracing_enabled=True,
            definition_body=chain,
        )

        # cdk-nag suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=log_group,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-CloudWatchLogGroupEncrypted",
                    reason="Log group is encrypted with default master key.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-CloudWatchLogGroupEncrypted",
                    reason="Log group is encrypted with default master key.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-CloudWatchLogGroupEncrypted",
                    reason="Log group is encrypted with default master key.",
                ),
            ],
        )

        state_machine_role_policies = [
            p for p in self._state_machine.role.node.children if isinstance(p, aws_iam.Policy)
        ]
        for policy in state_machine_role_policies:
            cdk_nag.NagSuppressions.add_resource_suppressions(
                construct=policy,
                suppressions=[
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-IAM5", reason="This policy is autogenerated by CDK with minimal permissions."
                    ),
                    cdk_nag.NagPackSuppression(
                        id="NIST.800.53.R4-IAMNoInlinePolicy",
                        reason="This is an inline policy auto-generated by CDK.",
                    ),
                    cdk_nag.NagPackSuppression(
                        id="NIST.800.53.R5-IAMNoInlinePolicy",
                        reason="This is an inline policy auto-generated by CDK.",
                    ),
                    cdk_nag.NagPackSuppression(
                        id="PCI.DSS.321-IAMNoInlinePolicy",
                        reason="This is an inline policy auto-generated by CDK.",
                    ),
                ],
            )

    @property
    def state_machine(self):
        return self._state_machine
