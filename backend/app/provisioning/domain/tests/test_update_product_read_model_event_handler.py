from unittest import mock

import pytest
from freezegun import freeze_time

from app.provisioning.domain.event_handlers import (
    update_product_read_model_event_handler,
)
from app.provisioning.domain.ports import (
    publishing_query_service,
    versions_query_service,
)
from app.provisioning.domain.read_models import (
    component_version_detail,
    product,
    version,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work

TEST_OS_VERSION = "Ubuntu 24"
TEST_COMPONENT_VERSION_DETAILS = [
    component_version_detail.ComponentVersionDetail(
        componentName="VS Code",
        componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
        softwareVendor="Microsoft",
        softwareVersion="1.87.0",
    ),
    component_version_detail.ComponentVersionDetail(
        componentName="Pied Piper",
        componentVersionType=component_version_detail.ComponentVersionEntryType.Helper,
        softwareVendor="PiperSoft",
        softwareVersion="0.5.2",
    ),
]


@pytest.fixture
def versions_repo_mock():
    vers_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)
    return vers_repo_mock


@pytest.fixture()
def get_sample_product():
    return product.Product(
        projectId="proj-123",
        productId="prod-123",
        technologyId="tech-123",
        technologyName="BRAIN",
        productName="mock_product_name",
        productType=product.ProductType.Workbench,
        productDescription="Mock product description",
        availableStages=[],
        availableRegions=[],
        pausedStages=[],
        pausedRegions=[],
        lastUpdateDate="2023-10-25T00:00:00+00:00",
        averageProvisioningTime=None,
        totalReportedTimes=None,
    )


@pytest.fixture
def products_repo_mock(get_sample_product):
    prod_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)
    prod_repo_mock.get.return_value = get_sample_product
    return prod_repo_mock


@pytest.fixture
def uow_mock(versions_repo_mock, products_repo_mock):
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork, instance=True)
    repos_dict = {
        version.Version: versions_repo_mock,
        product.Product: products_repo_mock,
    }
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    return uow_mock


@pytest.fixture()
def versions_qry_svc_mock():
    qry_svc = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    return qry_svc


@pytest.fixture()
def publishing_qry_svc_mock():
    qry_svc = mock.create_autospec(spec=publishing_query_service.PublishingQueryService)
    return qry_svc


@pytest.fixture()
def get_sample_version():
    def _get_sample_version(
        index,
        stage=version.VersionStage.DEV,
        time="2023-10-25T00:00:00+00:00",
        os_version=TEST_OS_VERSION,
        set_default_component_version_details=True,
    ):
        if set_default_component_version_details:
            component_version_details = TEST_COMPONENT_VERSION_DETAILS
        else:
            component_version_details = None
        return version.Version(
            projectId="proj-123",
            productId="prod-123",
            technologyId="tech-123",
            versionId=f"vers-{index}",
            versionName="1.0.0",
            versionDescription="version description",
            awsAccountId="105249321508",
            accountId="acct-12345",
            stage=stage,
            region="us-east-1",
            amiId="ami-12345",
            scProductId="prod-12345",
            scProvisioningArtifactId="pa-12345",
            isRecommendedVersion=True,
            componentVersionDetails=component_version_details,
            osVersion=os_version,
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
                    isTechnicalParameter=(True if i % 2 else False),
                )
                for i in range(5)
            ],
            lastUpdateDate=time,
        )

    return _get_sample_version


@pytest.fixture()
def get_sample_versions(get_sample_version):
    def _get_sample_versions(
        stage: version.VersionStage = version.VersionStage.DEV,
        time="2023-10-25T00:00:00+00:00",
        start_index=0,
        os_version=TEST_OS_VERSION,
        set_default_component_version_details=True,
    ):
        return [
            get_sample_version(
                i,
                stage,
                time,
                os_version=os_version,
                set_default_component_version_details=set_default_component_version_details,
            )
            for i in range(start_index, 5)
        ]

    return _get_sample_versions


