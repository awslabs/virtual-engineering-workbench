import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import launch_product_command
from app.provisioning.domain.model import user_profile
from app.provisioning.domain.ports import (
    products_query_service,
    projects_query_service,
    provisioned_products_query_service,
    versions_query_service,
)
from app.shared.adapters.feature_toggling import backend_feature_toggles
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.ddd import aggregate


def handle(
    command: launch_product_command.LaunchProductCommand,
    publisher: aggregate.AggregatePublisher,
    products_qs: products_query_service.ProductsQueryService,
    versions_qs: versions_query_service.VersionsQueryService,
    logger: logging.Logger,
    provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    uow: unit_of_work.UnitOfWork,
    feature_toggles_srv: backend_feature_toggles.BackendFeatureToggles,
    experimental_provisioned_product_per_project_limit: int,
    projects_qs: projects_query_service.ProjectsQueryService,
):
    with uow:
        user_profile_entity = uow.get_repository(user_profile.UserProfilePrimaryKey, user_profile.UserProfile).get(
            pk=user_profile.UserProfilePrimaryKey(
                userId=command.user_id.value,
            ),
        )

    product_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger, user_profile_entity=user_profile_entity
    )

    product_provisioning.launch(
        command=command,
        products_qs=products_qs,
        versions_qs=versions_qs,
        provisioned_products_qs=provisioned_products_qs,
        feature_toggles_srv=feature_toggles_srv,
        experimental_provisioned_product_per_project_limit=experimental_provisioned_product_per_project_limit,
        projects_qs=projects_qs,
    )

    publisher.publish(product_provisioning)
