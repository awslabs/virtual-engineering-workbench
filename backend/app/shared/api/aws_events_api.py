from typing import Any, List, Optional

from pydantic import BaseModel, Field


class PutEventsResponse(BaseModel):
    failed_entry_count: int = Field(..., alias="FailedEntryCount")
    entries: List[Any] = Field(..., alias="Entries")


class AWSEventsApi:
    def __init__(self, client) -> None:
        self._client = client

    def put_event(
        self,
        source: str,
        detail: str,
        resources: List[str],
        detail_type: str,
        event_bus: Optional[str] = None,
    ) -> PutEventsResponse:
        entry = {
            "Source": source,
            "Resources": resources,
            "DetailType": detail_type,
            "Detail": detail,
        }

        if event_bus:
            entry["EventBusName"] = event_bus

        resp = self._client.put_events(Entries=[entry])

        return PutEventsResponse(**resp)
