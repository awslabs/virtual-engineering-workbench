import typing

from app.publishing.domain.model import product, version, version_summary
from app.publishing.domain.ports import products_query_service, versions_query_service
from app.publishing.domain.query_services.helpers import version_helpers
from app.publishing.domain.value_objects import (
    product_id_value_object,
    product_type_value_object,
    project_id_value_object,
    user_role_value_object,
)
from app.shared.middleware.authorization import VirtualWorkbenchRoles


class ProductsDomainQueryService:
    def __init__(
        self,
        products_qry_srv: products_query_service.ProductsQueryService,
        versions_qry_srv: versions_query_service.VersionsQueryService,
    ) -> None:
        self._products_qry_srv = products_qry_srv
        self._versions_qry_srv = versions_qry_srv

    def get_products(self, project_id: project_id_value_object.ProjectIdValueObject) -> list[product.Product]:
        return self._products_qry_srv.get_products(project_id=project_id.value)

    def get_product(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        product_id: product_id_value_object.ProductIdValueObject,
    ) -> typing.Tuple[product.Product, list[version_summary.VersionSummary]]:
        distributions = self._versions_qry_srv.get_product_version_distributions(product_id=product_id.value)

        distribution_map: dict[str, list[version.Version]] = {}

        for distribution in distributions:
            if distribution.versionId in distribution_map:
                distribution_map[distribution.versionId].append(distribution)
            else:
                distribution_map[distribution.versionId] = [distribution]

        version_summaries = [version_helpers.get_summary(d) for id, d in distribution_map.items()]

        product = self._products_qry_srv.get_product(project_id=project_id.value, product_id=product_id.value)

        return product, version_summaries

    def get_products_ready_for_provisioning(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        user_roles: list[user_role_value_object.UserRoleValueObject],
        product_type: product_type_value_object.ProductTypeValueObject,
    ) -> list[product.Product]:
        # Decide which stages does the user role has access to
        user_roles = [user_role.value for user_role in user_roles]
        if any(
            [
                user_role
                in [
                    VirtualWorkbenchRoles.Admin,
                    VirtualWorkbenchRoles.ProgramOwner,
                    VirtualWorkbenchRoles.PowerUser,
                    VirtualWorkbenchRoles.ProductContributor,
                ]
                for user_role in user_roles
            ]
        ):
            allowed_stages = [product.ProductStage.DEV, product.ProductStage.QA, product.ProductStage.PROD]
        elif VirtualWorkbenchRoles.BetaUser in user_roles:
            allowed_stages = [product.ProductStage.QA, product.ProductStage.PROD]
        else:
            allowed_stages = [product.ProductStage.PROD]

        # Fetch the products available in these stages
        products = self._products_qry_srv.get_products(
            project_id=project_id.value,
            available_stages=allowed_stages,
            status=product.ProductStatus.Created,
            product_type=product_type.value,
        )

        # Update the stages to return only stages allowed for the user role
        for prod in products:
            prod.availableStages = [stage for stage in prod.availableStages if stage in allowed_stages]

        return products
