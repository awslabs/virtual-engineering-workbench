import os
import subprocess
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_ec2, aws_iam, aws_lambda, aws_sqs
from jsii import implements, member

from infra import constants
from infra.constructs.bundling import DOCKER_STRIP_CMD, strip_bundle


def _validate_path(path: str) -> None:
    if ".." in Path(path).parts:
        raise ValueError(f"Path traversal detected: {path}")


@implements(aws_cdk.ILocalBundling)
class LocalBundler:
    def __init__(self, app_root: str, lambda_root: str) -> None:
        _validate_path(app_root)
        _validate_path(lambda_root)
        self.__app_root = app_root
        self.__lambda_root = lambda_root
        self.__requirements_file = f"{self.__lambda_root}/requirements.txt"

    @member(jsii_name="tryBundle")
    def try_bundle(self, output_dir: str, options: aws_cdk.BundlingOptions) -> bool:
        if not constants.LOCAL_BUNDLING:
            return False

        requirements_file = Path(self.__requirements_file)

        try:
            if requirements_file.is_file():
                subprocess.run(
                    ["pip", "install", "-r", str(requirements_file), "-t", output_dir, "--no-compile"],
                    check=True,
                    shell=False,
                    capture_output=True,
                    timeout=300,
                )

            subprocess.run(
                [
                    "rsync",
                    "-r",
                    f"{self.__lambda_root}",
                    f"{output_dir}/{self.__app_root}/",
                ],
                check=True,
                shell=False,
                capture_output=True,
                timeout=60,
            )

            strip_bundle(Path(output_dir))
        except subprocess.CalledProcessError as e:
            print(f"Bundle command failed: {e.stderr if e.stderr else ''}")
            return False
        except subprocess.TimeoutExpired:
            print("Bundle command timed out")
            return False

        return True


