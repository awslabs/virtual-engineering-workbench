import typing

import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel, ConfigDict

from app.authorization.adapters.repository import dynamo_entity_config
from app.authorization.domain.integration_event_handlers.projects import (
    enrolment_approved_handler,
    user_assigned_handler,
    user_reassigned_handler,
    user_unassigned_handler,
)
from app.authorization.domain.integration_events.projects import (
    enrolment_approved,
    user_assigned,
    user_reassigned,
    user_unassigned,
)
from app.authorization.entrypoints.projects_event_handler import config
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    enrolment_approved_handler: typing.Callable[[enrolment_approved.EnrolmentApproved], None]
    user_assigned_handler: typing.Callable[[user_assigned.UserAssigned], None]
    user_reassigned_handler: typing.Callable[[user_reassigned.UserReAssigned], None]
    user_unassigned_handler: typing.Callable[[user_unassigned.UserUnAssigned], None]
    model_config = ConfigDict(arbitrary_types_allowed=True)


def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=app_config.get_table_name()).repo_factories(),
        logger=logger,
    )

    def __enrolment_approved(event: enrolment_approved.EnrolmentApproved):
        enrolment_approved_handler.handle(event=event, uow=uow)

    def __user_assigned(event: user_assigned.UserAssigned):
        user_assigned_handler.handle(event=event, uow=uow)

    def __user_reassigned(event: user_reassigned.UserReAssigned):
        user_reassigned_handler.handle(event=event, uow=uow)

    def __user_unassigned(event: user_unassigned.UserUnAssigned):
        user_unassigned_handler.handle(event=event, uow=uow)

    return Dependencies(
        enrolment_approved_handler=__enrolment_approved,
        user_assigned_handler=__user_assigned,
        user_reassigned_handler=__user_reassigned,
        user_unassigned_handler=__user_unassigned,
    )
