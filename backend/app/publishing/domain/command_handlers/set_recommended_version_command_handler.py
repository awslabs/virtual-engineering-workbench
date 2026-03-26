from app.publishing.domain.aggregates import recommended_version_aggregate
from app.publishing.domain.commands import set_recommended_version_command
from app.publishing.domain.events import recommended_version_set
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import products_query_service, versions_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    cmd: set_recommended_version_command.SetRecommendedVersionCommand,
    products_query_service: products_query_service.ProductsQueryService,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    uow: unit_of_work.UnitOfWork,
    msg_bus: message_bus.MessageBus,
):
    p = products_query_service.get_product(cmd.projectId.value, cmd.productId.value)

    new_recommended_version_dist = versions_qry_srv.get_product_version_distributions(
        product_id=cmd.productId.value,
        version_id=cmd.versionId.value,
    )

    old_recommended_version_dist = versions_qry_srv.get_product_version_distributions(
        product_id=cmd.productId.value,
        is_recommended=True,
    )

    with uow:
        recommended_version_aggregate.RecommendedVersionAggregate(
            product=p,
            recommended_version_distributions=old_recommended_version_dist,
            product_repository=uow.get_repository(product.ProductPrimaryKey, product.Product),
            version_repository=uow.get_repository(version.VersionPrimaryKey, version.Version),
        ).validate().set_new(
            new_recommended_version_distributions=new_recommended_version_dist,
            user_id=cmd.userId,
        )

        uow.commit()

    msg_bus.publish(
        recommended_version_set.RecommendedVersionSet(
            project_id=cmd.projectId.value,
            product_id=cmd.productId.value,
            version_id=cmd.versionId.value,
        )
    )