class BackendAppFunction(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        entry: str,
        app_root: str,
        lambda_root: str,
        layers: Sequence[aws_lambda.ILayerVersion],
        function_name: str,
        reserved_concurrency: Optional[int] = None,
        provisioned_concurrency: Optional[int] = None,
        runtime: aws_lambda.Runtime = aws_lambda.Runtime.PYTHON_3_13,
        handler: str = "handler",
        handler_filename: str = "handler.py",
        environment: Optional[Mapping[str, str]] = None,
        permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
        timeout: Optional[aws_cdk.Duration] = aws_cdk.Duration.seconds(3),
        memory_size: Optional[int] = 128,
        asynchronous: bool = False,
        asynchronous_retries: int = 2,
        vpc_id: Optional[str] = None,
        vpc_name: Optional[str] = None,
        local_bundling: bool = True,
        durable_execution_enabled: bool = False,
    ) -> None:
        super().__init__(scope, id)

        _validate_path(entry)
        _validate_path(app_root)
        _validate_path(lambda_root)

        hash_path = lambda_root
        if not hash_path.startswith("./"):
            hash_path = f"./{hash_path}"

        asset_hash = aws_cdk.FileSystem.fingerprint(hash_path)

        current_dir = "."
        code = aws_lambda.Code.from_asset(
            path=current_dir,
            bundling=aws_cdk.BundlingOptions(
                image=runtime.bundling_image,
                command=[
                    "bash",
                    "-c",
                    f"rsync -r {lambda_root} /asset-output/{app_root}/ && {DOCKER_STRIP_CMD}",
                ],
                local=(
                    LocalBundler(
                        app_root=app_root,
                        lambda_root=lambda_root,
                    )
                    if local_bundling
                    else None
                ),
            ),
            asset_hash=asset_hash,
            asset_hash_type=aws_cdk.AssetHashType.CUSTOM,
        )

        self._dlq = None
        if asynchronous:
            self._dlq = aws_sqs.Queue(
                self,
                f"{function_name}-dlq",
                queue_name=f"{function_name}-dlq",
                encryption=aws_sqs.QueueEncryption.KMS_MANAGED,
            )

            self._dlq.add_to_resource_policy(
                aws_iam.PolicyStatement(
                    sid="Enforce TLS for all principals",
                    effect=aws_iam.Effect.DENY,
                    principals=[
                        aws_iam.AnyPrincipal(),
                    ],
                    actions=[
                        "sqs:*",
                    ],
                    conditions={
                        "Bool": {"aws:secureTransport": "false"},
                    },
                    resources=[self._dlq.queue_arn],
                )
            )

            # cdk_nag suppressions
            cdk_nag.NagSuppressions.add_resource_suppressions(
                construct=self._dlq,
                suppressions=[
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-SQS3",
                        reason="This is already a dead-letter-queue.",
                    ),
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-SQS4",
                        reason="False positive: resource policy denies non-tls encrypted traffic.",
                    ),
                ],
            )

        vpc = None
        security_group = None

        if vpc_id:
            vpc = aws_ec2.Vpc.from_lookup(self, "vpc", vpc_id=vpc_id)
            security_group = aws_ec2.SecurityGroup(self, "lambda-sg", vpc=vpc)
        elif vpc_name:
            vpc = aws_ec2.Vpc.from_lookup(self, "vpc", vpc_name=vpc_name)
            security_group = aws_ec2.SecurityGroup(self, "lambda-sg", vpc=vpc)

        self._func = aws_lambda.Function(
            self,
            "BackendAppFunction",
            code=code,
            runtime=runtime,
            handler=f"{entry}/{os.path.splitext(handler_filename)[0]}.{handler}",
            layers=layers,
            function_name=function_name,
            environment=environment,
            tracing=aws_lambda.Tracing.ACTIVE,
            reserved_concurrent_executions=reserved_concurrency,
            timeout=timeout,
            memory_size=memory_size,
            current_version_options=aws_lambda.VersionOptions(
                removal_policy=aws_cdk.RemovalPolicy.RETAIN,
            ),
            architecture=constants.LAMBDA_ARCHITECTURE,
            dead_letter_queue_enabled=asynchronous,
            dead_letter_queue=self._dlq,
            retry_attempts=asynchronous_retries if asynchronous else None,
            description=f"{asset_hash[:5]}",
            security_groups=[security_group] if security_group else None,
            vpc=vpc,
            vpc_subnets={"subnets": vpc.private_subnets} if vpc else None,
        )

        # Configure durable execution if enabled
        if durable_execution_enabled:
            cfn_function: aws_lambda.CfnFunction = self._func.node.default_child
            cfn_function.durable_config = aws_lambda.CfnFunction.DurableConfigProperty(
                execution_timeout=timeout.to_seconds() if timeout else 900
            )

        self._func_alias = self._func.add_alias(
            alias_name=constants.LAMBDA_ALIAS_NAME,
            provisioned_concurrent_executions=provisioned_concurrency,
        )

        if self._func.role:
            cfn_role: aws_iam.CfnRole = self._func.role.node.default_child
            cfn_role.role_name = function_name

        for p in permissions:
            p(self._func)

        # cdk_nag suppressions
        # function suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=self._func,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-LambdaInsideVPC",
                    reason="It is not required to enable VPC for Lambda.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaInsideVPC",
                    reason="It is not required to enable VPC for Lambda.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-LambdaInsideVPC",
                    reason="It is not required to enable VPC for Lambda.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaDLQ",
                    reason="DLQ is not required since all Lambdas are executed synchronously via APIs.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-LambdaConcurrency",
                    reason="Reserved concurrency setting is only used for API lambdas.",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-L1",
                    reason="Python3.13 requires extra testing",
                ),
            ],
        )

        # role suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=self._func.role,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="AWSLambdaBasicExecutionRole is required minimum for Lambda function to run.",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                    ],
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason="Managed policy is autogenerated by CDK.",
                ),
            ],
            apply_to_children=True,
        )

        # policy suppressions
        lambda_role_policy = [p for p in self._func.role.node.children if isinstance(p, aws_iam.Policy)][0]
        cdk_nag.NagSuppressions.add_resource_suppressions(
            construct=lambda_role_policy,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Available xray actions does not support resource based policies.",
                    applies_to=["Resource::*"],
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="Using inline policies are enough for the use case.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="Using inline policies are enough for the use case.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="Using inline policies are enough for the use case.",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="AWS accounts will be dynamically defined in the application, thus not known.",
                    applies_to=[
                        "Resource::arn:aws:iam::*:role/WorkbenchWebApplicationCatalogRole",
                        "Resource::arn:aws:iam::*:role/WorkbenchWebAppProvisioningRole",
                        "Resource::arn:aws:iam::*:role/WorkbenchWebApplicationPipelineCatalogRole",
                        f"Resource::arn:aws:iam::*:role/{constants.PRODUCT_PROVISIONING_ROLE}",
                        "Resource::arn:aws:iam::*:role/ProductPublishingAdminRole",
                        "Resource::arn:aws:iam::*:role/ProductPublishingUseCaseRole",
                        "Resource::arn:aws:iam::*:role/ProductPublishingImageServiceRole",
                        f"Resource::arn:aws:iam::*:role/{constants.PRODUCT_PUBLISHING_ADMIN_ROLE}",
                        f"Resource::arn:aws:iam::*:role/{constants.PRODUCT_PUBLISHING_USE_CASE_ROLE}",
                        f"Resource::arn:aws:iam::*:role/{constants.PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE}",
                        "Resource::arn:aws:iam::*:role/VEWAccountBootstrapRole",
                        "Resource::arn:aws:iam::*:role/VEWDynamicBootstrapRole",
                    ],
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="* is only used for projectId path parameter.",
                    applies_to=[
                        cdk_nag.RegexAppliesTo(
                            regex=r"^Resource::arn:aws:execute-api:.*\/.*\/GET\/projects\/\*\/accounts$/g"
                        ),
                    ],
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="* is needed in order to allow access to all the parameters inside the AppConfig environment",
                    applies_to=[
                        cdk_nag.RegexAppliesTo(
                            regex=r"/^Resource::arn:aws:appconfig:.*:application\/(.*?)\/environment\/(.*?)\/configuration\/\*/gm"
                        )
                    ],
                ),
            ],
        )

    @property
    def function(self) -> aws_lambda.Function:
        return self._func

    @property
    def function_alias(self) -> aws_lambda.Alias:
        return self._func_alias

    @property
    def dead_letter_queue(self) -> Optional[aws_sqs.IQueue]:
        return self._dlq
