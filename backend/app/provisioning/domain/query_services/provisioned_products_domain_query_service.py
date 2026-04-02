import typing
from typing import List, Optional, Tuple

from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import (
    product_status,
    provisioned_product,
    user_credential,
)
from app.provisioning.domain.ports import (
    networking_query_service,
    parameter_service,
    provisioned_products_query_service,
    versions_query_service,
)
from app.provisioning.domain.read_models import version
from app.provisioning.domain.value_objects import (
    product_name_value_object,
    product_status_value_object,
    product_version_name_value_object,
    project_id_value_object,
    provisioned_product_id_value_object,
    provisioned_product_stage_value_object,
    provisioned_product_type_value_object,
    user_id_value_object,
)


class ProvisionedProductsDomainQueryService:
    def __init__(
        self,
        provisioned_products_qry_srv: provisioned_products_query_service.ProvisionedProductsQueryService,
        version_qry_srv: versions_query_service.VersionsQueryService,
        networking_qry_srv: networking_query_service.NetworkingQueryService,
        parameter_srv: parameter_service.ParameterService,
    ) -> None:
        self._provisioned_products_qry_srv = provisioned_products_qry_srv
        self._version_qry_srv = version_qry_srv
        self._networking_qry_srv = networking_qry_srv
        self._parameter_srv = parameter_srv

    def get_all_provisioned_products(
        self, start_key: typing.Optional[dict] = None
    ) -> typing.Tuple[typing.List[provisioned_product.ProvisionedProduct], typing.Optional[dict]]:
        return self._provisioned_products_qry_srv.get_all_cross_projects_provisioned_products(
            start_key=start_key, exclude_terminated=True
        )

    def get_paginated_provisioned_products(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        page_size: int,
        paging_key: dict | None = None,
        product_name: product_name_value_object.ProductNameValueObject | None = None,
        version_name: product_version_name_value_object.ProductVersionNameValueObject | None = None,
        owner: user_id_value_object.UserIdValueObject | None = None,
        provisioned_product_type: provisioned_product_type_value_object.ProvisionedProductTypeValueObject | None = None,
        status: product_status_value_object.ProductStatusValueObject | None = None,
        stage: provisioned_product_stage_value_object.ProvisionedProductStageValueObject | None = None,
        experimental: bool = False,
    ) -> Tuple[List[provisioned_product.ProvisionedProduct], Optional[dict]]:

        provisioned_products, last_evaluated_key = (
            self._provisioned_products_qry_srv.get_provisioned_products_by_project_id_paginated(
                project_id=project_id.value,
                page_size=page_size,
                paging_key=paging_key,
                provisioned_product_type=(provisioned_product_type.value if provisioned_product_type else None),
                stage=stage.value if stage else None,
                experimental=experimental,
                product_name=product_name.value if product_name else None,
                version_name=version_name.value if version_name else None,
                owner=owner.value if owner else None,
                status=status.value if status else None,
            )
        )

        return provisioned_products, last_evaluated_key

    def get_provisioned_products(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        user_id: user_id_value_object.UserIdValueObject | None = None,
        provisioned_product_type: provisioned_product_type_value_object.ProvisionedProductTypeValueObject | None = None,
        exclude_status: list[product_status_value_object.ProductStatusValueObject] | None = None,
        return_technical_params: bool = True,
    ) -> typing.List[provisioned_product.ProvisionedProduct]:
        if user_id:
            provisioned_products = self._provisioned_products_qry_srv.get_provisioned_products_by_user_id(
                user_id=user_id.value,
                project_id=project_id.value,
                provisioned_product_type=(provisioned_product_type.value if provisioned_product_type else None),
                exclude_status=([status.value for status in exclude_status] if exclude_status else None),
            )
        elif exclude_status == [product_status_value_object.from_str(product_status.ProductStatus.Terminated)]:
            # Optimized query for fetching all non-terminated provisioned products
            provisioned_products = self._provisioned_products_qry_srv.get_active_provisioned_products_by_project_id(
                project_id=project_id.value,
                provisioned_product_type=(provisioned_product_type.value if provisioned_product_type else None),
            )
        else:
            provisioned_products = self._provisioned_products_qry_srv.get_provisioned_products_by_project_id(
                project_id=project_id.value,
                provisioned_product_type=(provisioned_product_type.value if provisioned_product_type else None),
                exclude_status=([status.value for status in exclude_status] if exclude_status else None),
            )

        if not return_technical_params:
            for prod in provisioned_products:
                prod.provisioningParameters = [
                    param for param in (prod.provisioningParameters or []) if not param.isTechnicalParameter
                ]

        return provisioned_products

    def get_provisioned_product(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject,
        return_technical_params: bool = True,
        user_id: user_id_value_object.UserIdValueObject | None = None,
    ) -> tuple[provisioned_product.ProvisionedProduct, version.Version | None]:
        provisioned_product_entity = self._provisioned_products_qry_srv.get_provisioned_product(
            project_id.value, provisioned_product_id.value
        )

        if not provisioned_product_entity:
            raise NotFoundError(f"Provisioned product with id: {provisioned_product_id.value} does not exist.")

        if user_id and provisioned_product_entity.userId != user_id.value:
            raise domain_exception.DomainException("You do not have permissions to fetch the provisioned product")

        version_metadata = self._version_qry_srv.get_product_version_distributions(
            product_id=provisioned_product_entity.productId,
            version_id=provisioned_product_entity.versionId,
            aws_account_ids=[provisioned_product_entity.awsAccountId],
        )

        if not return_technical_params:
            provisioned_product_entity.provisioningParameters = [
                param
                for param in (provisioned_product_entity.provisioningParameters or [])
                if not param.isTechnicalParameter
            ]

        return provisioned_product_entity, (version_metadata.pop() if version_metadata else None)

    def get_provisioned_product_ssh_key(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject,
        user_id: user_id_value_object.UserIdValueObject,
    ) -> str:

        pp = self._provisioned_products_qry_srv.get_provisioned_product(
            project_id=project_id.value,
            provisioned_product_id=provisioned_product_id.value,
        )

        if not pp:
            raise domain_exception.DomainException("Provisioned product does not exist")

        if pp.userId != user_id.value:
            raise domain_exception.DomainException(
                "You do not have permissions to fetch the SSH key of the provisioned product"
            )

        if not pp.sshKeyPath:
            raise domain_exception.DomainException("Provisioned product does not have an SSH key.")

        return self._parameter_srv.get_parameter_value(
            parameter_name=pp.sshKeyPath,
            aws_account_id=pp.awsAccountId,
            region=pp.region,
            user_id=user_id.value,
        )

    def get_provisioned_product_user_credentials(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject,
        user_id: user_id_value_object.UserIdValueObject,
    ) -> user_credential.UserCredential:

        pp = self._provisioned_products_qry_srv.get_provisioned_product(
            project_id=project_id.value,
            provisioned_product_id=provisioned_product_id.value,
        )

        if not pp:
            raise domain_exception.DomainException("Provisioned product does not exist")

        if pp.userId != user_id.value:
            raise domain_exception.DomainException(
                "You do not have permissions to fetch the  user credentials of the provisioned product"
            )

        if not pp.userCredentialName:
            raise domain_exception.DomainException("Provisioned product does not have user credentials.")

        secret_string = self._parameter_srv.get_secret_value(
            secret_name=pp.userCredentialName,
            aws_account_id=pp.awsAccountId,
            region=pp.region,
            user_id=user_id.value,
        )

        return user_credential.UserCredential.model_validate_json(secret_string)
