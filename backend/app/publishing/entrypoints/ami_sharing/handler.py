from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import event_source

from app.publishing.domain.commands import (
    copy_ami_command,
    fail_ami_sharing_command,
    share_ami_command,
    succeed_ami_sharing_command,
)
from app.publishing.domain.model import product
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    event_name_value_object,
    product_id_value_object,
    product_type_value_object,
    region_value_object,
    version_id_value_object,
)
from app.publishing.entrypoints.ami_sharing import bootstrapper, config
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
    decision, region, original_ami_id, copied_ami_id = dependencies.shared_amis_domain_qry_svc.make_share_ami_decision(
        product_id=product_id_value_object.from_str(event.product_id),
        version_id=version_id_value_object.from_str(event.version_id),
        aws_account_id=aws_account_id_value_object.from_str(event.aws_account_id),
        product_type=product_type_value_object.from_str(event.product_type),
    )
    return step_function_model.DecideActionResponse(
        decision=decision.value, originalAmiId=original_ami_id, copiedAmiId=copied_ami_id, region=region
    ).dict(by_alias=True)


@app.handle(step_function_model.VerifyCopyRequest)
def handle_verify_copy(event: step_function_model.VerifyCopyRequest):
    is_copy_verified = dependencies.shared_amis_domain_qry_svc.verify_copy(
        region=region_value_object.from_str(event.region),
        copied_ami_id=ami_id_value_object.from_str(event.copied_ami_id),
    )
    return step_function_model.VerifyCopyResponse(isCopyVerified=is_copy_verified).dict(by_alias=True)


@app.handle(step_function_model.CopyAmiRequest)
def handle_copy_ami(event: step_function_model.CopyAmiRequest):
    """Copies an AMI to another region"""
    command = copy_ami_command.CopyAmiCommand(
        originalAmiId=ami_id_value_object.from_str(event.original_ami_id),
        region=region_value_object.from_str(event.region),
    )

    copied_ami_id = dependencies.command_bus.handle(command)

    return step_function_model.CopyAmiResponse(copiedAmiId=copied_ami_id).dict(by_alias=True)


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

    return step_function_model.ShareAmiResponse().dict(by_alias=True)


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

    return step_function_model.SucceedAmiSharingResponse().dict(by_alias=True)


@app.handle(step_function_model.FailAmiSharingRequest)
def handle_fail_ami_sharing(event: step_function_model.FailAmiSharingRequest):
    """Fails ami sharing process"""
    command = fail_ami_sharing_command.FailAmiSharingCommand(
        productId=product_id_value_object.from_str(event.product_id),
        versionId=version_id_value_object.from_str(event.version_id),
        awsAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
    )

    dependencies.command_bus.handle(command)

    return step_function_model.FailAmiSharingResponse().dict(by_alias=True)


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
