from datetime import datetime, timezone

from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.ports import products_query_service, versions_query_service
from app.provisioning.domain.read_models import version
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    project_id: str,
    product_id: str,
    new_recommended_version_id: str,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    product_qry_srv: products_query_service.ProductsQueryService,
    uow: unit_of_work.UnitOfWork,
) -> None:
    product_entity = product_qry_srv.get_product(project_id=project_id, product_id=product_id)
    new_recommended_version_distributions = versions_qry_srv.get_product_version_distributions(
        product_id, new_recommended_version_id
    )
    old_recommended_version_distributions = versions_qry_srv.get_product_version_distributions(
        product_id, is_recommended=True
    )
    if not product_entity:
        raise domain_exception.DomainException("Product for this versions does not exist")

    with uow:
        current_date = datetime.now(timezone.utc).isoformat()
        for v in new_recommended_version_distributions:
            v.isRecommendedVersion = True
            v.lastUpdateDate = current_date
            uow.get_repository(version.VersionPrimaryKey, version.Version).update_entity(
                pk=version.VersionPrimaryKey(
                    productId=v.productId,
                    versionId=v.versionId,
                    awsAccountId=v.awsAccountId,
                ),
                entity=v,
            )
        for v in old_recommended_version_distributions:
            v.isRecommendedVersion = False
            v.lastUpdateDate = current_date
            uow.get_repository(version.VersionPrimaryKey, version.Version).update_entity(
                pk=version.VersionPrimaryKey(
                    productId=v.productId,
                    versionId=v.versionId,
                    awsAccountId=v.awsAccountId,
                ),
                entity=v,
            )
        uow.commit()
