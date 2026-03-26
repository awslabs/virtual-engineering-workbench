import typing

import aws_cdk
import constructs
from aws_cdk import aws_dynamodb, aws_lambda
from aws_cdk import aws_lambda_event_sources as event_sources

from infra import config


class EventStream(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        dynamodb_table: aws_dynamodb.ITable,
    ) -> None:
        super().__init__(scope, id)

        self._app_config = app_config
        self._dynamodb_table = dynamodb_table

    def subscribe_to_stream(
        self,
        lambda_function: aws_lambda.IFunction,
        filters: typing.List[aws_lambda.FilterCriteria] = None,
        batch_size: int = 20,
        retry_attempts: int = 0,
        parallelization_factor: int = 1,
        max_batching_window: aws_cdk.Duration = aws_cdk.Duration.seconds(60),
    ):
        if lambda_function:
            # Grant Lambda function with permissions to read from DynamoDB Stream
            self._dynamodb_table.grant_read_data(lambda_function)

            # Add DynamoDB stream as a trigger for Lambda function with specific filter or None
            lambda_function.add_event_source(
                event_sources.DynamoEventSource(
                    self._dynamodb_table,
                    starting_position=aws_lambda.StartingPosition.LATEST,
                    batch_size=batch_size,
                    max_batching_window=max_batching_window,
                    bisect_batch_on_error=True,
                    retry_attempts=retry_attempts,
                    parallelization_factor=parallelization_factor,  # review for performance
                    filters=filters,
                ),
            )


def from_bounded_context(
    scope,
    id,
    app_config: config.AppConfig,
    dynamodb_table: aws_dynamodb.ITable,
) -> EventStream:
    """
    Gets DynamoDB stream from another component (bounded context)
    """
    return EventStream(
        scope,
        id,
        app_config=app_config,
        dynamodb_table=dynamodb_table,
    )


def for_self(
    scope,
    id,
    app_config: config.AppConfig,
    dynamodb_table: aws_dynamodb.ITable,
) -> EventStream:
    """
    Gets DynamoDB stream for a component from app_config.
    """
    return from_bounded_context(
        scope,
        id,
        app_config=app_config,
        dynamodb_table=dynamodb_table,
    )
