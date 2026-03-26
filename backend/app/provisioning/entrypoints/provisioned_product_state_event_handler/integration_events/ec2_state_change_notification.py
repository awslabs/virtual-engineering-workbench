from pydantic import Field

from app.shared.middleware import event_handler


class EC2StateChangeNotification(event_handler.EventBase):
    instanceId: str = Field(..., alias="instanceId")
    state: str = Field(..., alias="state")
    accountId: str = Field(..., alias="accountId")
    region: str = Field(..., alias="region")
