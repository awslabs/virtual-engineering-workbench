import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_iam, aws_lambda, aws_logs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks

from infra import config


class AmiSharingStateMachine(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        ami_sharing_lambda: aws_lambda.Function,
    ) -> None:
        """
        Sample expected input for the state machine:
        {
            "version": "0",
            "id": "a0fd2d09-02c3-1696-1cee-406e4cc14c86",
            "detail-type": "ProductVersionCreationStarted",
            "source": "proserve.workbench.publishing.dev",
            "account": "111111111111",
            "time": "2023-08-01T14:18:48Z",
            "region": "us-east-1",
            "resources": [],
            "detail": {
                "eventName": "ProductVersionCreationStarted",
                "productId": "prod-dt3ycosm",
                "versionId": "vers-1vbc9box",
                "awsAccountId": "222222222222",
                "oldVersionId": "vers-12345abc"  # Only in ProductVersionRestorationStarted
                "productType": "VIRTUAL_TARGET"
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

        # Pass states for storing copied ami id
        pass_copy: sfn.Pass = sfn.Pass(
            self, "PassCopy", parameters={"copiedAmiId.$": "$.copyAmiResponse.copiedAmiId"}, result_path="$.copiedAmi"
        )
        pass_share: sfn.Pass = sfn.Pass(
            self,
            "PassShare",
            parameters={"copiedAmiId.$": "$.decideActionResponse.originalAmiId"},
            result_path="$.copiedAmi",
        )
        pass_done: sfn.Pass = sfn.Pass(
            self,
            "PassDone",
            parameters={"copiedAmiId.$": "$.decideActionResponse.copiedAmiId"},
            result_path="$.copiedAmi",
        )

        # Pass state for assigning old version id
        pass_assign_old_version_id: sfn.Pass = sfn.Pass(
            self,
            "PassAssignOldVersionId",
            parameters={
                "eventName.$": "$.eventName",
                "productId.$": "$.productId",
                "versionId.$": "$.versionId",
                "awsAccountId.$": "$.awsAccountId",
                "oldVersionId": "",
            },
            result_path="$.PassOldVersionIdResponse",
        )

        # Pass state for doing nothing in case oldVersionId is already assigned
        # Special thanks to how state machines work
        pass_skip_old_version_id: sfn.Pass = sfn.Pass(
            self,
            "PassSkipOldVersionId",
            parameters={
                "eventName.$": "$.eventName",
                "productId.$": "$.productId",
                "versionId.$": "$.versionId",
                "awsAccountId.$": "$.awsAccountId",
                "oldVersionId": "$.oldVersionId",
            },
            result_path="$.PassOldVersionIdResponse",
        )

        # Synthetic $.error for the Choice branches that end in failure. A task failure
        # populates $.error through add_catch; a Choice taking its otherwise branch does
        # not, so each one sets its own reason before FailAmiSharingLambda, which now
        # reads $.error unconditionally.
        pass_unexpected_decision_error: sfn.Pass = sfn.Pass(
            self,
            "PassUnexpectedDecisionError",
            parameters={
                "Error": "UnexpectedDecision",
                "Cause": "DecideAction returned a decision this state machine does not handle.",
            },
            result_path="$.error",
        )
        pass_grant_not_verified_error: sfn.Pass = sfn.Pass(
            self,
            "PassGrantNotVerifiedError",
            parameters={
                "Error": "LicenseGrantNotVerified",
                "Cause": "The target account has no active license grant for this Marketplace product.",
            },
            result_path="$.error",
        )
        pass_launch_permission_denied_error: sfn.Pass = sfn.Pass(
            self,
            "PassLaunchPermissionDeniedError",
            parameters={
                "Error": "LaunchPermissionDenied",
                "Cause": "The target account cannot launch the regional Marketplace AMI.",
            },
            result_path="$.error",
        )

        # Fail ami sharing lambda
        fail_ami_sharing_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "FailAmiSharingLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "FailAmiSharingRequest",
                    "productId.$": "$.productId",
                    "versionId.$": "$.versionId",
                    "awsAccountId.$": "$.awsAccountId",
                    # Every route into this state sets $.error: a task failure through
                    # add_catch(result_path="$.error"), and each Choice branch through
                    # its own Pass below. Without it the reason a share failed was
                    # dropped here and the version showed a bare Failed status.
                    "error.$": "$.error",
                }
            ),
            result_selector={"eventType.$": "$.Payload.eventType"},
            result_path="$.failAmiSharingResponse",
        )

        # Decide action lambda
        decide_action_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "DecideActionLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "DecideActionRequest",
                    "productId.$": "$.productId",
                    "versionId.$": "$.versionId",
                    "awsAccountId.$": "$.awsAccountId",
                    "productType.$": "$.productType",
                }
            ),
            result_selector={
                "eventType.$": "$.Payload.eventType",
                "decision.$": "$.Payload.decision",
                "originalAmiId.$": "$.Payload.originalAmiId",
                "copiedAmiId.$": "$.Payload.copiedAmiId",
                "region.$": "$.Payload.region",
                "imageId.$": "$.Payload.imageId",
                "projectId.$": "$.Payload.projectId",
                "licenseArn.$": "$.Payload.licenseArn",
                "homeRegion.$": "$.Payload.homeRegion",
                "grantName.$": "$.Payload.grantName",
            },
            result_path="$.decideActionResponse",
        )
        decide_action_lambda.add_catch(fail_ami_sharing_lambda, result_path="$.error")

        # Copy ami lambda
        copy_ami_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CopyAmiLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CopyAmiRequest",
                    "originalAmiId.$": "$.decideActionResponse.originalAmiId",
                    "region.$": "$.decideActionResponse.region",
                }
            ),
            result_selector={
                "eventType.$": "$.Payload.eventType",
                "copiedAmiId.$": "$.Payload.copiedAmiId",
            },
            result_path="$.copyAmiResponse",
        )
        copy_ami_lambda.add_catch(fail_ami_sharing_lambda, result_path="$.error")

        # Verify copy lambda
        verify_copy_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "VerifyCopyLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "VerifyCopyRequest",
                    "region.$": "$.decideActionResponse.region",
                    "copiedAmiId.$": "$.copiedAmi.copiedAmiId",
                }
            ),
            result_selector={
                "eventType.$": "$.Payload.eventType",
                "isCopyVerified.$": "$.Payload.isCopyVerified",
            },
            result_path="$.verifyCopyResponse",
        )
        verify_copy_lambda.add_catch(fail_ami_sharing_lambda, result_path="$.error")

        # Create license grant lambda
        create_license_grant_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "CreateLicenseGrantLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "CreateLicenseGrantRequest",
                    "productId.$": "$.productId",
                    "versionId.$": "$.versionId",
                    "awsAccountId.$": "$.awsAccountId",
                    "imageId.$": "$.decideActionResponse.imageId",
                    "grantName.$": "$.decideActionResponse.grantName",
                    "projectId.$": "$.decideActionResponse.projectId",
                }
            ),
            result_selector={
                "eventType.$": "$.Payload.eventType",
                "grantId.$": "$.Payload.grantId",
                "grantArn.$": "$.Payload.grantArn",
                "homeRegion.$": "$.Payload.homeRegion",
            },
            result_path="$.createLicenseGrantResponse",
        )
        create_license_grant_lambda.add_catch(fail_ami_sharing_lambda, result_path="$.error")

        # Accept license grant lambda
        accept_license_grant_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "AcceptLicenseGrantLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "AcceptLicenseGrantRequest",
                    "grantId.$": "$.createLicenseGrantResponse.grantId",
                    "grantArn.$": "$.createLicenseGrantResponse.grantArn",
                    "homeRegion.$": "$.createLicenseGrantResponse.homeRegion",
                    "awsAccountId.$": "$.awsAccountId",
                    "projectId.$": "$.decideActionResponse.projectId",
                }
            ),
            result_selector={
                "eventType.$": "$.Payload.eventType",
            },
            result_path="$.acceptLicenseGrantResponse",
        )
        # Retry accept: grant distribution from hub to spoke is async — the grant may not
        # be visible in the spoke's ListReceivedGrants immediately after CreateGrant returns.
        accept_license_grant_lambda.add_retry(
            max_attempts=3,
            interval=aws_cdk.Duration.seconds(10),
        )
        accept_license_grant_lambda.add_catch(fail_ami_sharing_lambda, result_path="$.error")

        # Verify launch permission lambda (shared by LICENSE_GRANT and VERIFY_EXTERNAL_GRANT paths)
        verify_launch_permission_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "VerifyLaunchPermissionLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "VerifyLicenseGrantRequest",
                    "amiId.$": "$.decideActionResponse.imageId",
                    "region.$": "$.decideActionResponse.region",
                    "awsAccountId.$": "$.awsAccountId",
                }
            ),
            result_selector={
                "eventType.$": "$.Payload.eventType",
                "launchPermissionVerified.$": "$.Payload.isAccessible",
            },
            result_path="$.verifyLaunchPermissionResponse",
            retry_on_service_exceptions=False,
        )
        verify_launch_permission_lambda.add_retry(
            max_attempts=3,
            interval=aws_cdk.Duration.seconds(30),
        )
        verify_launch_permission_lambda.add_catch(fail_ami_sharing_lambda, result_path="$.error")

        # Verify external grant lambda
        verify_external_grant_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "VerifyExternalGrantLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "VerifyExternalGrantRequest",
                    "productId.$": "$.productId",
                    "versionId.$": "$.versionId",
                    "awsAccountId.$": "$.awsAccountId",
                    "amiId.$": "$.decideActionResponse.imageId",
                    "region.$": "$.decideActionResponse.region",
                    "licenseArn.$": "$.decideActionResponse.licenseArn",
                    "homeRegion.$": "$.decideActionResponse.homeRegion",
                }
            ),
            result_selector={
                "eventType.$": "$.Payload.eventType",
                "grantVerified.$": "$.Payload.grantVerified",
            },
            result_path="$.verifyExternalGrantResponse",
        )
        verify_external_grant_lambda.add_catch(fail_ami_sharing_lambda, result_path="$.error")

        # Verify external grant choice
        verify_external_grant_choice: sfn.Choice = sfn.Choice(self, "VerifyExternalGrantChoice")
        verify_external_grant_choice.when(
            sfn.Condition.boolean_equals("$.verifyExternalGrantResponse.grantVerified", True),
            verify_launch_permission_lambda,
        )
        verify_external_grant_choice.otherwise(pass_grant_not_verified_error)

        # Launch permission choice. VerifyLaunchPermissionLambda reports whether the
        # spoke can actually launch the regional AMI, and previously nothing read the
        # answer: both Marketplace paths ran straight on to SucceedAmiSharing, so a
        # spoke that could not launch the image was recorded as shared successfully.
        verify_launch_permission_choice: sfn.Choice = sfn.Choice(self, "VerifyLaunchPermissionChoice")

        # Pass state for the Marketplace paths' copied-ami placeholder. SucceedAmiSharing
        # reads $.copiedAmi.copiedAmiId, and on the verify-external-grant path nothing set
        # it, so that path could never complete. Both Marketplace paths record the REGIONAL
        # AMI, which is the image the spoke launches.
        pass_marketplace_ami: sfn.Pass = sfn.Pass(
            self,
            "PassMarketplaceAmi",
            parameters={"copiedAmiId.$": "$.decideActionResponse.imageId"},
            result_path="$.copiedAmi",
        )

        # Pass state for license grant path to set copiedAmi placeholder
        pass_license_grant: sfn.Pass = sfn.Pass(
            self,
            "PassLicenseGrant",
            parameters={"copiedAmiId.$": "$.decideActionResponse.originalAmiId"},
            result_path="$.copiedAmi",
        )
        # NOTE: both Marketplace paths overwrite $.copiedAmi with the regional AMI at
        # PassMarketplaceAmi after the launch-permission check, so this placeholder only
        # covers the states in between.

        # Share ami lambda
        share_ami_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "ShareAmiLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "ShareAmiRequest",
                    "originalAmiId.$": "$.decideActionResponse.originalAmiId",
                    "copiedAmiId.$": "$.copiedAmi.copiedAmiId",
                    "region.$": "$.decideActionResponse.region",
                    "awsAccountId.$": "$.awsAccountId",
                }
            ),
            result_selector={"eventType.$": "$.Payload.eventType"},
            result_path="$.shareAmiResponse",
        )
        share_ami_lambda.add_catch(fail_ami_sharing_lambda, result_path="$.error")

        # Succeed ami sharing lambda
        succeed_ami_sharing_lambda: sfn_tasks.LambdaInvoke = sfn_tasks.LambdaInvoke(
            self,
            "SucceedAmiSharingLambda",
            lambda_function=ami_sharing_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "eventType": "SucceedAmiSharingRequest",
                    "productId.$": "$.productId",
                    "versionId.$": "$.versionId",
                    "awsAccountId.$": "$.awsAccountId",
                    "copiedAmiId.$": "$.copiedAmi.copiedAmiId",
                    "previousEventName.$": "$.eventName",
                    "oldVersionId.$": "$.PassOldVersionIdResponse.oldVersionId",
                    "productType.$": "$.productType",
                }
            ),
            result_selector={"eventType.$": "$.Payload.eventType"},
            result_path="$.succeedAmiSharingResponse",
        )
        succeed_ami_sharing_lambda.add_catch(fail_ami_sharing_lambda, result_path="$.error")

        # Wait for verifying copy
        verify_copy_wait: sfn.Wait = sfn.Wait(
            self, "VerifyCopyWait", time=sfn.WaitTime.duration(aws_cdk.Duration.seconds(30))
        )

        # Check old version id choice
        check_old_version_id_choice: sfn.Choice = sfn.Choice(self, "CheckOldVersionIdChoice")
        check_old_version_id_choice.when(sfn.Condition.is_not_present("$.oldVersionId"), pass_assign_old_version_id)
        check_old_version_id_choice.otherwise(pass_skip_old_version_id)

        # Verify copy choice
        verify_copy_choice: sfn.Choice = sfn.Choice(self, "VerifyCopyChoice")
        verify_copy_choice.when(
            sfn.Condition.boolean_equals("$.verifyCopyResponse.isCopyVerified", True), share_ami_lambda
        )
        verify_copy_choice.otherwise(verify_copy_wait)
        verify_copy_wait.next(verify_copy_lambda)

        # Define the 3 chains: COPY/SHARE/DONE
        chain_copy = (
            sfn.Chain.start(copy_ami_lambda)
            .next(pass_copy)
            .next(verify_copy_lambda)
            .next(verify_copy_choice.afterwards())
        )
        chain_share = sfn.Chain.start(pass_share).next(share_ami_lambda)
        chain_done = sfn.Chain.start(pass_done)

        # LICENSE_GRANT chain: CreateLicenseGrant → AcceptLicenseGrant →
        # VerifyLaunchPermission → Choice(launchPermissionVerified?)
        chain_license_grant = (
            sfn.Chain.start(pass_license_grant)
            .next(create_license_grant_lambda)
            .next(accept_license_grant_lambda)
            .next(verify_launch_permission_lambda)
            .next(verify_launch_permission_choice.afterwards(include_otherwise=False))
        )

        # VERIFY_EXTERNAL_GRANT chain: VerifyExternalGrant → Choice(grantVerified?) →
        # VerifyLaunchPermission → Choice(launchPermissionVerified?)
        chain_verify_external_grant = sfn.Chain.start(verify_external_grant_lambda).next(
            verify_external_grant_choice.afterwards(include_otherwise=False)
        )

        # Both Marketplace paths converge here: record the regional AMI, then succeed.
        verify_launch_permission_choice.when(
            sfn.Condition.boolean_equals("$.verifyLaunchPermissionResponse.launchPermissionVerified", True),
            pass_marketplace_ami,
        )
        verify_launch_permission_choice.otherwise(pass_launch_permission_denied_error)

        pass_grant_not_verified_error.next(fail_ami_sharing_lambda)
        pass_launch_permission_denied_error.next(fail_ami_sharing_lambda)
        pass_unexpected_decision_error.next(fail_ami_sharing_lambda)
        fail_ami_sharing_lambda.next(fail_state)

        # Decide action choice
        decide_action_choice: sfn.Choice = sfn.Choice(self, "DecideActionChoice")
        decide_action_choice.when(sfn.Condition.string_equals("$.decideActionResponse.decision", "COPY"), chain_copy)
        decide_action_choice.when(sfn.Condition.string_equals("$.decideActionResponse.decision", "SHARE"), chain_share)
        decide_action_choice.when(sfn.Condition.string_equals("$.decideActionResponse.decision", "DONE"), chain_done)
        decide_action_choice.when(
            sfn.Condition.string_equals("$.decideActionResponse.decision", "NOT_REQUIRED"), chain_done
        )
        decide_action_choice.when(
            sfn.Condition.string_equals("$.decideActionResponse.decision", "LICENSE_GRANT"), chain_license_grant
        )
        decide_action_choice.when(
            sfn.Condition.string_equals("$.decideActionResponse.decision", "VERIFY_EXTERNAL_GRANT"),
            chain_verify_external_grant,
        )
        decide_action_choice.otherwise(pass_unexpected_decision_error)

        # Define log group
        log_group = aws_logs.LogGroup(
            self,
            "AmiSharingStateMachineLogGroup",
            log_group_name=app_config.format_resource_name("ami-sharing-state-machine-log-group"),
            removal_policy=aws_cdk.RemovalPolicy.RETAIN,
            retention=aws_logs.RetentionDays.TWO_MONTHS,
        )

        # Define the state machine
        self._state_machine: sfn.StateMachine = sfn.StateMachine(
            self,
            "AmiSharingStateMachine",
            state_machine_name=app_config.format_resource_name("ami-sharing-state-machine"),
            logs=sfn.LogOptions(destination=log_group, level=sfn.LogLevel.ALL),
            tracing_enabled=True,
            definition_body=sfn.DefinitionBody.from_chainable(
                sfn.Chain.start(start_state)
                .next(check_old_version_id_choice.afterwards())
                .next(decide_action_lambda)
                .next(decide_action_choice.afterwards())
                .next(succeed_ami_sharing_lambda)
                .next(success_state)
            ),
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

        state_machine_role_policy = [
            p for p in self._state_machine.role.node.children if isinstance(p, aws_iam.Policy)
        ][0]
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=state_machine_role_policy,
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
