import tempfile
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import restore_version_command_handler
from app.publishing.domain.commands import restore_version_command
from app.publishing.domain.events import product_version_restoration_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import portfolio, product, version
from app.publishing.domain.ports import (
    portfolios_query_service,
    template_service,
    versions_query_service,
)
from app.publishing.domain.query_services import template_domain_query_service
from app.publishing.domain.read_models import component_version_detail
from app.publishing.domain.value_objects import (
    product_id_value_object,
    project_id_value_object,
    user_id_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.api import parameter_service


@pytest.fixture()
def command_mock() -> restore_version_command.RestoreVersionCommand:
    return restore_version_command.RestoreVersionCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        productId=product_id_value_object.from_str("prod-12345abc"),
        versionId=version_id_value_object.from_str("vers-12345abc"),
        restoredBy=user_id_value_object.from_str("T000001"),
    )


@pytest.fixture
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
            createDate="2023-08-17T00:00:00+00:00",
            lastUpdateDate="2023-08-17T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        )

    return _get_product


@pytest.fixture()
def get_test_version():
    def _get_test_version(
        aws_account_id: str = "123456789012",
        status: str = version.VersionStatus.Retired,
        version_name: str = "2.3.4",
        version_type: str = version.VersionType.Released.text,
    ):
        return version.Version(
            projectId="proj-12345",
            productId="prod-12345abc",
            technologyId="tech-12345",
            versionId="vers-12345abc",
            versionName=version_name,
            versionType=version_type,
            awsAccountId=aws_account_id,
            stage=version.VersionStage.DEV,
            region="us-east-1",
            originalAmiId="ami-12345",
            copiedAmiId="ami-12345",
            status=status,
            scPortfolioId="port-12345",
            isRecommendedVersion=True,
            componentVersionDetails=[
                component_version_detail.ComponentVersionDetail(
                    componentName="VS Code",
                    componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
                    softwareVendor="Microsoft",
                    softwareVersion="1.87.0",
                )
            ],
            osVersion="Ubuntu 24",
            createDate="2023-08-17T00:00:00+00:00",
            lastUpdateDate="2023-08-17T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
        )

    return _get_test_version


@pytest.fixture
def versions_query_service_mock(get_test_version):
    vers_qry_srv_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    vers_qry_srv_mock.get_product_version_distributions.return_value = [
        get_test_version(),
        get_test_version(aws_account_id="123456789013"),
    ]
    vers_qry_srv_mock.get_latest_version_name_and_id.return_value = None, None
    vers_qry_srv_mock.get_distinct_number_of_versions.return_value = 1
    return vers_qry_srv_mock


@pytest.fixture
def portfolios_query_service_mock():
    portf_qry_srv_mock = mock.create_autospec(spec=portfolios_query_service.PortfoliosQueryService)
    portf_qry_srv_mock.get_portfolios_by_tech_and_stage.return_value = [
        portfolio.Portfolio(
            portfolioId="port-12345abc",
            scPortfolioId="port-12345",
            projectId="proj-12345",
            technologyId="tech-12345",
            awsAccountId="123456789012",
            accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
            stage=portfolio.PortfolioStage.DEV,
            region="us-east-1",
            status=portfolio.PortfolioStatus.Created,
            createDate="2023-08-17T00:00:00+00:00",
            lastUpdateDate="2023-08-17T00:00:00+00:00",
        ),
        portfolio.Portfolio(
            portfolioId="port-12345abc",
            scPortfolioId="port-12345",
            projectId="proj-12345",
            technologyId="tech-12345",
            awsAccountId="123456789013",
            accountId="60f4a16c-a8f3-45e0-8c57-ff3b3364cd13",
            stage=portfolio.PortfolioStage.DEV,
            region="us-east-1",
            status=portfolio.PortfolioStatus.Created,
            createDate="2023-08-17T00:00:00+00:00",
            lastUpdateDate="2023-08-17T00:00:00+00:00",
        ),
    ]
    return portf_qry_srv_mock


@pytest.fixture
def message_bus_mock():
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    return message_bus_mock


@pytest.fixture
def parameter_service_mock():
    param_service_mock = mock.create_autospec(spec=parameter_service.ParameterService)
    param_service_mock.get_parameter_value.return_value = 10
    return param_service_mock


@pytest.fixture
def file_service_mock():
    file_mock = mock.create_autospec(spec=template_service.TemplateService)
    file_mock.put_template.return_value = None
    file_mock.does_template_exist.return_value = False
    return file_mock


