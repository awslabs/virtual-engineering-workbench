from app.packaging.domain.ports import mandatory_components_list_query_service
from app.packaging.domain.value_objects.component import (
    component_platform_value_object,
    component_supported_architecture_value_object,
    component_supported_os_version_value_object,
)


class MandatoryComponentsListDomainQueryService(
    mandatory_components_list_query_service.MandatoryComponentsListQueryService
):
    def __init__(
        self,
        mandatory_components_list_qry_srv: mandatory_components_list_query_service.MandatoryComponentsListQueryService,
    ):
        self._mandatory_components_list_qry_srv = mandatory_components_list_qry_srv

    def get_mandatory_components_list(
        self,
        platform: component_platform_value_object.ComponentPlatformValueObject,
        os: component_supported_os_version_value_object.ComponentSupportedOsVersionValueObject,
        architecture: component_supported_architecture_value_object.ComponentSupportedArchitectureValueObject,
    ):
        return self._mandatory_components_list_qry_srv.get_mandatory_components_list(
            platform=platform.value,
            os=os.value,
            architecture=architecture.value,
        )

    def get_mandatory_components_lists(self):
        return self._mandatory_components_list_qry_srv.get_mandatory_components_lists()
