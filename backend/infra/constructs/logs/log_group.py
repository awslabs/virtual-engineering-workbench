from typing import Callable, Optional, Sequence

import constructs
from aws_cdk import ArnFormat, RemovalPolicy, Stack, aws_iam, aws_kms, aws_logs

from infra.constructs.kms import key


class LogGroup(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        log_group_name: str,
        create_key: Optional[bool] = False,
        data_protection_policy: Optional[aws_logs.DataProtectionPolicy] = None,
        encryption_key: Optional[aws_kms.IKey] = None,
        log_group_class: Optional[aws_logs.LogGroupClass] = aws_logs.LogGroupClass.STANDARD,
        key_permissions: Sequence[Callable[[aws_iam.IGrantable], aws_iam.Grant]] = [],
        removal_policy: Optional[RemovalPolicy] = RemovalPolicy.RETAIN,
        retention: Optional[aws_logs.RetentionDays] = aws_logs.RetentionDays.INFINITE,
    ) -> None:
        super().__init__(scope, id)

        self.__key = None
        if create_key:
            self.__key = key.Key(
                self,
                "Key",
                alias=f"{log_group_name}-key",
                description=f"Key used to encrypt/decrypt {log_group_name} logs.",
                permissions=key_permissions,
            )
            encryption_key = self.__key.key
        self.__log_group = aws_logs.LogGroup(
            self,
            "LogGroup",
            data_protection_policy=data_protection_policy,
            encryption_key=encryption_key,
            log_group_class=log_group_class,
            log_group_name=log_group_name,
            removal_policy=removal_policy,
            retention=retention,
        )

        if encryption_key:
            encryption_key.grant_encrypt_decrypt(
                aws_iam.ServicePrincipal(
                    conditions={
                        "ArnEquals": {
                            "kms:EncryptionContext:aws:logs:arn": Stack.of(self).format_arn(
                                account=Stack.of(self).account,
                                arn_format=ArnFormat.COLON_RESOURCE_NAME,
                                partition=Stack.of(self).partition,
                                region=Stack.of(self).region,
                                resource="log-group",
                                resource_name=log_group_name,
                                service="logs",
                            ),
                        },
                    },
                    service=f"logs.{Stack.of(self).url_suffix}",
                )
            )

    @property
    def log_group(self) -> aws_logs.LogGroup:
        return self.__log_group

    @property
    def key(self) -> Optional[key.Key]:
        return self.__key
