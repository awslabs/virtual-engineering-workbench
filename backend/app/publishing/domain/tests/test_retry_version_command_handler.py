from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import retry_version_command_handler
from app.publishing.domain.commands import retry_version_command
from app.publishing.domain.events import product_version_retry_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import version
from app.publishing.domain.ports import versions_query_service
from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    product_id_value_object,
    project_id_value_object,
    user_id_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import message_bus


def sample_versions() -> list[version.Version]:
    return [
        version.Version(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            versionId="vers-12345abc",
            versionName="1.0.0-rc.2",
            versionType=version.VersionType.ReleaseCandidate.text,
            awsAccountId="123456789012",
            stage=version.VersionStage.DEV,
            region="us-east-1",
            originalAmiId="ami-12345",
            status=version.VersionStatus.Failed,
            scPortfolioId="port-12345",
            isRecommendedVersion=True,
            createDate="2023-07-13T00:00:00+00:00",
            lastUpdateDate="2023-07-13T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        ),
        version.Version(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            versionId="vers-12345abc",
            versionName="1.0.0-rc.2",
            versionType=version.VersionType.ReleaseCandidate.text,
            awsAccountId="123456789013",  # This is the only difference in 2 versions
            stage=version.VersionStage.DEV,
            region="us-east-1",
            originalAmiId="ami-12345",
            status=version.VersionStatus.Failed,
            scPortfolioId="port-12345",
            isRecommendedVersion=True,
            createDate="2023-07-13T00:00:00+00:00",
            lastUpdateDate="2023-07-13T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        ),
    ]


@pytest.fixture()
def command_mock() -> retry_version_command.RetryVersionCommand:
    return retry_version_command.RetryVersionCommand(
        projectId=project_id_value_object.from_str("proj-123"),
        productId=product_id_value_object.from_str("prod-12345abc"),
        versionId=version_id_value_object.from_str("vers-12345abc"),
        awsAccountIds=[aws_account_id_value_object.from_str("123456789012")],
        lastUpdatedBy=user_id_value_object.from_str("T000002"),
    )


@pytest.fixture
def versions_query_service_mock():
    versions_qry_srv_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    versions_qry_srv_mock.get_product_version_distributions.return_value = sample_versions()
    return versions_qry_srv_mock


@pytest.fixture
def message_bus_mock():
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    return message_bus_mock


@freeze_time("2023-07-24")
def test_retry_version_updates_versions_and_publishes_events(
    command_mock,
    mock_unit_of_work,
    versions_query_service_mock,
    message_bus_mock,
    mock_version_repo,
    product_query_service_mock,
    get_sample_product,
):
    # ARRANGE
    product_query_service_mock.get_product.return_value = get_sample_product(product_id="prod-12345abc")
    # ACT
    retry_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        versions_qry_srv=versions_query_service_mock,
        message_bus=message_bus_mock,
        product_qry_srv=product_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(mock_version_repo.update_attributes.call_count).is_equal_to(2)
    mock_version_repo.update_attributes.assert_has_calls(
        [
            mock.call(
                pk=version.VersionPrimaryKey(
                    productId="prod-12345abc",
                    versionId="vers-12345abc",
                    awsAccountId="123456789012",
                ),
                lastUpdateDate="2023-07-24T00:00:00+00:00",
                lastUpdatedBy="T000002",
                status=version.VersionStatus.Updating,
            ),
            mock.call(
                pk=version.VersionPrimaryKey(
                    productId="prod-12345abc",
                    versionId="vers-12345abc",
                    awsAccountId="123456789013",
                ),
                lastUpdateDate="2023-07-24T00:00:00+00:00",
                lastUpdatedBy="T000002",
                status=version.VersionStatus.Updating,
            ),
        ]
    )
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(2)
    assertpy.assert_that(message_bus_mock.publish.call_count).is_equal_to(2)
    message_bus_mock.publish.assert_has_calls(
        [
            mock.call(
                product_version_retry_started.ProductVersionRetryStarted(
                    product_id="prod-12345abc",
                    version_id="vers-12345abc",
                    aws_account_id="123456789012",
                    product_type="WORKBENCH",
                )
            ),
            mock.call(
                product_version_retry_started.ProductVersionRetryStarted(
                    product_id="prod-12345abc",
                    version_id="vers-12345abc",
                    aws_account_id="123456789013",
                    product_type="WORKBENCH",
                )
            ),
        ]
    )


@freeze_time("2023-07-24")
def test_retry_version_raises_exception_if_version_status_is_not_failed(
    command_mock,
    mock_unit_of_work,
    versions_query_service_mock,
    message_bus_mock,
    mock_version_repo,
    product_query_service_mock,
    get_sample_product,
):
    # ARRANGE
    product_query_service_mock.get_product.return_value = get_sample_product(product_id="prod-12345abc")

    versions = sample_versions()
    versions[0].status = version.VersionStatus.Created
    versions_query_service_mock.get_product_version_distributions.return_value = versions

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException):
        retry_version_command_handler.handle(
            cmd=command_mock,
            uow=mock_unit_of_work,
            versions_qry_srv=versions_query_service_mock,
            message_bus=message_bus_mock,
            product_qry_srv=product_query_service_mock,
        )
