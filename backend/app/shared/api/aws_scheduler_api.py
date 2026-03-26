import json

from pydantic import BaseModel, Field

from app.shared.adapters.message_bus import message_bus


class CreateUpdateScheduleResponse(BaseModel):
    schedule_arn: str = Field(..., alias="ScheduleArn")


class AWSSchedulerApi:
    def __init__(self, client, bounded_context_name, role_arn, event_bus_arn) -> None:
        self._client = client
        self._bounded_context_name = bounded_context_name
        self._role_arn = role_arn
        self._event_bus_arn = event_bus_arn

    def create_flexible_schedule(self, flexible_config: message_bus.ScheduleFlexibleConfig, event_json: dict):
        detail_type = event_json.get("DetailType")

        schedule_expression = flexible_config.cron_expression
        event_detail_str = json.dumps(event_json.get("Detail"), ensure_ascii=False)

        resp = self._client.create_schedule(
            ActionAfterCompletion="DELETE",
            Description=f"Flexible scheduled publishing of {detail_type} at {flexible_config.end_time.isoformat()}",
            Name=flexible_config.schedule_id,
            GroupName=self._bounded_context_name,
            EndDate=flexible_config.end_time,
            ScheduleExpression=schedule_expression,
            FlexibleTimeWindow={"Mode": "FLEXIBLE", "MaximumWindowInMinutes": 240},
            Target={
                "Arn": self._event_bus_arn,
                "EventBridgeParameters": {"DetailType": detail_type, "Source": event_json.get("Source")},
                "Input": event_detail_str,
                "RoleArn": self._role_arn,
            },
        )

        return CreateUpdateScheduleResponse(**resp)

    def create_schedule(self, schedule_config: message_bus.ScheduleConfig, event_json: dict):

        detail_type = event_json.get("DetailType")

        naive_time = schedule_config.end_time.replace(tzinfo=None)
        formatted_time = naive_time.strftime("%Y-%m-%dT%H:%M:%S")
        schedule_expression = f"at({formatted_time})"
        event_detail_str = json.dumps(event_json.get("Detail"), ensure_ascii=False)

        resp = self._client.create_schedule(
            ActionAfterCompletion="DELETE",
            Description=f"Scheduled publishing of {detail_type} at {schedule_config.end_time.isoformat()}",
            Name=schedule_config.schedule_id,
            GroupName=self._bounded_context_name,
            ScheduleExpression=schedule_expression,
            FlexibleTimeWindow={"Mode": "OFF"},
            Target={
                "Arn": self._event_bus_arn,
                "EventBridgeParameters": {"DetailType": detail_type, "Source": event_json.get("Source")},
                "Input": event_detail_str,
                "RoleArn": self._role_arn,
            },
        )

        return CreateUpdateScheduleResponse(**resp)

    def update_schedule(self, schedule_config: message_bus.ScheduleConfig, event_json: dict):
        detail_type = event_json.get("DetailType")

        try:
            self._client.get_schedule(
                Name=schedule_config.schedule_id,
                GroupName=self._bounded_context_name,
            )
            schedule_expression = f"at({schedule_config.end_time.isoformat()})"
            event_detail_str = json.dumps(event_json.get("Detail"), ensure_ascii=False)

            resp = self._client.update_schedule(
                ActionAfterCompletion="DELETE",
                Description=f"Rescheduled publishing of {detail_type} at {schedule_config.end_time.isoformat()}",
                Name=schedule_config.schedule_id,
                GroupName=self._bounded_context_name,
                ScheduleExpression=schedule_expression,
                EndDate=schedule_config.end_time,
                FlexibleTimeWindow={"Mode": "OFF"},
                Target={
                    "Arn": self._event_bus_arn,
                    "EventBridgeParameters": {"DetailType": detail_type, "Source": event_json.get("Source")},
                    "Input": event_detail_str,
                    "RoleArn": self._role_arn,
                },
            )
        except:
            raise Exception(
                f"Schedule with ID {schedule_config.schedule_id} in schedule group {self._bounded_context_name} not found"
            )

        return CreateUpdateScheduleResponse(**resp)

    def delete_schedule(self, schedule_id: str):
        try:
            self._client.get_schedule(Name=schedule_id, GroupName=self._bounded_context_name)
            self._client.delete_schedule(Name=schedule_id, GroupName=self._bounded_context_name)
        except:
            raise Exception(f"Schedule with ID {schedule_id} in schedule group {self._bounded_context_name} not found")
