import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_iam, aws_lambda, aws_logs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks

from infra import config


class RecipeVersionTestingStateMachine(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        recipe_version_testing_lambda: aws_lambda.Function,
    ) -> None:
        """
        Sample expected input for the state machine:
        {
            "version": "0",
            "id": "0be91e9a-caed-4c4c-8072-f7c203cea24e",
            "detail-type": "RecipeVersionPublished",
            "source": "proserve.wb.packaging.dev",
            "account": "123456789012",
            "time": "2023-08-01T14:18:48Z",
            "region": "us-east-1",
            "resources": [],
            "detail": {
                "eventName": "RecipeVersionPublished",
                "projectId": "proj-12345",
                "recipeId": "reci-12345abc",
                "recipeVersionId": "version-12345abc",
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

        # Has Recipee Version Test Succeeded Choice
        has_recipe_version_test_succeeded: sfn.Choice = sfn.Choice(self, "HasRecipeVersionTestSucceeded")

        has_recipe_version_test_succeeded.when(
            sfn.Condition.string_equals(
                "$.testExecutionDetails.recipeVersionTestStatus",
                "SUCCESS",
            ),
            success,
        )
        has_recipe_version_test_succeeded.otherwise(fail)

        # Complete Recipe Version Test Task
        complete_recipe_version_test: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CompleteRecipeVersionTest",
            lambda_function=recipe_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CompleteRecipeVersionTestRequest",
                    "projectId.$": "$.projectId",
                    "recipeId.$": "$.recipeId",
                    "recipeVersionId.$": "$.recipeVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "CompleteRecipeVersionTestResponse",
                "recipeVersionTestStatus.$": "$.Payload.recipeVersionTestStatus",
            },
        )

        complete_recipe_version_test.add_catch(fail)
        complete_recipe_version_test.next(has_recipe_version_test_succeeded)

        # Launch Test Environment Task
        launch_test_environment: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "LaunchTestEnvironment",
            lambda_function=recipe_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "LaunchTestEnvironmentRequest",
                    "projectId.$": "$.projectId",
                    "recipeId.$": "$.recipeId",
                    "recipeVersionId.$": "$.recipeVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "LaunchTestEnvironmentResponse",
            },
        )

        launch_test_environment.add_catch(complete_recipe_version_test, result_path="$.error")

        # Check Test Environment Launch Status Task
        check_test_environment_launch_status: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CheckTestEnvironmentLaunchStatus",
            lambda_function=recipe_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CheckTestEnvironmentLaunchStatusRequest",
                    "recipeVersionId.$": "$.recipeVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "CheckTestEnvironmentLaunchStatusResponse",
                "instanceStatus.$": "$.Payload.instanceStatus",
            },
        )

        check_test_environment_launch_status.add_catch(complete_recipe_version_test, result_path="$.error")

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
            lambda_function=recipe_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "SetupTestEnvironmentRequest",
                    "recipeVersionId.$": "$.recipeVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "SetupTestEnvironmentResponse",
            },
        )

        setup_test_environment.add_catch(complete_recipe_version_test, result_path="$.error")

        # Check Test Environment Setup Status Task
        check_test_environment_setup_status: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CheckTestEnvironmentSetupStatus",
            lambda_function=recipe_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CheckTestEnvironmentSetupStatusRequest",
                    "recipeVersionId.$": "$.recipeVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "CheckTestEnvironmentSetupStatusResponse",
                "setupCommandStatus.$": "$.Payload.setupCommandStatus",
            },
        )

        check_test_environment_setup_status.add_catch(complete_recipe_version_test, result_path="$.error")

        # Is Test Environment Setup Choice
        is_test_environment_setup: sfn.Choice = sfn.Choice(self, "IsTestEnvironmentSetup")

        is_test_environment_setup.when(
            sfn.Condition.string_equals(
                "$.testExecutionDetails.setupCommandStatus",
                "FAILED",
            ),
            next=complete_recipe_version_test,
        )

        # Wait for Test Environment Setup
        wait_for_test_environment_setup: sfn.Wait = sfn.Wait(
            self,
            "WaitForTestEnvironmentSetup",
            time=sfn.WaitTime.duration(aws_cdk.Duration.seconds(15)),
        )

        # Run Recipe Version Test Task
        run_recipe_version_test: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "RunRecipeVersionTest",
            lambda_function=recipe_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "RunRecipeVersionTestRequest",
                    "recipeId.$": "$.recipeId",
                    "recipeVersionId.$": "$.recipeVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "RunRecipeVersionTestResponse",
            },
        )

        run_recipe_version_test.add_catch(complete_recipe_version_test, result_path="$.error")

        # Check Recipe Version Test Status Task
        check_recipe_version_test_status: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CheckRecipeVersionTestStatus",
            lambda_function=recipe_version_testing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CheckRecipeVersionTestStatusRequest",
                    "recipeVersionId.$": "$.recipeVersionId",
                    "testExecutionId.$": "$$.Execution.Input.id",
                }
            ),
            result_path="$.testExecutionDetails",
            result_selector={
                "eventType": "CheckRecipeVersionTestStatusResponse",
                "testCommandStatus.$": "$.Payload.testCommandStatus",
            },
        )

        check_recipe_version_test_status.add_catch(complete_recipe_version_test, result_path="$.error")

        # Is Recipe Version Test Completed Choice
        is_recipe_version_test_completed: sfn.Choice = sfn.Choice(self, "IsRecipeVersionTestCompleted")

        is_recipe_version_test_completed.when(
            sfn.Condition.string_equals(
                "$.testExecutionDetails.testCommandStatus",
                "FAILED",
            ),
            next=complete_recipe_version_test,
        )

        # Wait for Recipe Version Test Completed
        wait_for_recipe_version_test_completed: sfn.Wait = sfn.Wait(
            self,
            "WaitForRecipeVersionTestCompleted",
            time=sfn.WaitTime.duration(aws_cdk.Duration.minutes(1)),
        )

        # Log Group
        log_group = aws_logs.LogGroup(
            self,
            "RecipeVersionTestingLogGroup",
            log_group_name=app_config.format_resource_name("recipe-version-testing-state-machine-log-group"),
            removal_policy=aws_cdk.RemovalPolicy.RETAIN,
            retention=aws_logs.RetentionDays.TWO_MONTHS,
        )

        # State Machine
        self._state_machine: sfn.StateMachine = sfn.StateMachine(
            self,
            "RecipeVersionTestingStateMachine",
            state_machine_name=app_config.format_resource_name("recipe-version-testing-state-machine"),
            logs=sfn.LogOptions(destination=log_group, level=sfn.LogLevel.ALL),
            tracing_enabled=True,
            definition_body=sfn.DefinitionBody.from_chainable(
                start.next(
                    launch_test_environment.next(
                        check_test_environment_launch_status.next(
                            is_test_environment_launched.when(
                                sfn.Condition.string_equals(
                                    "$.testExecutionDetails.instanceStatus",
                                    "CONNECTED",
                                ),
                                next=setup_test_environment.next(
                                    check_test_environment_setup_status.next(
                                        is_test_environment_setup.when(
                                            sfn.Condition.string_equals(
                                                "$.testExecutionDetails.setupCommandStatus",
                                                "SUCCESS",
                                            ),
                                            next=run_recipe_version_test.next(
                                                check_recipe_version_test_status.next(
                                                    is_recipe_version_test_completed.when(
                                                        sfn.Condition.string_equals(
                                                            "$.testExecutionDetails.testCommandStatus",
                                                            "SUCCESS",
                                                        ),
                                                        next=complete_recipe_version_test,
                                                    ).otherwise(
                                                        wait_for_recipe_version_test_completed.next(
                                                            check_recipe_version_test_status,
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