@pytest.fixture
def template_service_mock():
    temp_mock = mock.create_autospec(spec=template_domain_query_service.TemplateDomainQueryService)
    temp_mock.get_default_template_file_name.return_value = "draft_workbench.yml"
    return temp_mock


@freeze_time("2023-08-17")
def test_restore_version_command_handler_starts_restoration_in_dev(
    command_mock,
    mock_version_repo,
    mock_unit_of_work,
    versions_query_service_mock,
    portfolios_query_service_mock,
    message_bus_mock,
    parameter_service_mock,
    file_service_mock,
    template_service_mock,
    mock_products_repo,
    get_product,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    temp_file = tempfile.NamedTemporaryFile(delete=False)

    temp_file.write(b"Existing version template")
    temp_file.close()

    file_service_mock.get_template.return_value = temp_file.name

    # ACT
    new_version_name = restore_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        msg_bus=message_bus_mock,
        portfolios_qry_srv=portfolios_query_service_mock,
        versions_qry_srv=versions_query_service_mock,
        param_service=parameter_service_mock,
        product_version_limit_param_name="workbench_version_limit",
        file_service=file_service_mock,
        template_query_service=template_service_mock,
    )

    # ASSERT
    version_id = mock_version_repo.add.call_args.args[0].versionId
    mock_version_repo.add.assert_has_calls(
        [
            mock.call(
                version.Version(
                    projectId="proj-12345",
                    productId="prod-12345abc",
                    technologyId="tech-12345",
                    versionId=version_id,
                    versionName="2.3.4-restored.1",
                    versionType=version.VersionType.Restored.text,
                    draftTemplateLocation=f"prod-12345abc/{version_id}/draft_workbench.yml",
                    awsAccountId="123456789012",
                    accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
                    stage=version.VersionStage.DEV,
                    region="us-east-1",
                    originalAmiId="ami-12345",
                    status=version.VersionStatus.Creating,
                    scPortfolioId="port-12345",
                    isRecommendedVersion=False,
                    restoredFromVersionName="2.3.4",
                    componentVersionDetails=[
                        component_version_detail.ComponentVersionDetail(
                            componentName="VS Code",
                            componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
                            softwareVendor="Microsoft",
                            softwareVersion="1.87.0",
                        )
                    ],
                    osVersion="Ubuntu 24",
                    createDate="2023-08-17T00:00:00+00:00",
                    lastUpdateDate="2023-08-17T00:00:00+00:00",
                    createdBy="T000001",
                    lastUpdatedBy="T000001",
                )
            ),
            mock.call(
                version.Version(
                    projectId="proj-12345",
                    productId="prod-12345abc",
                    technologyId="tech-12345",
                    versionId=version_id,
                    versionName="2.3.4-restored.1",
                    versionType=version.VersionType.Restored.text,
                    draftTemplateLocation=f"prod-12345abc/{version_id}/draft_workbench.yml",
                    awsAccountId="123456789013",
                    accountId="60f4a16c-a8f3-45e0-8c57-ff3b3364cd13",
                    stage=version.VersionStage.DEV,
                    region="us-east-1",
                    originalAmiId="ami-12345",
                    status=version.VersionStatus.Creating,
                    scPortfolioId="port-12345",
                    isRecommendedVersion=False,
                    restoredFromVersionName="2.3.4",
                    componentVersionDetails=[
                        component_version_detail.ComponentVersionDetail(
                            componentName="VS Code",
                            componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
                            softwareVendor="Microsoft",
                            softwareVersion="1.87.0",
                        )
                    ],
                    osVersion="Ubuntu 24",
                    createDate="2023-08-17T00:00:00+00:00",
                    lastUpdateDate="2023-08-17T00:00:00+00:00",
                    createdBy="T000001",
                    lastUpdatedBy="T000001",
                )
            ),
        ]
    )
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(2)
    message_bus_mock.publish.assert_has_calls(
        [
            mock.call(
                product_version_restoration_started.ProductVersionRestorationStarted(
                    productId="prod-12345abc",
                    versionId=version_id,
                    awsAccountId="123456789012",
                    oldVersionId="vers-12345abc",
                    product_type="WORKBENCH",
                )
            ),
            mock.call(
                product_version_restoration_started.ProductVersionRestorationStarted(
                    productId="prod-12345abc",
                    versionId=version_id,
                    awsAccountId="123456789013",
                    oldVersionId="vers-12345abc",
                    product_type="WORKBENCH",
                )
            ),
        ]
    )
    assertpy.assert_that(new_version_name).is_equal_to("2.3.4-restored.1")


