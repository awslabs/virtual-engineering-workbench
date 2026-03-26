from typing import Callable, Optional, Sequence

import cdk_nag
import constructs
from aws_cdk import Duration, aws_iam


class Role(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        assumed_by: aws_iam.IPrincipal,
        role_name: str,
        description: Optional[str] = None,
        instance_profile_name: Optional[str] = None,
        managed_policies: Optional[Sequence[aws_iam.IManagedPolicy]] = None,
        max_session_duration: Optional[Duration] = Duration.hours(1),
        path: Optional[str] = "/",
        permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
    ) -> None:
        super().__init__(scope, id)

        self.__instance_profile = None
        self.__role = aws_iam.Role(
            self,
            "Role",
            assumed_by=assumed_by,
            description=description,
            managed_policies=managed_policies,
            max_session_duration=max_session_duration,
            path=path,
            role_name=role_name,
        )
        if instance_profile_name:
            self.__instance_profile = aws_iam.InstanceProfile(
                self,
                "InstanceProfile",
                instance_profile_name=instance_profile_name,
                path=path,
                role=self.__role,
            )

        for permission in permissions:
            permission(self.__role)
        self.__apply_nag_suppressions()

    @property
    def instance_profile(self) -> Optional[aws_iam.InstanceProfile]:
        return self.__instance_profile

    @property
    def role(self) -> aws_iam.Role:
        return self.__role

    def __apply_nag_suppressions(self):
        role_policy = next((_ for _ in self.role.node.children if isinstance(_, aws_iam.Policy)), None)

        if role_policy is None:
            return

        cdk_nag.NagSuppressions.add_resource_suppressions(
            role_policy,
            [
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="Usage of inline policies is allowed for this use case.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="Usage of inline policies is allowed for this use case.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="Usage of inline policies is allowed for this use case.",
                ),
            ],
        )
