from pydantic import ConfigDict

from app.publishing.domain.value_objects import (
    product_description_value_object,
    product_id_value_object,
    product_name_value_object,
    product_type_value_object,
    project_id_value_object,
    tech_id_value_object,
    tech_name_value_object,
    user_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class CreateProductCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    productId: product_id_value_object.ProductIdValueObject
    productName: product_name_value_object.ProductNameValueObject
    productType: product_type_value_object.ProductTypeValueObject
    productDescription: product_description_value_object.ProductDescriptionValueObject
    technologyId: tech_id_value_object.TechIdValueObject
    technologyName: tech_name_value_object.TechNameValueObject
    userId: user_id_value_object.UserIdValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