@freeze_time("2023-10-25")
def test_updates_versions_when_version_id_is_in_event_and_repo(
    uow_mock,
    get_sample_product,
    versions_qry_svc_mock,
    get_sample_versions,
    versions_repo_mock,
    publishing_qry_svc_mock,
):
    # ARRANGE
    versions_qry_svc_mock.get_product_version_distributions.return_value = get_sample_versions()
    publishing_qry_svc_mock.get_available_product_versions.return_value = get_sample_versions(version.VersionStage.PROD)
    # ACT
    update_product_read_model_event_handler.handle(
        product_obj=get_sample_product,
        uow=uow_mock,
        versions_qry_srv=versions_qry_svc_mock,
        publishing_qry_srv=publishing_qry_svc_mock,
    )
    # ASSERT
    calls = [
        mock.call(
            version.VersionPrimaryKey(productId="prod-123", versionId=f"vers-{i}", awsAccountId="105249321508"),
            **{
                "projectId": "proj-123",
                "productId": "prod-123",
                "technologyId": "tech-123",
                "versionId": f"vers-{i}",
                "versionName": "1.0.0",
                "versionDescription": "version description",
                "awsAccountId": "105249321508",
                "accountId": "acct-12345",
                "stage": version.VersionStage.PROD,
                "region": "us-east-1",
                "amiId": "ami-12345",
                "scProductId": "prod-12345",
                "scProvisioningArtifactId": "pa-12345",
                "isRecommendedVersion": True,
                "componentVersionDetails": TEST_COMPONENT_VERSION_DETAILS,
                "osVersion": TEST_OS_VERSION,
                "parameters": [
                    version.VersionParameter(
                        parameterKey=f"{param_index}",
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
                        isTechnicalParameter=(True if param_index % 2 else False),
                    ).dict()
                    for param_index in range(5)
                ],
                "lastUpdateDate": "2023-10-25T00:00:00+00:00",
                "metadata": None,
            },
        )
        for i in range(5)
    ]

    versions_repo_mock.update_attributes.assert_has_calls(calls=calls, any_order=True)
    uow_mock.commit.assert_called_once()


def test_removes_version_when_only_in_db(
    uow_mock,
    versions_qry_svc_mock,
    get_sample_versions,
    versions_repo_mock,
    get_sample_product,
    publishing_qry_svc_mock,
):
    # ARRANGE
    versions_qry_svc_mock.get_product_version_distributions.return_value = get_sample_versions()
    publishing_qry_svc_mock.get_available_product_versions.return_value = get_sample_versions(
        version.VersionStage.PROD, start_index=2
    )

    # ACT
    update_product_read_model_event_handler.handle(
        product_obj=get_sample_product,
        uow=uow_mock,
        versions_qry_srv=versions_qry_svc_mock,
        publishing_qry_srv=publishing_qry_svc_mock,
    )
    # ASSERT
    calls = [
        mock.call(version.VersionPrimaryKey(productId="prod-123", versionId=f"vers-{i}", awsAccountId="105249321508"))
        for i in range(2)
    ]
    versions_repo_mock.remove.assert_has_calls(calls=calls, any_order=True)
    uow_mock.commit.assert_called_once()


@freeze_time("2023-10-25")
def test_adds_version_to_repo_when_only_in_event(
    get_sample_version,
    uow_mock,
    versions_qry_svc_mock,
    versions_repo_mock,
    get_sample_product,
    get_sample_versions,
    publishing_qry_svc_mock,
):
    # ARRANGE
    publishing_qry_svc_mock.get_available_product_versions.return_value = get_sample_versions()
    # ACT
    update_product_read_model_event_handler.handle(
        product_obj=get_sample_product,
        uow=uow_mock,
        versions_qry_srv=versions_qry_svc_mock,
        publishing_qry_srv=publishing_qry_svc_mock,
    )
    # ASSERT
    calls = [
        mock.call(
            get_sample_version(
                i,
            )
        )
        for i in range(5)
    ]
    versions_repo_mock.add.assert_has_calls(calls=calls, any_order=True)
    uow_mock.commit.assert_called_once()


def test_removes_product_if_no_versions(
    uow_mock,
    versions_qry_svc_mock,
    products_repo_mock,
    get_sample_product,
    publishing_qry_svc_mock,
    get_sample_versions,
    versions_repo_mock,
):
    # ARRANGE
    versions_qry_svc_mock.get_product_version_distributions.return_value = get_sample_versions()
    publishing_qry_svc_mock.get_available_product_versions.return_value = []

    # ACT
    update_product_read_model_event_handler.handle(
        product_obj=get_sample_product,
        uow=uow_mock,
        versions_qry_srv=versions_qry_svc_mock,
        publishing_qry_srv=publishing_qry_svc_mock,
    )
    # ASSERT
    products_repo_mock.remove.assert_called_once()
    calls = [
        mock.call(
            version.VersionPrimaryKey(
                **{
                    "productId": "prod-123",
                    "versionId": f"vers-{i}",
                    "awsAccountId": "105249321508",
                }
            )
        )
        for i in range(5)
    ]
    versions_repo_mock.remove.assert_has_calls(calls=calls, any_order=True)
    uow_mock.commit.assert_called_once()


def test_add_product_to_repo_if_product_does_not_exists(
    get_sample_version,
    uow_mock,
    versions_qry_svc_mock,
    products_repo_mock,
    get_sample_product,
    get_sample_versions,
    publishing_qry_svc_mock,
):
    # ARRANGE
    products_repo_mock.get.return_value = None
    publishing_qry_svc_mock.get_available_product_versions.return_value = get_sample_versions()

    # ACT
    update_product_read_model_event_handler.handle(
        product_obj=get_sample_product,
        uow=uow_mock,
        versions_qry_srv=versions_qry_svc_mock,
        publishing_qry_srv=publishing_qry_svc_mock,
    )
    # ASSERT
    products_repo_mock.add.assert_called_once_with(
        product.Product(
            projectId="proj-123",
            productId="prod-123",
            technologyId="tech-123",
            technologyName="BRAIN",
            productName="mock_product_name",
            productType=product.ProductType.Workbench,
            productDescription="Mock product description",
            availableStages=[],
            availableRegions=[],
            pausedStages=[],
            pausedRegions=[],
            lastUpdateDate="2023-10-25T00:00:00+00:00",
            availableTools=set(["VS Code", "Pied Piper"]),
            availableOSVersions=set(["Ubuntu 24"]),
        )
    )
    uow_mock.commit.assert_called_once()


