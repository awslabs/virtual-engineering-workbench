import re

from pydantic import BaseModel, Field, root_validator, validator

from app.provisioning.entrypoints.provisioned_product_event_handlers.model import product_cf_stack_status
from app.shared.middleware import event_handler


class CatalogSNSNotificationBody(BaseModel):
    sc_provisioned_product_id: str = Field(..., alias="SCProvisionedProductId")
    stack_name: str = Field(..., alias="StackName")
    stack_id: str = Field(..., alias="StackId")
    resource_status: product_cf_stack_status.ProductCFStackStatus = Field(..., alias="ResourceStatus")
    resource_type: str = Field(..., alias="ResourceType")
    account: str = Field(..., alias="Account")
    region: str = Field(..., alias="Region")

    @root_validator(pre=True)
    def parse_sc_provisioned_product_id(cls, values) -> dict:
        """
        Takes StackName property from the notification and parses the workbench ID (provisioned product ID)
        """
        s_name = values.get("StackName")
        wb_id_regex = re.compile(r"pp-\w+")
        values["SCProvisionedProductId"] = wb_id_regex.search(s_name).group()

        s_id_parts = values.get("StackId").split(":")
        values["Region"] = s_id_parts[3]
        values["Account"] = s_id_parts[4]

        return values


class CatalogSNSNotification(event_handler.EventBase):
    message: CatalogSNSNotificationBody = Field(..., alias="Message")

    @validator("message", pre=True)
    def message_validator(cls, v):
        """
        Converts stack notification format "Key1='Value1'\nKey2='Value2'" to dict and creates CatalogSNSNotificationBody
        """
        msg_dict = {line.split("=")[0]: line.split("=")[1].strip("'") for line in v.split("\n") if line and "=" in line}
        return CatalogSNSNotificationBody.parse_obj(msg_dict)
