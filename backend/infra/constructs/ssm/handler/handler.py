import hashlib

import boto3
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities.data_classes import CloudFormationCustomResourceEvent, event_source
from aws_lambda_powertools.utilities.typing import LambdaContext
from mypy_boto3_ram import client

ram_client: client.RAMClient = boto3.client("ram")
logger = logging.Logger()


@event_source(data_class=CloudFormationCustomResourceEvent)
@logger.inject_lambda_context(log_event=True)
def handler(event: CloudFormationCustomResourceEvent, context: LambdaContext):

    if event.request_type == "Create":
        return on_create(event)
    if event.request_type == "Update":
        return on_update(event)
    if event.request_type == "Delete":
        return on_delete(event)


def on_create(event: CloudFormationCustomResourceEvent):

    props = event.resource_properties

    resource_share_name = props.get("Name")

    logger.info(f"Accepting resource share {resource_share_name}")

    try:
        paginator = ram_client.get_paginator("get_resource_share_invitations")
        resource_shares = [
            r
            for r in paginator.paginate().build_full_result().get("resourceShareInvitations", [])
            if r.get("resourceShareName") == resource_share_name
        ]

    except Exception as e:
        logger.exception("Failed to fetch resource share invitations")
        raise e

    if accepted := next((r for r in resource_shares if r.get("status") == "ACCEPTED"), None):
        logger.warning(f"Resource share {resource_share_name} is already accepted")
        return {"PhysicalResourceId": accepted.get("resourceShareInvitationArn")}

    if pending := next((r for r in resource_shares if r.get("status") == "PENDING"), None):
        client_token = hashlib.sha256(pending.get("resourceShareInvitationArn").encode("utf-8")).hexdigest()[:64]

        ram_client.accept_resource_share_invitation(
            resourceShareInvitationArn=pending.get("resourceShareInvitationArn"),
            clientToken=client_token,
        )
        return {"PhysicalResourceId": pending.get("resourceShareInvitationArn")}

    logger.error(f"Resource share {resource_share_name} not found")
    raise Exception(f"Resource share {resource_share_name} not found")


def on_update(event: CloudFormationCustomResourceEvent):
    physical_id = event.physical_resource_id
    props = event.resource_properties
    logger.info(f"Skipping update resource {physical_id} with props {props}.")


def on_delete(event: CloudFormationCustomResourceEvent):
    physical_id = event.physical_resource_id
    logger.info(f"Skipping delete resource {physical_id}: RAM resource shares cannot be unaccepted.")
