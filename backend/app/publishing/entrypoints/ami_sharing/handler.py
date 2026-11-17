from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import event_source

from app.publishing.domain.commands import (
    accept_license_grant_command,
    copy_ami_command,
    create_license_grant_command,
    fail_ami_sharing_command,
    share_ami_command,
    succeed_ami_sharing_command,
)
from app.publishing.domain.model import product
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    event_name_value_object,
    grant_arn_value_object,
    grant_id_value_object,
    grant_name_value_object,
    product_id_value_object,
    product_type_value_object,
    project_id_value_object,
    region_value_object,
    version_id_value_object,
)
from app.publishing.entrypoints.ami_sharing import bootstrapper, config, step_error
from app.publishing.entrypoints.ami_sharing.model import step_function_model
from app.shared.middleware import event_handler
from app.shared.middleware.custom_events import step_function_event
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

logger = logging.Logger()
tracer = tracing.Tracer()
metrics_handler = metrics.Metrics()
app_config = config.AppConfig()
dependencies = bootstrapper.bootstrap(app_config, logger)
app = event_handler.StepFunctionEventResolver(logger=logger)


@app.handle(step_function_model.DecideActionRequest)
def handle_decide_action(event: step_function_model.DecideActionRequest):
    result = dependencies.shared_amis_domain_qry_svc.make_share_ami_decision(
        product_id=product_id_value_object.from_str(event.product_id),
        version_id=version_id_value_object.from_str(event.version_id),
        aws_account_id=aws_account_id_value_object.from_str(event.aws_account_id),
        product_type=product_type_value_object.from_str(event.product_type),
    )
    return step_function_model.DecideActionResponse(
        decision=result.decision.value,
        originalAmiId=result.original_ami_id,
        copiedAmiId=result.copied_ami_id,
        region=result.region,
        imageId=result.image_id,
        projectId=result.project_id,
        licenseArn=result.license_arn,
        homeRegion=result.home_region,
        grantName=result.grant_name,
    ).model_dump(by_alias=True)


@app.handle(step_function_model.VerifyCopyRequest)
def handle_verify_copy(event: step_function_model.VerifyCopyRequest):
    is_copy_verified = dependencies.shared_amis_domain_qry_svc.verify_copy(
        region=region_value_object.from_str(event.region),
        copied_ami_id=ami_id_value_object.from_str(event.copied_ami_id),
    )
    return step_function_model.VerifyCopyResponse(isCopyVerified=is_copy_verified).model_dump(by_alias=True)


@app.handle(step_function_model.CopyAmiRequest)
def handle_copy_ami(event: step_function_model.CopyAmiRequest):
    """Copies an AMI to another region"""
    command = copy_ami_command.CopyAmiCommand(
        originalAmiId=ami_id_value_object.from_str(event.original_ami_id),
        region=region_value_object.from_str(event.region),
    )

    copied_ami_id = dependencies.command_bus.handle(command)

    return step_function_model.CopyAmiResponse(copiedAmiId=copied_ami_id).model_dump(by_alias=True)


@app.handle(step_function_model.ShareAmiRequest)
def handle_share_ami(event: step_function_model.ShareAmiRequest):
    """Shares an AMI with another account"""
    command = share_ami_command.ShareAmiCommand(
        originalAmiId=ami_id_value_object.from_str(event.original_ami_id),
        copiedAmiId=ami_id_value_object.from_str(event.copied_ami_id),
        region=region_value_object.from_str(event.region),
        awsAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
    )

    dependencies.command_bus.handle(command)

    return step_function_model.ShareAmiResponse().model_dump(by_alias=True)