@freeze_time("2023-08-17")
def test_restore_version_command_handler_increases_restored_version_counter(
    command_mock,
    mock_version_repo,
    mock_unit_of_work,
    versions_query_service_mock,
    portfolios_query_service_mock,
    message_bus_mock,
    parameter_service_mock,
    file_service_mock,
    template_service_mock,
    mock_products_repo,
    get_product,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    temp_file = tempfile.NamedTemporaryFile(delete=False)

    temp_file.write(b"Existing version template")
    temp_file.close()

    file_service_mock.get_template.return_value = temp_file.name
    versions_query_service_mock.get_latest_version_name_and_id.return_value = (
        "2.3.4-restored.1",
        "vers-1234",
    )

    # ACT
    new_version_name = restore_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        msg_bus=message_bus_mock,
        portfolios_qry_srv=portfolios_query_service_mock,
        versions_qry_srv=versions_query_service_mock,
        param_service=parameter_service_mock,
        product_version_limit_param_name="workbench_version_limit",
        file_service=file_service_mock,
        template_query_service=template_service_mock,
    )

    # ASSERT
    version_id = mock_version_repo.add.call_args.args[0].versionId
    mock_version_repo.add.assert_has_calls(
        [
            mock.call(
                version.Version(
                    projectId="proj-12345",
                    productId="prod-12345abc",
                    technologyId="tech-12345",
                    versionId=version_id,
                    versionName="2.3.4-restored.2",
                    versionType=version.VersionType.Restored.text,
                    draftTemplateLocation=f"prod-12345abc/{version_id}/draft_workbench.yml",
                    awsAccountId="123456789012",
                    accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
                    stage=version.VersionStage.DEV,
                    region="us-east-1",
                    originalAmiId="ami-12345",
                    status=version.VersionStatus.Creating,
                    scPortfolioId="port-12345",
                    isRecommendedVersion=False,
                    restoredFromVersionName="2.3.4",
                    componentVersionDetails=[
                        component_version_detail.ComponentVersionDetail(
                            componentName="VS Code",
                            componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
                            softwareVendor="Microsoft",
                            softwareVersion="1.87.0",
                        )
                    ],
                    osVersion="Ubuntu 24",
                    createDate="2023-08-17T00:00:00+00:00",
                    lastUpdateDate="2023-08-17T00:00:00+00:00",
                    createdBy="T000001",
                    lastUpdatedBy="T000001",
                )
            ),
            mock.call(
                version.Version(
                    projectId="proj-12345",
                    productId="prod-12345abc",
                    technologyId="tech-12345",
                    versionId=version_id,
                    versionName="2.3.4-restored.2",
                    versionType=version.VersionType.Restored.text,
                    draftTemplateLocation=f"prod-12345abc/{version_id}/draft_workbench.yml",
                    awsAccountId="123456789013",
                    accountId="60f4a16c-a8f3-45e0-8c57-ff3b3364cd13",
                    stage=version.VersionStage.DEV,
                    region="us-east-1",
                    originalAmiId="ami-12345",
                    status=version.VersionStatus.Creating,
                    scPortfolioId="port-12345",
                    isRecommendedVersion=False,
                    restoredFromVersionName="2.3.4",
                    componentVersionDetails=[
                        component_version_detail.ComponentVersionDetail(
                            componentName="VS Code",
                            componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
                            softwareVendor="Microsoft",
                            softwareVersion="1.87.0",
                        )
                    ],
                    osVersion="Ubuntu 24",
                    createDate="2023-08-17T00:00:00+00:00",
                    lastUpdateDate="2023-08-17T00:00:00+00:00",
                    createdBy="T000001",
                    lastUpdatedBy="T000001",
                )
            ),
        ]
    )
    assertpy.assert_that(mock_unit_of_work.commit.call_count).is_equal_to(2)
    message_bus_mock.publish.assert_has_calls(
        [
            mock.call(
                product_version_restoration_started.ProductVersionRestorationStarted(
                    productId="prod-12345abc",
                    versionId=version_id,
                    awsAccountId="123456789012",
                    oldVersionId="vers-12345abc",
                    product_type="WORKBENCH",
                )
            ),
            mock.call(
                product_version_restoration_started.ProductVersionRestorationStarted(
                    productId="prod-12345abc",
                    versionId=version_id,
                    awsAccountId="123456789013",
                    oldVersionId="vers-12345abc",
                    product_type="WORKBENCH",
                )
            ),
        ]
    )
    assertpy.assert_that(new_version_name).is_equal_to("2.3.4-restored.2")


