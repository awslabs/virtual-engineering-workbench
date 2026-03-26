import glob
import os
import shutil
from typing import Callable, Mapping, Optional, Sequence

import cdk_nag
import constructs
from aws_cdk import aws_ecs, aws_iam, aws_logs


class BackendAppTaskDefinition(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        container_name: str,
        task_definition_name: str,
        cpu_architecture: aws_ecs.CpuArchitecture = aws_ecs.CpuArchitecture.ARM64,
        cpu_container: Optional[int] = None,
        cpu_task: int = 256,
        directory: Optional[str] = None,
        environment: Optional[Mapping[str, str]] = None,
        execution_role_name: Optional[str] = None,
        ephemeral_storage_gib: Optional[int] = None,
        image: Optional[str] = None,
        include: Sequence[str] = [],
        log_retention: Optional[aws_logs.RetentionDays] = None,
        memory_limit_mib_container: Optional[int] = None,
        memory_limit_mib_task: int = 512,
        memory_reservation_mib_container: Optional[int] = None,
        operating_system_family: aws_ecs.OperatingSystemFamily = aws_ecs.OperatingSystemFamily.LINUX,
        permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
        privileged: bool = False,
        user: Optional[str] = None,
        task_role_name: Optional[str] = None,
        working_directory: Optional[str] = None,
    ) -> None:
        super().__init__(scope, id)

        self.__task_definition = aws_ecs.FargateTaskDefinition(
            self,
            "BackendAppTaskDefinition",
            cpu=cpu_task,
            ephemeral_storage_gib=ephemeral_storage_gib,
            family=task_definition_name,
            memory_limit_mib=memory_limit_mib_task,
            runtime_platform=aws_ecs.RuntimePlatform(
                cpu_architecture=cpu_architecture,
                operating_system_family=operating_system_family,
            ),
        )
        self.__container_definition = self.__task_definition.add_container(
            "BackendAppContainerDefinition",
            container_name=container_name,
            cpu=cpu_container,
            environment=environment,
            image=(
                # Build image from sources on disk
                aws_ecs.ContainerImage.from_asset(directory=directory)
                if not image
                # Use a pre-built image - Required
                # if Docker bundling not available
                else aws_ecs.ContainerImage.from_registry(name=image)
            ),
            logging=aws_ecs.LogDrivers.aws_logs(
                log_retention=log_retention,
                stream_prefix=task_definition_name,
            ),
            memory_limit_mib=memory_limit_mib_container,
            memory_reservation_mib=memory_reservation_mib_container,
            privileged=privileged,
            user=user,
            working_directory=working_directory,
        )
        if execution_role_name and self.__task_definition.execution_role:
            cfn_execution_role: aws_iam.CfnRole = self.__task_definition.execution_role.node.default_child
            cfn_execution_role.role_name = execution_role_name
        if task_role_name and self.__task_definition.task_role:
            cfn_task_role: aws_iam.CfnRole = self.__task_definition.task_role.node.default_child
            cfn_task_role.role_name = task_role_name
        if directory:
            # The directory f"{directory}/.cdk.staging"
            # is used to share assets with Docker
            # when building image from sources on disk
            staging_directory = f"{directory}/.cdk.staging"

            os.makedirs(staging_directory, exist_ok=True)
            for pattern in include:
                self.include_pattern(
                    pattern=pattern,
                    staging_directory=staging_directory,
                )
        for permission in permissions:
            permission(self.__task_definition)
        self.__apply_nag_suppressions()

    def __apply_nag_suppressions(self):
        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.task_definition,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-ECS2",
                    reason="Environment variables do not contain sensitive data.",
                ),
            ],
        )

        execution_role_policy = [
            _ for _ in self.task_definition.execution_role.node.children if isinstance(_, aws_iam.Policy)
        ][0]

        cdk_nag.NagSuppressions.add_resource_suppressions(
            execution_role_policy,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Policies defined by the aws_ecs.FargateTaskDefinition construct are secure enough.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="Policies defined by the aws_ecs.FargateTaskDefinition construct are secure enough.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="Policies defined by the aws_ecs.FargateTaskDefinition construct are secure enough.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="Policies defined by the aws_ecs.FargateTaskDefinition construct are secure enough.",
                ),
            ],
        )

        log_group = [_ for _ in self.container_definition.node.children if isinstance(_, aws_logs.LogGroup)][0]

        cdk_nag.NagSuppressions.add_resource_suppressions(
            log_group,
            [
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-CloudWatchLogGroupEncrypted",
                    reason="Container logs do not contain sensitive data hence default encryption is sufficient.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-CloudWatchLogGroupRetentionPeriod",
                    reason="Container logs can be preserved for an infinite amount of time.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-CloudWatchLogGroupEncrypted",
                    reason="Container logs do not contain sensitive data hence default encryption is sufficient.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-CloudWatchLogGroupRetentionPeriod",
                    reason="Container logs can be preserved for an infinite amount of time.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-CloudWatchLogGroupEncrypted",
                    reason="Container logs do not contain sensitive data hence default encryption is sufficient.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-CloudWatchLogGroupRetentionPeriod",
                    reason="Container logs can be preserved for an infinite amount of time.",
                ),
            ],
        )

        task_role_policy = [_ for _ in self.task_definition.task_role.node.children if isinstance(_, aws_iam.Policy)][0]

        cdk_nag.NagSuppressions.add_resource_suppressions(
            task_role_policy,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason="Policies defined by the aws_ecs.FargateTaskDefinition construct are secure enough.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="Policies defined by the aws_ecs.FargateTaskDefinition construct are secure enough.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="Policies defined by the aws_ecs.FargateTaskDefinition construct are secure enough.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="Policies defined by the aws_ecs.FargateTaskDefinition construct are secure enough.",
                ),
            ],
        )

    @property
    def container_definition(self) -> aws_ecs.ContainerDefinition:
        return self.__container_definition

    @property
    def task_definition(self) -> aws_ecs.FargateTaskDefinition:
        return self.__task_definition

    def include_pattern(self, pattern: str, staging_directory: str) -> None:
        for item in glob.glob(pattern, recursive=True):
            relative_path = os.path.relpath(item, os.path.dirname(pattern))
            target_path = os.path.join(
                staging_directory,
                os.path.dirname(pattern),
                relative_path,
            )

            if os.path.isdir(item):
                os.makedirs(target_path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(item, target_path)
