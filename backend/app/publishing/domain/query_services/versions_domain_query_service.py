import typing

from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import version, version_summary
from app.publishing.domain.ports import template_service, versions_query_service
from app.publishing.domain.query_services.helpers import version_helpers
from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    product_id_value_object,
    region_value_object,
    stage_value_object,
    version_id_value_object,
)


class VersionsDomainQueryService:
    def __init__(
        self,
        version_qry_srv: versions_query_service.VersionsQueryService,
        file_srv: template_service.TemplateService,
        default_original_ami_region: str,
    ):
        self._version_qry_srv = version_qry_srv
        self._file_srv = file_srv
        self._default_original_ami_region = default_original_ami_region

    def get_latest_version_name(self, product_id: str) -> str:
        return self._version_qry_srv.get_latest_version_name_and_id(product_id=product_id)[0]

    def get_version_distribution(
        self,
        product_id: product_id_value_object.ProductIdValueObject,
        version_id: version_id_value_object.VersionIdValueObject,
        aws_account_id: aws_account_id_value_object.AWSAccountIDValueObject,
    ) -> version.Version | None:
        version_distribution = self._version_qry_srv.get_product_version_distribution(
            product_id=product_id.value, version_id=version_id.value, aws_account_id=aws_account_id.value
        )
        if version_distribution:
            vers_data = version_distribution.model_dump()
            vers_data["amiId"] = version_distribution.copiedAmiId
            return vers_data

    def get_product_version(
        self,
        product_id: product_id_value_object.ProductIdValueObject,
        version_id: version_id_value_object.VersionIdValueObject,
    ) -> typing.Tuple[typing.Optional[version_summary.VersionSummary], typing.List[version.Version], str]:
        distributions = self._version_qry_srv.get_product_version_distributions(
            product_id=product_id.value, version_id=version_id.value
        )

        if not distributions:
            raise domain_exception.DomainException(f"Could not find version with id {version_id.value}")

        summary = version_helpers.get_summary(distributions)

        if not distributions[0].draftTemplateLocation:
            raise domain_exception.DomainException(f"Could not find draft template path for {version_id.value}.")

        # Download the draft template
        local_template_path = self._file_srv.get_template(template_path=distributions[0].draftTemplateLocation)
        if not local_template_path:
            raise domain_exception.DomainException(f"Could not find draft template file for {version_id.value}.")

        # Read the draft template
        with open(local_template_path, "rb") as f:
            draft_template = f.read()

        return summary, distributions, draft_template.decode()

    def get_versions_ready_for_provisioning(
        self,
        product_id: product_id_value_object.ProductIdValueObject,
        stage: stage_value_object.StageValueObject,
        region: region_value_object.RegionValueObject,
    ) -> typing.List[version.Version]:
        distributions = self._version_qry_srv.get_product_version_distributions(
            product_id=product_id.value,
            stage=stage.value,
            region=region.value,
            statuses=[version.VersionStatus.Created],
        )

        return distributions

    def get_enriched_versions_ready_for_provisioning(
        self,
        product_id: product_id_value_object.ProductIdValueObject,
        version_id: version_id_value_object.VersionIdValueObject | None = None,
    ) -> typing.List[dict]:
        distributions = self._version_qry_srv.get_product_version_distributions(
            product_id=product_id.value,
            version_id=version_id.value if version_id else None,
            statuses=[version.VersionStatus.Created],
        )

        enriched_versions = []
        for vers in distributions:
            vers_data = vers.model_dump()
            vers_data["amiId"] = vers.copiedAmiId
            enriched_versions.append(vers_data)

        return enriched_versions

    def get_latest_major_version_summaries(
        self, product_id: product_id_value_object.ProductIdValueObject
    ) -> list[version_summary.VersionSummary]:
        # Get CREATED version distributions
        distributions = self._version_qry_srv.get_product_version_distributions(
            product_id=product_id.value,
            statuses=[version.VersionStatus.Created],
        )
        if not distributions:
            return []

        # Parse version summaries
        distribution_map: dict[str, list[version.Version]] = {}
        for distribution in distributions:
            if distribution.versionId in distribution_map:
                distribution_map[distribution.versionId].append(distribution)
            else:
                distribution_map[distribution.versionId] = [distribution]
        version_summaries = [version_helpers.get_summary(d) for id, d in distribution_map.items()]

        # Filter the version summaries to only contain latest major versions
        major_versions: dict[str, version_summary.VersionSummary] = {}
        for vers in version_summaries:
            major = vers.name.split(".")[0]
            if major not in major_versions or vers.name > major_versions[major].name:
                major_versions[major] = vers

        # Return list of latest major versions
        return major_versions.values()
