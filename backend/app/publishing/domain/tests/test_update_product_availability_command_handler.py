import logging
from collections import Counter
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import update_product_availability_command_handler
from app.publishing.domain.commands import update_product_availability_command
from app.publishing.domain.events import product_availability_updated
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import versions_query_service
from app.publishing.domain.value_objects import product_id_value_object, project_id_value_object
from app.shared.adapters.message_bus import message_bus


@pytest.fixture()
def command_mock() -> update_product_availability_command.UpdateProductAvailabilityCommand:
    return update_product_availability_command.UpdateProductAvailabilityCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        productId=product_id_value_object.from_str("prod-12345abc"),
    )


@pytest.fixture()
def get_product():
    def _get_product():
        return product.Product(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            technologyName="Test technology",
            status=product.ProductStatus.Created,
            productName="My product",
            productType=product.ProductType.Workbench,
            availableStages=[product.ProductStage.DEV, product.ProductStage.QA],
            availableRegions=["us-east-1", "eu-west-3"],
            createDate="2023-08-22T00:00:00+00:00",
            lastUpdateDate="2023-08-22T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
            productDescription="mock description",
        )

    return _get_product


@pytest.fixture
def get_test_version():
    def _get_test_version(
        version_id: str = "vers-12345abc",
        status: version.VersionStatus = version.VersionStatus.Created,
        stage: version.VersionStage = version.VersionStage.DEV,
        region: str = "us-east-1",
    ):
        return version.Version(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            versionId=version_id,
            versionName="1.0.0-rc.1",
            versionDescription="Test Description",
            versionType=version.VersionType.ReleaseCandidate.text,
            awsAccountId="123456789012",
            accountId="123467875435678",
            stage=stage,
            region=region,
            originalAmiId="ami-12345",
            copiedAmiId="cp-ami-12345",
            status=status,
            scPortfolioId="port-12345",
            scProductId="prod-12345",
            scProvisioningArtifactId="pa-12345",
            isRecommendedVersion=True,
            createDate="2023-08-22T00:00:00+00:00",
            lastUpdateDate="2023-08-22T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
            parameters=[
                version.VersionParameter(
                    parameterKey=f"{i}",
                    defaultValue="mock-value",
                    description="mock-description",
                    isNoEcho=False,
                    parameterType="mock-param-type",
                    parameterMetadata=version.ParameterMetadata(label="mock-label", optionLabels={"test": "label"}),
                    parameterConstraints=version.ParameterConstraints(
                        allowedPattern="mock-pattern",
                        allowedValues=["mock", "values"],
                        constraintDescription="mock-constraint-description",
                        maxLength="100",
                        maxValue="100",
                        minLength="100",
                        minValue="0",
                    ),
                ).dict()
                for i in range(5)
            ],
            metadata={"GenericMetadata": version.ProductVersionMetadataItem(label="Test", value=["Line items"])},
        )

    return _get_test_version


@pytest.fixture
def versions_query_service_mock(get_test_version):
    vers_qry_srv_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    return vers_qry_srv_mock


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@pytest.fixture()
def message_bus_mock():
    msg_mus = mock.create_autospec(spec=message_bus.MessageBus)
    return msg_mus