@app.handle(step_function_model.SucceedAmiSharingRequest)
def handle_succeed_ami_sharing(event: step_function_model.SucceedAmiSharingRequest):
    """Succeeds ami sharing process"""
    # Validation: copiedAmiId can only be empty if productType is "Container"
    if not event.copied_ami_id and event.product_type != product.ProductType.Container.value:
        raise ValueError("copiedAmiId must be provided unless productType is 'Container'")
    command = succeed_ami_sharing_command.SucceedAmiSharingCommand(
        productId=product_id_value_object.from_str(event.product_id),
        versionId=version_id_value_object.from_str(event.version_id),
        awsAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
        copiedAmiId=(ami_id_value_object.from_str(event.copied_ami_id) if event.copied_ami_id else None),
        previousEventName=event_name_value_object.from_str(event.previous_event_name),
        oldVersionId=event.old_version_id,
        productType=product_type_value_object.from_str(event.product_type),
    )

    dependencies.command_bus.handle(command)

    return step_function_model.SucceedAmiSharingResponse().model_dump(by_alias=True)


@app.handle(step_function_model.FailAmiSharingRequest)
def handle_fail_ami_sharing(event: step_function_model.FailAmiSharingRequest):
    """Fails ami sharing process"""
    command = fail_ami_sharing_command.FailAmiSharingCommand(
        productId=product_id_value_object.from_str(event.product_id),
        versionId=version_id_value_object.from_str(event.version_id),
        awsAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
        statusReason=step_error.summarize(event.error),
    )

    dependencies.command_bus.handle(command)

    return step_function_model.FailAmiSharingResponse().model_dump(by_alias=True)


@app.handle(step_function_model.CreateLicenseGrantRequest)
def handle_create_license_grant_sfn(event: step_function_model.CreateLicenseGrantRequest):
    """Creates a License Manager grant for a spoke account (called by Step Functions)."""
    command = create_license_grant_command.CreateLicenseGrantCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        amiId=ami_id_value_object.from_str(event.image_id),
        targetAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
        grantName=grant_name_value_object.from_str(event.grant_name),
    )
    result = dependencies.command_bus.handle(command)
    return step_function_model.CreateLicenseGrantResponse(
        grantId=result.grantId,
        grantArn=result.grantArn,
        homeRegion=result.homeRegion,
    ).model_dump(by_alias=True)


@app.handle(step_function_model.AcceptLicenseGrantRequest)
def handle_accept_license_grant_sfn(event: step_function_model.AcceptLicenseGrantRequest):
    """Accepts and activates a License Manager grant in the spoke account."""
    command = accept_license_grant_command.AcceptLicenseGrantCommand(
        grantId=grant_id_value_object.from_str(event.grant_id),
        grantArn=grant_arn_value_object.from_str(event.grant_arn),
        projectId=project_id_value_object.from_str(event.project_id),
        homeRegion=region_value_object.from_str(event.home_region),
        targetAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
    )
    dependencies.command_bus.handle(command)
    return step_function_model.AcceptLicenseGrantResponse().model_dump(by_alias=True)


@app.handle(step_function_model.VerifyLicenseGrantRequest)
def handle_verify_license_grant(event: step_function_model.VerifyLicenseGrantRequest):
    """Verifies AMI is accessible in spoke account after grant acceptance."""
    is_accessible = dependencies.license_manager_svc.verify_image_accessible(
        ami_id=ami_id_value_object.from_str(event.ami_id).value,
        region=region_value_object.from_str(event.region).value,
        spoke_account_id=aws_account_id_value_object.from_str(event.aws_account_id).value,
    )
    return step_function_model.VerifyLicenseGrantResponse(isAccessible=is_accessible).model_dump(by_alias=True)


@app.handle(step_function_model.VerifyExternalGrantRequest)
def handle_verify_external_grant(event: step_function_model.VerifyExternalGrantRequest):
    """Verifies an active EXTERNALLY_MANAGED grant exists in the spoke account for the license."""
    grant_verified = dependencies.license_manager_svc.has_active_received_grant(
        license_arn=grant_arn_value_object.from_str(event.license_arn).value,
        spoke_account_id=aws_account_id_value_object.from_str(event.aws_account_id).value,
        home_region=region_value_object.from_str(event.home_region).value,
    )
    return step_function_model.VerifyExternalGrantResponse(grantVerified=grant_verified).model_dump(by_alias=True)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "AmiSharing"})
@event_source(data_class=step_function_event.StepFunctionEvent)
def handler(
    event: step_function_event.StepFunctionEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