@freeze_time("2023-08-17")
def test_restore_version_command_handler_raises_exception_when_all_prev_versions_are_not_retired(
    command_mock,
    mock_unit_of_work,
    versions_query_service_mock,
    portfolios_query_service_mock,
    message_bus_mock,
    get_test_version,
    parameter_service_mock,
    file_service_mock,
    template_service_mock,
    mock_products_repo,
    get_product,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    temp_file = tempfile.NamedTemporaryFile(delete=False)

    temp_file.write(b"Existing version template")
    temp_file.close()

    file_service_mock.get_template.return_value = temp_file.name
    versions_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(),
        get_test_version(aws_account_id="123456789013", status=version.VersionStatus.Failed),
    ]

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        restore_version_command_handler.handle(
            cmd=command_mock,
            uow=mock_unit_of_work,
            msg_bus=message_bus_mock,
            portfolios_qry_srv=portfolios_query_service_mock,
            versions_qry_srv=versions_query_service_mock,
            param_service=parameter_service_mock,
            product_version_limit_param_name="workbench_version_limit",
            file_service=file_service_mock,
            template_query_service=template_service_mock,
        )
    assertpy.assert_that(str(e.value)).is_equal_to(
        "Product version can only be restored if the statuses of all distributed versions are 'Retired'."
    )


@freeze_time("2023-08-17")
def test_restore_version_command_handler_raises_exception_when_restoring_rc_or_restored_versions(
    command_mock,
    mock_unit_of_work,
    versions_query_service_mock,
    portfolios_query_service_mock,
    message_bus_mock,
    get_test_version,
    parameter_service_mock,
    file_service_mock,
    template_service_mock,
    mock_products_repo,
    get_product,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    temp_file = tempfile.NamedTemporaryFile(delete=False)

    temp_file.write(b"Existing version template")
    temp_file.close()

    file_service_mock.get_template.return_value = temp_file.name
    versions_query_service_mock.get_product_version_distributions.return_value = [
        get_test_version(
            version_name="2.3.4-rc.1",
            version_type=version.VersionType.ReleaseCandidate.text,
        ),
        get_test_version(
            aws_account_id="123456789013",
            version_name="2.3.4-restored.1",
            version_type=version.VersionType.Restored.text,
        ),
    ]

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        restore_version_command_handler.handle(
            cmd=command_mock,
            uow=mock_unit_of_work,
            msg_bus=message_bus_mock,
            portfolios_qry_srv=portfolios_query_service_mock,
            versions_qry_srv=versions_query_service_mock,
            param_service=parameter_service_mock,
            product_version_limit_param_name="workbench_version_limit",
            file_service=file_service_mock,
            template_query_service=template_service_mock,
        )
    assertpy.assert_that(str(e.value)).is_equal_to("Only released versions can be restored.")


@freeze_time("2023-08-17")
def test_restore_version_command_handler_raises_exception_when_version_limit_reached(
    command_mock,
    mock_unit_of_work,
    versions_query_service_mock,
    portfolios_query_service_mock,
    message_bus_mock,
    parameter_service_mock,
    file_service_mock,
    template_service_mock,
    mock_products_repo,
    get_product,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()
    temp_file = tempfile.NamedTemporaryFile(delete=False)

    temp_file.write(b"Existing version template")
    temp_file.close()

    file_service_mock.get_template.return_value = temp_file.name
    versions_query_service_mock.get_distinct_number_of_versions.return_value = 11

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        restore_version_command_handler.handle(
            cmd=command_mock,
            uow=mock_unit_of_work,
            msg_bus=message_bus_mock,
            portfolios_qry_srv=portfolios_query_service_mock,
            versions_qry_srv=versions_query_service_mock,
            param_service=parameter_service_mock,
            product_version_limit_param_name="workbench_version_limit",
            file_service=file_service_mock,
            template_query_service=template_service_mock,
        )
    assertpy.assert_that(str(e.value)).is_equal_to(
        "You have reached the maximum number of active versions for this product."
    )