@pytest.mark.parametrize(
    "stages,regions",
    [
        pytest.param([], []),
        pytest.param([version.VersionStage.DEV], ["us-east-1"]),
        pytest.param([version.VersionStage.DEV, version.VersionStage.QA], ["us-east-1"]),
        pytest.param(
            [version.VersionStage.DEV, version.VersionStage.QA],
            ["us-east-1", "eu-west-3"],
        ),
        pytest.param(
            [
                version.VersionStage.DEV,
                version.VersionStage.QA,
                version.VersionStage.PROD,
            ],
            ["us-east-1", "eu-west-3"],
        ),
    ],
)
def test_update_product_availability_command_handler_updates_correct_stages_and_regions(
    stages,
    regions,
    command_mock,
    mock_products_repo,
    mock_unit_of_work,
    versions_query_service_mock,
    logger_mock,
    get_test_version,
    message_bus_mock,
    get_product,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()
    versions = []
    for stage in stages:
        for region in regions:
            versions.append(get_test_version(version_id=version.generate_version_id(), stage=stage, region=region))
            versions.append(get_test_version(version_id=version.generate_version_id(), stage=stage, region=region))
    versions_query_service_mock.get_product_version_distributions.side_effect = [
        [],
        versions,
    ]

    # ACT
    update_product_availability_command_handler.handle(
        command=command_mock,
        uow=mock_unit_of_work,
        versions_qry_srv=versions_query_service_mock,
        logger=logger_mock,
        message_bus=message_bus_mock,
    )

    # ASSERT
    updated_stages = mock_products_repo.update_attributes.call_args.kwargs["availableStages"]
    updated_regions = mock_products_repo.update_attributes.call_args.kwargs["availableRegions"]
    assertpy.assert_that(Counter(updated_stages)).is_equal_to(Counter(stages))
    assertpy.assert_that(Counter(updated_regions)).is_equal_to(Counter(regions))
    mock_unit_of_work.commit.assert_called_once()


def test_update_product_availability_command_handler_does_not_update_while_versions_are_processing(
    command_mock,
    uow_mock,
    versions_query_service_mock,
    logger_mock,
    get_test_version,
    message_bus_mock,
):
    # ARRANGE
    processing_versions = [
        get_test_version(
            version_id=version.generate_version_id(),
            status=version.VersionStatus.Creating,
        ),
        get_test_version(
            version_id=version.generate_version_id(),
            status=version.VersionStatus.Updating,
        ),
        get_test_version(
            version_id=version.generate_version_id(),
            status=version.VersionStatus.Retiring,
        ),
        get_test_version(
            version_id=version.generate_version_id(),
            status=version.VersionStatus.Restoring,
        ),
    ]
    versions = [
        get_test_version(
            version_id=version.generate_version_id(),
            status=version.VersionStatus.Created,
        ),
    ]
    versions_query_service_mock.get_product_version_distributions.side_effect = [
        processing_versions,
        versions,
    ]

    # ACT
    update_product_availability_command_handler.handle(
        command=command_mock,
        uow=uow_mock,
        versions_qry_srv=versions_query_service_mock,
        logger=logger_mock,
        message_bus=message_bus_mock,
    )

    # ASSERT
    uow_mock.commit.assert_not_called()


@freeze_time("2023.08.22")
@pytest.mark.parametrize(
    "stages,regions",
    [
        pytest.param([], []),
        pytest.param([version.VersionStage.DEV], {"us-east-1"}),
        pytest.param([version.VersionStage.DEV, version.VersionStage.QA], {"us-east-1"}),
        pytest.param(
            [version.VersionStage.DEV, version.VersionStage.QA],
            {"us-east-1", "eu-west-3"},
        ),
        pytest.param(
            [
                version.VersionStage.DEV,
                version.VersionStage.QA,
                version.VersionStage.PROD,
            ],
            {"us-east-1", "eu-west-3"},
        ),
    ],
)
def test_update_product_availability_command_handler_publish_product_availability_updated_event(
    stages,
    regions,
    command_mock,
    mock_unit_of_work,
    versions_query_service_mock,
    logger_mock,
    get_test_version,
    message_bus_mock,
    mock_products_repo,
    get_product,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    regions = sorted(regions)
    versions = []
    version_id = 0
    for stage in stages:
        for region in regions:
            versions.append(get_test_version(version_id=version_id, stage=stage, region=region))
            version_id += 1
    versions_query_service_mock.get_product_version_distributions.side_effect = [
        [],
        versions,
    ]

    # ACT
    update_product_availability_command_handler.handle(
        command=command_mock,
        uow=mock_unit_of_work,
        versions_qry_srv=versions_query_service_mock,
        logger=logger_mock,
        message_bus=message_bus_mock,
    )
    # ASSERT
    message_bus_mock.publish.assert_called_once_with(
        product_availability_updated.ProductAvailabilityUpdated(
            projectId="proj-12345",
            productId="prod-12345abc",
            productType=product.ProductType.Workbench,
            productName="My product",
            productDescription="mock description",
            technologyId="tech-12345",
            technologyName="Test technology",
            availableStages=stages,
            availableRegions=regions,
            lastUpdateDate="2023-08-22T00:00:00+00:00",
        )
    )
