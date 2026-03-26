from pydantic import Field

from app.shared.middleware import event_handler


class ContainerChangeNotification(event_handler.EventBase):
    taskArn: str = Field(..., alias="taskArn")
    clusterArn: str = Field(..., alias="clusterArn")
    lastStatus: str = Field(..., alias="lastStatus")
    accountId: str = Field(..., alias="accountId")
    region: str = Field(..., alias="region")
