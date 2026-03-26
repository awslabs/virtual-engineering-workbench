from app.provisioning.domain.ports import publishing_query_service, versions_query_service
from app.provisioning.domain.read_models import product, version
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    product_obj: product.Product,
    uow: unit_of_work.UnitOfWork,
    versions_qry_srv: versions_query_service.VersionsQueryService,
    publishing_qry_srv: publishing_query_service.PublishingQueryService,
) -> None:
    version_objs = publishing_qry_srv.get_available_product_versions(product_id=product_obj.productId)
    if not version_objs:
        with uow:
            versions_in_repo = versions_qry_srv.get_product_version_distributions(product_obj.productId)
            for vers in versions_in_repo:
                uow.get_repository(version.VersionPrimaryKey, version.Version).remove(
                    version.VersionPrimaryKey(
                        productId=vers.productId, versionId=vers.versionId, awsAccountId=vers.awsAccountId
                    )
                )

            product_entity = uow.get_repository(product.ProductPrimaryKey, product.Product).get(
                product.ProductPrimaryKey(projectId=product_obj.projectId, productId=product_obj.productId)
            )
            if product_entity:
                uow.get_repository(product.ProductPrimaryKey, product.Product).remove(
                    product.ProductPrimaryKey(projectId=product_obj.projectId, productId=product_obj.productId)
                )

            uow.commit()
    else:
        versions_in_repo = versions_qry_srv.get_product_version_distributions(product_obj.productId)
        versions_keys_in_repo = {f"{vers.versionId}#{vers.awsAccountId}" for vers in versions_in_repo}
        versions_keys_in_event = {f"{vers.versionId}#{vers.awsAccountId}" for vers in version_objs}

        versions_keys_in_both = versions_keys_in_repo.intersection(versions_keys_in_event)
        versions_keys_only_in_repo = versions_keys_in_repo.difference(versions_keys_in_event)
        versions_keys_only_in_event = versions_keys_in_event.difference(versions_keys_in_repo)

        # Aggregate available tools and os'es across all versions
        available_tools = set(
            [
                comp.componentName
                for vers in version_objs
                if vers.componentVersionDetails
                for comp in vers.componentVersionDetails
            ]
        )
        product_obj.availableTools = available_tools if available_tools else None

        available_os_versions = set([vers.osVersion for vers in version_objs if vers.osVersion])
        product_obj.availableOSVersions = available_os_versions if available_os_versions else None

        with uow:
            # Update version in repo if version already exists in repo and event
            for vers_key in versions_keys_in_both:
                version_entity_from_event = next(
                    filter(
                        lambda vers: f"{vers.versionId}#{vers.awsAccountId}" == vers_key,
                        version_objs,
                    ),
                    None,
                )

                uow.get_repository(version.VersionPrimaryKey, version.Version).update_attributes(
                    version.VersionPrimaryKey(
                        productId=product_obj.productId,
                        versionId=version_entity_from_event.versionId,
                        awsAccountId=version_entity_from_event.awsAccountId,
                    ),
                    **version_entity_from_event.dict(),
                )
            # Remove versions in repo if not present in the event
            for vers_key in versions_keys_only_in_repo:
                version_id, aws_account_id = vers_key.split("#")
                uow.get_repository(version.VersionPrimaryKey, version.Version).remove(
                    version.VersionPrimaryKey(
                        productId=product_obj.productId, versionId=version_id, awsAccountId=aws_account_id
                    )
                )

            # Create new versions if version exists in the event but not in repo
            for vers_key in versions_keys_only_in_event:
                version_entity = next(
                    filter(
                        lambda vers: f"{vers.versionId}#{vers.awsAccountId}" == vers_key,
                        version_objs,
                    ),
                    None,
                )
                uow.get_repository(version.VersionPrimaryKey, version.Version).add(version_entity)

            product_entity = uow.get_repository(product.ProductPrimaryKey, product.Product).get(
                product.ProductPrimaryKey(projectId=product_obj.projectId, productId=product_obj.productId)
            )
            if not product_entity:
                uow.get_repository(product.ProductPrimaryKey, product.Product).add(product_obj)
            else:
                uow.get_repository(product.ProductPrimaryKey, product.Product).update_attributes(
                    product.ProductPrimaryKey(projectId=product_obj.projectId, productId=product_obj.productId),
                    **product_obj.dict(),
                )
            uow.commit()
