import typing
from datetime import datetime, timezone

from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.value_objects import user_id_value_object
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class RecommendedVersionAggregate:
    def __init__(
        self,
        product: product.Product,
        recommended_version_distributions: list[version.Version],
        product_repository: unit_of_work.GenericRepository[product.ProductPrimaryKey, product.Product],
        version_repository: unit_of_work.GenericRepository[version.VersionPrimaryKey, version.Version],
    ) -> None:
        self._product = product
        self._recommended_version_distributions = recommended_version_distributions
        self._product_repository = product_repository
        self._version_repository = version_repository

    def set_new(
        self,
        new_recommended_version_distributions: list[version.Version],
        user_id: user_id_value_object.UserIdValueObject,
    ):
        version_id = self._validate_and_get_new_recommended_version_id(new_recommended_version_distributions)
        self._validate_new_distributions_are_published_to_prod(new_recommended_version_distributions, version_id)
        self._validate_all_prod_distributions_are_created_state(new_recommended_version_distributions)

        current_time = datetime.now(timezone.utc).isoformat()

        self._product_repository.update_attributes(
            pk=product.ProductPrimaryKey(
                projectId=self._product.projectId,
                productId=self._product.productId,
            ),
            recommendedVersionId=version_id,
            lastUpdateDate=current_time,
            lastUpdatedBy=user_id.value,
        )

        for old_v in self._recommended_version_distributions:
            self._version_repository.update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=old_v.productId,
                    versionId=old_v.versionId,
                    awsAccountId=old_v.awsAccountId,
                ),
                isRecommendedVersion=False,
                lastUpdateDate=current_time,
                lastUpdatedBy=user_id.value,
            )

        for new_v in new_recommended_version_distributions:
            self._version_repository.update_attributes(
                pk=version.VersionPrimaryKey(
                    productId=new_v.productId,
                    versionId=new_v.versionId,
                    awsAccountId=new_v.awsAccountId,
                ),
                isRecommendedVersion=True,
                lastUpdateDate=current_time,
                lastUpdatedBy=user_id.value,
            )

        self._recommended_version_distributions = new_recommended_version_distributions
        self._product.recommendedVersionId = version_id

    def validate(self) -> typing.Self:
        if not self._product:
            raise domain_exception.DomainException("Product does not exist in the specified program")

        if not self._product_repository:
            raise domain_exception.DomainException(
                "Recommended Product Version aggregate is not correctly initialised - missing products repository"
            )

        if not self._version_repository:
            raise domain_exception.DomainException(
                "Recommended Product Version aggregate is not correctly initialised - missing versions repository"
            )

        if next((v for v in self._recommended_version_distributions if not v.isRecommendedVersion), None):
            raise domain_exception.DomainException(
                "Current version distributions contain non-recommended versions in it"
            )

        return self

    def _validate_and_get_new_recommended_version_id(
        self, new_recommended_version_distributions: list[version.Version]
    ) -> str:
        version_ids = {v.versionId for v in new_recommended_version_distributions}

        if not version_ids:
            raise domain_exception.DomainException("Provided version distributions list is empty.")

        if len(version_ids) > 1:
            raise domain_exception.DomainException(
                "Provided new recommended version distributions must be of the same version ID."
            )

        return version_ids.pop()

    def _validate_new_distributions_are_published_to_prod(
        self, new_recommended_version_distributions: list[version.Version], version_id: str
    ):
        prod_version = next(
            (v for v in new_recommended_version_distributions if v.stage == version.VersionStage.PROD), None
        )
        if not prod_version:
            raise domain_exception.DomainException(f"Product version {version_id} is not published to PROD stage.")

    def _validate_all_prod_distributions_are_created_state(
        self, new_recommended_version_distributions: list[version.Version]
    ):
        non_created_prod_version = next(
            (
                v
                for v in new_recommended_version_distributions
                if v.stage == version.VersionStage.PROD and v.status != version.VersionStatus.Created
            ),
            None,
        )
        if non_created_prod_version:
            raise domain_exception.DomainException(
                f"Product version {non_created_prod_version.versionId} is not fully published to the PROD environment: {non_created_prod_version.status} status exists"
            )
