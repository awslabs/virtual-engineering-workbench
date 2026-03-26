from typing import Callable, Optional, Sequence

import constructs
from aws_cdk import Duration, RemovalPolicy, aws_iam, aws_kms


class Key(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        alias: str,
        description: Optional[str] = None,
        enabled: Optional[bool] = True,
        key_spec: Optional[aws_kms.KeySpec] = aws_kms.KeySpec.SYMMETRIC_DEFAULT,
        key_usage: Optional[aws_kms.KeyUsage] = aws_kms.KeyUsage.ENCRYPT_DECRYPT,
        pending_window: Optional[Duration] = Duration.days(30),
        permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
        removal_policy: Optional[RemovalPolicy] = RemovalPolicy.RETAIN,
        rotation_period: Optional[Duration] = Duration.days(365),
    ) -> None:
        super().__init__(scope, id)

        self.__key = aws_kms.Key(
            self,
            "Key",
            alias=f"alias/{alias}",
            description=description,
            enabled=enabled,
            enable_key_rotation=True,
            key_spec=key_spec,
            key_usage=key_usage,
            pending_window=pending_window,
            removal_policy=removal_policy,
            rotation_period=rotation_period,
        )

        for permission in permissions:
            permission(self.__key)

    @property
    def key(self) -> aws_kms.Key:
        return self.__key
