import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_iam, aws_lambda, aws_logs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks

from infra import config


class ComponentVersionTestingStateMachine(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        component_version_testing_lambda: aws_lambda.Function,
    ) -> None:
        """
        Sample expected input for the state machine:
        {
            "version": "0",
            "id": "0be91e9a-caed-4c4c-8072-f7c203cea24e",
            "detail-type": "ComponentVersionPublished",
            "source": "proserve.wb.packaging.dev",
            "account": "123456789012",
            "time": "2023-08-01T14:18:48Z",
            "region": "us-east-1",
            "resources": [],
            "detail": {
                "eventName": "ComponentVersionPublished",
                "componentId": "comp-12345abc",
                "componentVersionId": "version-12345abc",
            }
        }
        """
        super().__init__(scope, id)

        # Start State
        start: sfn.Pass = sfn.Pass(self, "Start", output_path="$.detail")

        # Fail State
        fail: sfn.Fail = sfn.Fail(self, "Fail")

        # Success State
        success: sfn.Succeed = sfn.Succeed(self, "Success")

        # Has Component Version Test Succeeded Choice
        has_component_version_test_succeeded: sfn.Choice = sfn.Choice(self, "HasComponentVersionTestSucceeded")

        has_component_version_test_succeeded.when(
            sfn.Condition.string_equals(
                "$.testExecutionDetails.componentVersionTestStatus",
                "SUCCESS",
            ),
            success,
        )
        has_component_version_test_succeeded.otherwise(fail)

        # Complete Component Version Test Task
        complete_component_version_test: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CompleteComponentVersionTest",
            lambda_function=component_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CompleteComponentVersionTestRequest",
                    "componentId.$": "$.componentId",
                    "componentVersionId.$": "$.componentVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "CompleteComponentVersionTestResponse",
                "componentVersionTestStatus.$": "$.Payload.componentVersionTestStatus",
            },
        )

        complete_component_version_test.add_catch(fail)
        complete_component_version_test.next(has_component_version_test_succeeded)

        # Launch Test Environment Task
        launch_test_environment: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "LaunchTestEnvironment",
            lambda_function=component_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "LaunchTestEnvironmentRequest",
                    "componentId.$": "$.componentId",
                    "componentVersionId.$": "$.componentVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "LaunchTestEnvironmentResponse",
            },
        )

        launch_test_environment.add_catch(complete_component_version_test, result_path="$.error")

        # Check Test Environment Launch Status Task
        check_test_environment_launch_status: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CheckTestEnvironmentLaunchStatus",
            lambda_function=component_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CheckTestEnvironmentLaunchStatusRequest",
                    "componentVersionId.$": "$.componentVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "CheckTestEnvironmentLaunchStatusResponse",
                "instancesStatus.$": "$.Payload.instancesStatus",
            },
        )

        check_test_environment_launch_status.add_catch(complete_component_version_test, result_path="$.error")

        # Is Test Environment Launched Choice
        is_test_environment_launched: sfn.Choice = sfn.Choice(self, "IsTestEnvironmentLaunched")

        # Wait for Test Environment Launched
        wait_for_test_environment_launched: sfn.Wait = sfn.Wait(
            self,
            "WaitForTestEnvironmentLaunched",
            time=sfn.WaitTime.duration(aws_cdk.Duration.seconds(15)),
        )

        # Setup Test Environment Task
        setup_test_environment: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "SetupTestEnvironment",
            lambda_function=component_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "SetupTestEnvironmentRequest",
                    "componentVersionId.$": "$.componentVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "SetupTestEnvironmentResponse",
            },
        )

        setup_test_environment.add_catch(complete_component_version_test, result_path="$.error")

        # Check Test Environment Setup Status Task
        check_test_environment_setup_status: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CheckTestEnvironmentSetupStatus",
            lambda_function=component_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CheckTestEnvironmentSetupStatusRequest",
                    "componentVersionId.$": "$.componentVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "CheckTestEnvironmentSetupStatusResponse",
                "setupCommandsStatus.$": "$.Payload.setupCommandsStatus",
            },
        )

        check_test_environment_setup_status.add_catch(complete_component_version_test, result_path="$.error")

        # Is Test Environment Setup Choice
        is_test_environment_setup: sfn.Choice = sfn.Choice(self, "IsTestEnvironmentSetup")

        is_test_environment_setup.when(
            sfn.Condition.string_equals(
                "$.testExecutionDetails.setupCommandsStatus",
                "FAILED",
            ),
            next=complete_component_version_test,
        )

        # Wait for Test Environment Setup
        wait_for_test_environment_setup: sfn.Wait = sfn.Wait(
            self,
            "WaitForTestEnvironmentSetup",
            time=sfn.WaitTime.duration(aws_cdk.Duration.seconds(15)),
        )

        # Run Component Version Test Task
        run_component_version_test: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "RunComponentVersionTest",
            lambda_function=component_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "RunComponentVersionTestRequest",
                    "componentId.$": "$.componentId",
                    "componentVersionId.$": "$.componentVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "RunComponentVersionTestResponse",
            },
        )

        run_component_version_test.add_catch(complete_component_version_test, result_path="$.error")

        # Check Component Version Test Status Task
        check_component_version_test_status: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CheckComponentVersionTestStatus",
            lambda_function=component_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CheckComponentVersionTestStatusRequest",
                    "componentVersionId.$": "$.componentVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "CheckComponentVersionTestStatusResponse",
                "testCommandsStatus.$": "$.Payload.testCommandsStatus",
            },
        )

        check_component_version_test_status.add_catch(complete_component_version_test, result_path="$.error")

        # Is Component Version Test Completed Choice
        is_component_version_test_completed: sfn.Choice = sfn.Choice(self, "IsComponentVersionTestCompleted")

        is_component_version_test_completed.when(
            sfn.Condition.string_equals(
                "$.testExecutionDetails.testCommandsStatus",
                "FAILED",
            ),
            next=complete_component_version_test,
        )

        # Wait for Component Version Test Completed
        wait_for_component_version_test_completed: sfn.Wait = sfn.Wait(
            self,
            "WaitForComponentVersionTestCompleted",
            time=sfn.WaitTime.duration(aws_cdk.Duration.minutes(1)),
        )

        # Log Group
        log_group = aws_logs.LogGroup(
            self,
            "ComponentVersionTestingLogGroup",
            log_group_name=app_config.format_resource_name("component-version-testing-state-machine-log-group"),
            removal_policy=aws_cdk.RemovalPolicy.RETAIN,
            retention=aws_logs.RetentionDays.TWO_MONTHS,
        )

        # State Machine
        self._state_machine: sfn.StateMachine = sfn.StateMachine(
            self,
            "ComponentVersionTestingStateMachine",
            state_machine_name=app_config.format_resource_name("component-version-testing-state-machine"),
            logs=sfn.LogOptions(destination=log_group, level=sfn.LogLevel.ALL),
            tracing_enabled=True,
            definition_body=sfn.DefinitionBody.from_chainable(
                start.next(
                    launch_test_environment.next(
                        check_test_environment_launch_status.next(
                            is_test_environment_launched.when(
                                sfn.Condition.string_equals(
                                    "$.testExecutionDetails.instancesStatus",
                                    "CONNECTED",
                                ),
                                next=setup_test_environment.next(
                                    check_test_environment_setup_status.next(
                                        is_test_environment_setup.when(
                                            sfn.Condition.string_equals(
                                                "$.testExecutionDetails.setupCommandsStatus",
                                                "SUCCESS",
                                            ),
                                            next=run_component_version_test.next(
                                                check_component_version_test_status.next(
                                                    is_component_version_test_completed.when(
                                                        sfn.Condition.string_equals(
                                                            "$.testExecutionDetails.testCommandsStatus",
                                                            "SUCCESS",
                                                        ),
                                                        next=complete_component_version_test,
                                                    ).otherwise(
                                                        wait_for_component_version_test_completed.next(
                                                            check_component_version_test_status,
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ).otherwise(
                                            wait_for_test_environment_setup.next(
                                                check_test_environment_setup_status,
                                            ),
                                        ),
                                    ),
                                ),
                            ).otherwise(
                                wait_for_test_environment_launched.next(
                                    check_test_environment_launch_status,
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

        # cdk-nag Suppressions
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

        state_machine_role_policy = [
            p for p in self._state_machine.role.node.children if isinstance(p, aws_iam.Policy)
        ][0]

        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=state_machine_role_policy,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="This policy is autogenerated by CDK with minimal permissions.",
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
