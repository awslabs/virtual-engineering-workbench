import boto3
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities.data_classes import CloudFormationCustomResourceEvent, event_source
from aws_lambda_powertools.utilities.typing import LambdaContext
from mypy_boto3_events import client

eb_client: client.EventBridgeClient = boto3.client("events")
logger = logging.Logger()


@event_source(data_class=CloudFormationCustomResourceEvent)
@logger.inject_lambda_context(log_event=True)
def handler(event: CloudFormationCustomResourceEvent, context: LambdaContext):

    request_type = event.request_type

    if request_type == "Create":
        return on_create(event)
    if request_type == "Update":
        return on_update(event)
    if request_type == "Delete":
        return on_delete(event)


def on_create(event: CloudFormationCustomResourceEvent):

    props = event.resource_properties
    logger.info(f"Create new resource with props {props}.")

    eb_name = props.get("Name")

    try:
        eb = eb_client.describe_event_bus(Name=eb_name)
        return {"PhysicalResourceId": eb.get("Arn"), "Data": {"EventBusArn": eb.get("Arn")}}
    except eb_client.exceptions.ResourceNotFoundException:
        logger.warning(f"EventBus {eb_name} not found. Creating new EventBus.")
    except Exception as e:
        logger.exception("Failed to fetch EventBus.")
        raise e

    try:
        eb = eb_client.create_event_bus(Name=eb_name)
        return {"PhysicalResourceId": eb.get("EventBusArn"), "Data": {"EventBusArn": eb.get("EventBusArn")}}
    except Exception as e:
        logger.exception("Failed to create EventBus.")
        raise e


def on_update(event: CloudFormationCustomResourceEvent):
    physical_id = event.physical_resource_id
    props = event.resource_properties
    logger.info(f"Skipping update resource {physical_id} with props {props}.")


def on_delete(event: CloudFormationCustomResourceEvent):
    physical_id = event.physical_resource_id
    logger.info(f"Skipping delete resource {physical_id}.")
