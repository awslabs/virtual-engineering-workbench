import json

import constructs
from aws_cdk import custom_resources

from infra import config


class EventPublisher(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        source: str,
        detail_type: str,
        detail: dict,
        app_config: config.AppConfig,
        event_bus_arn: str,
        physical_resource_id_str: str,
    ) -> None:
        super().__init__(scope, id)

        sdk_call = custom_resources.AwsSdkCall(
            service="eventbridge",
            action="putEvents",
            parameters={
                "Entries": [
                    {
                        "Source": source,
                        "DetailType": detail_type,
                        "Detail": json.dumps(detail),
                        "EventBusName": event_bus_arn,
                    }
                ]
            },
            region=app_config.region,
            physical_resource_id=custom_resources.PhysicalResourceId.of(physical_resource_id_str),
        )

        custom_resources.AwsCustomResource(
            scope,
            id=f"{id}EventBridgeEventCustomResource",
            on_create=sdk_call,
            on_update=sdk_call,
            policy=custom_resources.AwsCustomResourcePolicy.from_sdk_calls(resources=[event_bus_arn]),
        )
