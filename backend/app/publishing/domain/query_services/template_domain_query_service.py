from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product
from app.publishing.domain.ports import products_query_service, template_service, versions_query_service
from app.publishing.domain.value_objects import (
    product_id_value_object,
    product_type_value_object,
    project_id_value_object,
    template_name_value_object,
    version_id_value_object,
)


class TemplateDomainQueryService:
    def __init__(
        self,
        workbench_template: str,
        virtual_target_template: str,
        container_template: str,
        products_qry_srv: products_query_service.ProductsQueryService,
        template_srv: template_service.TemplateService,
        versions_qry_srv: versions_query_service.VersionsQueryService,
    ) -> None:
        self.__wb_tmpl = template_name_value_object.from_str(workbench_template)
        self.__vt_tmpl = template_name_value_object.from_str(virtual_target_template)
        self.__cnt_tmpl = template_name_value_object.from_str(container_template)
        self.__products_qry_srv = products_qry_srv
        self.__template_srv = template_srv
        self.__versions_qry_srv = versions_qry_srv
        self.__template_map = {
            product.ProductType.VirtualTarget: self.__vt_tmpl,
            product.ProductType.Workbench: self.__wb_tmpl,
            product.ProductType.Container: self.__cnt_tmpl,
        }

    def get_default_template_file_name(
        self,
        product_type: product_type_value_object.ProductTypeValueObject,
        is_draft: bool = False,
        return_full_path: bool = False,
    ) -> str:
        template_file_name = ""
        # Use the dictionary to get the correct template object
        template_obj = self.__template_map.get(product_type.value)

        if not template_obj:
            raise domain_exception.DomainException("Failed  to retrieve template object.")
        template_file_name = template_obj.value if return_full_path else template_obj.get_filename()

        if is_draft:
            template_file_name = f"draft-{template_file_name}"

        return template_file_name

    def get_latest_draft_template(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        product_id: product_id_value_object.ProductIdValueObject,
        version_id: version_id_value_object.VersionIdValueObject | None = None,
    ) -> str:
        """
        Returns the latest draft product template for the given logic:
        1. If version_id is provided, it returns the template for that version.
        2. If version_id is not provided, it find and returns the template for the latest version of the given product_id.
        3. If no version is found for the product, it returns the initial template for the product type.
        """
        product_entity = self.__products_qry_srv.get_product(project_id=project_id.value, product_id=product_id.value)
        downloaded_template_path = None

        # Download the template to the tmp folder for the matching case
        # CASE 1
        if version_id:
            downloaded_template_path = self.__template_srv.get_template(
                template_path=f"{product_entity.productId}/{version_id.value}/{self.get_default_template_file_name(product_type=product_entity.productType, is_draft=True)}"
            )
        else:
            latest_version_id = self.__versions_qry_srv.get_latest_version_name_and_id(product_id=product_id.value)[1]
            # CASE 2
            if latest_version_id:
                downloaded_template_path = self.__template_srv.get_template(
                    template_path=f"{product_entity.productId}/{latest_version_id}/{self.get_default_template_file_name(product_type=product_entity.productType, is_draft=True)}"
                )
            # CASE 3
            else:
                downloaded_template_path = self.__template_srv.get_template(
                    template_path=self.get_default_template_file_name(
                        product_type=product_entity.productType, return_full_path=True
                    )
                )

        # Parse and return the template file
        with open(downloaded_template_path, "r") as template_file:
            return template_file.read()
