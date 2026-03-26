import aws_cdk
import cdk_nag
import constructs
from aws_cdk import aws_s3, aws_secretsmanager, aws_ssm

from infra import config, constants
from infra.constructs.eventbridge import eb_upsert


class SharedDeploymentInfrastructure(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        eb_upsert.EBUpsert(
            self,
            "EBUpsert",
            format_resource_name=app_config.format_resource_name,
            environment=app_config.environment,
        )

        audit_logging_key = aws_secretsmanager.Secret(
            self, "audit-logging-key", secret_name=app_config.format_resource_name("audit-logging-key")
        )

        aws_ssm.StringParameter(
            self,
            "audit-logging-secret-arn",
            parameter_name=constants.AUDIT_LOGGING_KEY_ARN_SSM_PARAM_NAME.format(environment=app_config.environment),
            string_value=audit_logging_key.secret_arn,
        )

        aws_ssm.StringParameter(
            self,
            "audit-logging-secret-name",
            parameter_name=constants.AUDIT_LOGGING_KEY_NAME_SSM_PARAM_NAME.format(environment=app_config.environment),
            string_value=audit_logging_key.secret_name,
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            audit_logging_key,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-SMG4",
                    reason="Secret should not be rotated for audit logging.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-SecretsManagerRotationEnabled",
                    reason="Secret should not be rotated for audit logging.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-SecretsManagerUsingKMSKey",
                    reason="Key does not need to be customer managed.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-SecretsManagerUsingKMSKey",
                    reason="Key does not need to be customer managed.",
                ),
            ],
            apply_to_children=True,
        )

        # S3 bucket for access logs
        self.__access_log_bucket = aws_s3.Bucket(
            self,
            "AccessLogBucket",
            bucket_name=app_config.format_resource_name(f"{app_config.web_app_account}-logs"),
            access_control=aws_s3.BucketAccessControl.LOG_DELIVERY_WRITE,
            block_public_access=aws_s3.BlockPublicAccess.BLOCK_ALL,
            encryption=aws_s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        cdk_nag.NagSuppressions.add_resource_suppressions(
            self.__access_log_bucket,
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-S3BucketDefaultLockEnabled",
                    reason="No need to have object lock for CDN access logs.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-S3BucketReplicationEnabled",
                    reason="No need to have replication for CDN access logs.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-S3BucketVersioningEnabled",
                    reason="No need to have versioning for CDN access logs.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-S3BucketReplicationEnabled",
                    reason="No need to have replication for CDN access logs.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-S3BucketVersioningEnabled",
                    reason="No need to have versioning for CDN access logs.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-S3DefaultEncryptionKMS",
                    reason="Currently there is no requirement to use KMS customer managed keys.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-S3DefaultEncryptionKMS",
                    reason="Currently there is no requirement to use KMS customer managed keys.",
                ),
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason="Bucket itself is an access log bucket and would result in infinite loop.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-S3BucketLoggingEnabled",
                    reason="Bucket itself is an access log bucket and would result in infinite loop.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-S3BucketLoggingEnabled",
                    reason="Bucket itself is an access log bucket and would result in infinite loop.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-S3BucketLoggingEnabled",
                    reason="Bucket itself is an access log bucket and would result in infinite loop.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-S3BucketReplicationEnabled",
                    reason="There is not requirement to replicate access logs.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-S3BucketVersioningEnabled", reason="There is no requirement for access logs."
                ),
            ],
        )

    @property
    def access_log_bucket(self):
        return self.__access_log_bucket
