from typing import Any, Optional, Sequence, Union

import cdk_nag
import constructs
from aws_cdk import RemovalPolicy, Stack, aws_s3


class Bucket(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        bucket_name: str,
        auto_delete_objects: Optional[bool] = False,
        cors: Optional[Sequence[Union[aws_s3.CorsRule, dict[str, Any]]]] = None,
        encryption: Optional[aws_s3.BucketEncryption] = aws_s3.BucketEncryption.S3_MANAGED,
        encryption_key=None,
        force_bucket_name_uniqueness: Optional[bool] = True,
        lifecycle_rules: Optional[Sequence[Union[aws_s3.LifecycleRule, dict[str, Any]]]] = None,
        removal_policy: Optional[RemovalPolicy] = RemovalPolicy.RETAIN,
        server_access_logs_bucket=None,
        server_access_logs_prefix: Optional[str] = None,
        versioned: Optional[bool] = True,
    ) -> None:
        super().__init__(scope, id)

        self.__bucket = aws_s3.Bucket(
            self,
            "Bucket",
            auto_delete_objects=auto_delete_objects,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            bucket_name=(
                "-".join([bucket_name, Stack.of(self).account, Stack.of(self).region])
                if force_bucket_name_uniqueness
                else bucket_name
            ),
            cors=cors,
            encryption=aws_s3.BucketEncryption.KMS if encryption_key else encryption,
            encryption_key=encryption_key,
            enforce_ssl=True,
            lifecycle_rules=lifecycle_rules,
            removal_policy=removal_policy,
            server_access_logs_bucket=server_access_logs_bucket,
            server_access_logs_prefix=server_access_logs_prefix,
            versioned=versioned,
        )

        self.__apply_nag_suppressions()

    @property
    def bucket(self) -> aws_s3.Bucket:
        return self.__bucket

    def __apply_nag_suppressions(self):
        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.bucket,
            [
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason="This use case does not require server access logging.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-S3BucketLoggingEnabled",
                    reason="This use case does not require server access logging.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-S3BucketDefaultLockEnabled",
                    reason="This use case does not require object lock.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-S3BucketReplicationEnabled",
                    reason="This use case does not require replication.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-S3BucketLoggingEnabled",
                    reason="This use case does not require server access logging.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-S3BucketReplicationEnabled",
                    reason="This use case does not require replication.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-S3DefaultEncryptionKMS",
                    reason="Managed S3 encryption is sufficient for this use case.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-S3BucketLoggingEnabled",
                    reason="This use case does not require server access logging.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-S3BucketReplicationEnabled",
                    reason="This use case does not require replication.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-S3DefaultEncryptionKMS",
                    reason="Managed S3 encryption is sufficient for this use case.",
                ),
            ],
        )