def test_update_product_if_product_already_exists(
    get_sample_version,
    uow_mock,
    versions_qry_svc_mock,
    products_repo_mock,
    get_sample_product,
    get_sample_versions,
    publishing_qry_svc_mock,
):
    # ARRANGE
    publishing_qry_svc_mock.get_available_product_versions.return_value = get_sample_versions()

    # ACT
    update_product_read_model_event_handler.handle(
        product_obj=get_sample_product,
        uow=uow_mock,
        versions_qry_srv=versions_qry_svc_mock,
        publishing_qry_srv=publishing_qry_svc_mock,
    )
    # ASSERT
    products_repo_mock.update_attributes.assert_called_once_with(
        product.ProductPrimaryKey(projectId="proj-123", productId="prod-123"),
        **{
            "projectId": "proj-123",
            "productId": "prod-123",
            "technologyId": "tech-123",
            "technologyName": "BRAIN",
            "productName": "mock_product_name",
            "productType": product.ProductType.Workbench,
            "productDescription": "Mock product description",
            "availableStages": [],
            "availableRegions": [],
            "pausedStages": [],
            "pausedRegions": [],
            "lastUpdateDate": "2023-10-25T00:00:00+00:00",
            "averageProvisioningTime": None,
            "totalReportedTimes": None,
            "availableTools": set(["VS Code", "Pied Piper"]),
            "availableOSVersions": set(["Ubuntu 24"]),
            "costForecastDetails": None,
        },
    )
    uow_mock.commit.assert_called_once()


def test_do_not_set_product_available_tools_if_component_version_details_is_none(
    uow_mock,
    get_sample_product,
    publishing_qry_svc_mock,
    versions_qry_svc_mock,
    get_sample_versions,
    versions_repo_mock,
    products_repo_mock,
):
    # ARRANGE
    versions_qry_svc_mock.get_product_version_distributions.return_value = get_sample_versions()
    publishing_qry_svc_mock.get_available_product_versions.return_value = get_sample_versions(
        version.VersionStage.PROD,
        set_default_component_version_details=False,
        os_version=None,
    )

    # ACT
    update_product_read_model_event_handler.handle(
        product_obj=get_sample_product,
        uow=uow_mock,
        versions_qry_srv=versions_qry_svc_mock,
        publishing_qry_srv=publishing_qry_svc_mock,
    )
    # ASSERT
    calls = [
        mock.call(
            version.VersionPrimaryKey(productId="prod-123", versionId=f"vers-{i}", awsAccountId="105249321508"),
            **{
                "projectId": "proj-123",
                "productId": "prod-123",
                "technologyId": "tech-123",
                "versionId": f"vers-{i}",
                "versionName": "1.0.0",
                "versionDescription": "version description",
                "awsAccountId": "105249321508",
                "accountId": "acct-12345",
                "stage": version.VersionStage.PROD,
                "region": "us-east-1",
                "amiId": "ami-12345",
                "scProductId": "prod-12345",
                "scProvisioningArtifactId": "pa-12345",
                "isRecommendedVersion": True,
                "componentVersionDetails": None,
                "osVersion": None,
                "parameters": [
                    version.VersionParameter(
                        parameterKey=f"{param_index}",
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
                        isTechnicalParameter=(True if param_index % 2 else False),
                    ).dict()
                    for param_index in range(5)
                ],
                "lastUpdateDate": "2023-10-25T00:00:00+00:00",
                "metadata": None,
            },
        )
        for i in range(5)
    ]

    versions_repo_mock.update_attributes.assert_has_calls(calls=calls, any_order=True)
    products_repo_mock.update_attributes.assert_called_once_with(
        product.ProductPrimaryKey(projectId="proj-123", productId="prod-123"),
        **{
            "projectId": "proj-123",
            "productId": "prod-123",
            "technologyId": "tech-123",
            "technologyName": "BRAIN",
            "productName": "mock_product_name",
            "productType": product.ProductType.Workbench,
            "productDescription": "Mock product description",
            "availableStages": [],
            "availableRegions": [],
            "pausedStages": [],
            "pausedRegions": [],
            "lastUpdateDate": "2023-10-25T00:00:00+00:00",
            "averageProvisioningTime": None,
            "totalReportedTimes": None,
            "availableTools": None,
            "availableOSVersions": None,
            "costForecastDetails": None,
        },
    )
    uow_mock.commit.assert_called_once()
