from datetime import datetime, timezone
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import create_version_command_handler
from app.publishing.domain.commands import create_version_command
from app.publishing.domain.events import product_version_creation_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import portfolio, product, version
from app.publishing.domain.ports import (
    amis_query_service,
    iac_service,
    portfolios_query_service,
    template_service,
    versions_query_service,
)
from app.publishing.domain.query_services import template_domain_query_service
from app.publishing.domain.read_models import ami, component_version_detail
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    image_digest_value_object,
    image_tag_value_object,
    major_version_name_value_object,
    product_id_value_object,
    project_id_value_object,
    user_id_value_object,
    version_description_value_object,
    version_release_type_value_object,
    version_template_definition_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.api import parameter_service


@pytest.fixture()
def get_product():
    def _get_product(
        product_type: product.ProductType = product.ProductType.Workbench,
        status: product.ProductStatus = product.ProductStatus.Created,
    ):
        return product.Product(
            projectId="proj-12345",
            productId="prod-11111111",
            technologyId="tech-12345",
            technologyName="Test technology",
            status=status,
            productName="My Product",
            productType=product_type,
            productDescription="My Description",
            recommendedVersionId=None,
            createDate="2023-06-20T00:00:00+00:00",
            lastUpdateDate="2023-06-20T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        )

    return _get_product


@pytest.fixture()
def portfolio_query_service_mock():
    portfolio_srv_mock = mock.create_autospec(spec=portfolios_query_service.PortfoliosQueryService)
    current_time = datetime.now(timezone.utc).isoformat()
    portfolio_srv_mock.get_portfolios_by_tech_and_stage.return_value = [
        portfolio.Portfolio(
            portfolioId="port-12345abc",
            scPortfolioId="port-12345",
            projectId="proj-12345",
            technologyId="tech-12345",
            awsAccountId="123456789012",
            accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
            stage="DEV",
            region="us-east-1",
            status=portfolio.PortfolioStatus.Creating,
            createDate=current_time,
            lastUpdateDate=current_time,
        )
    ]
    return portfolio_srv_mock


@pytest.fixture()
def version_query_service_mock():
    return mock.create_autospec(spec=versions_query_service.VersionsQueryService)


@pytest.fixture()
def mock_command():
    def _mock_command(
        product_type: product.ProductType = product.ProductType.Workbench,
        release_type: str = version.VersionReleaseType.Major.value,
        major_version_name: major_version_name_value_object.MajorVersionNameValueObject = None,
    ) -> create_version_command.CreateVersionCommand:
        if product_type is product.ProductType.Container:
            return create_version_command.CreateVersionCommand(
                imageTag=image_tag_value_object.from_str("nginx"),
                imageDigest=image_digest_value_object.from_str("sha256:94afd1f2e64d908bc90dbca0035a5b567EXAMPLE"),
                majorVersionName=major_version_name,
                versionReleaseType=version_release_type_value_object.from_str(release_type),
                versionDescription=version_description_value_object.from_str("Workbench version description"),
                versionTemplateDefinition=version_template_definition_value_object.from_str("new version template"),
                projectId=project_id_value_object.from_str("proj-12345"),
                productId=product_id_value_object.from_str("prod-11111111"),
                createdBy=user_id_value_object.from_str("T0037SG"),
            )
        else:
            return create_version_command.CreateVersionCommand(
                amiId=ami_id_value_object.from_str("ami-023c04780e65e723c"),
                majorVersionName=major_version_name,
                versionReleaseType=version_release_type_value_object.from_str(release_type),
                versionDescription=version_description_value_object.from_str("Workbench version description"),
                versionTemplateDefinition=version_template_definition_value_object.from_str("new version template"),
                projectId=project_id_value_object.from_str("proj-12345"),
                productId=product_id_value_object.from_str("prod-11111111"),
                createdBy=user_id_value_object.from_str("T0037SG"),
            )

    return _mock_command


@pytest.fixture
def stack_service_mock():
    stack_srv_mock = mock.create_autospec(spec=iac_service.IACService)
    stack_srv_mock.validate_template.return_value = (
        True,
        [
            version.VersionParameter(
                parameterKey="param-1",
                defaultValue="12345",
                description="param description",
            ),
            version.VersionParameter(parameterKey="param-2"),
        ],
        None,
    )
    return stack_srv_mock


@pytest.fixture()
def get_test_ami():
    def _get_test_ami(
        ami_id: str = "ami-023c04780e65e723c",
    ) -> ami.Ami:
        return ami.Ami(
            projectId="proj-12345",
            amiId=ami_id,
            amiName="Test Ami",
            amiDescription="Test Ami Description",
            componentVersionDetails=[
                component_version_detail.ComponentVersionDetail(
                    componentName="VS Code",
                    componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
                    softwareVendor="Microsoft",
                    softwareVersion="1.87.0",
                )
            ],
            osVersion="Ubuntu 24",
            platform="Linux",
            integrations=["GitHub"],
            createDate="2024-03-06T00:00:00+00:00",
            lastUpdateDate="2024-03-06T00:00:00+00:00",
        )

    return _get_test_ami


@pytest.fixture
def amis_query_service_mock():
    amis_qry_srv_mock = mock.create_autospec(spec=amis_query_service.AMIsQueryService)
    return amis_qry_srv_mock


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


@pytest.fixture()
def message_bus_mock():
    return mock.create_autospec(spec=message_bus.MessageBus)


@pytest.mark.parametrize(
    "fetched_release_name,release_type,expected_version_name",
    (
        ("2.0.0-rc.1", version.VersionReleaseType.Major.value, "3.0.0-rc.1"),
        ("1.2.1-rc.1", version.VersionReleaseType.Minor.value, "1.3.0-rc.1"),
        ("2.5.10-rc.1", version.VersionReleaseType.Patch.value, "2.5.11-rc.1"),
        (None, version.VersionReleaseType.Major.value, "1.0.0-rc.1"),
        (None, version.VersionReleaseType.Minor.value, "1.0.0-rc.1"),
        (None, version.VersionReleaseType.Patch.value, "1.0.0-rc.1"),
    ),
)
@mock.patch("app.publishing.domain.model.version.random.choice", lambda chars: "1")
@freeze_time("2023-06-20")
def test_handle_should_create_new_version_if_version_in_repository(
    fetched_release_name,
    release_type,
    expected_version_name,
    portfolio_query_service_mock,
    version_query_service_mock,
    stack_service_mock,
    amis_query_service_mock,
    get_test_ami,
    file_service_mock,
    template_service_mock,
    get_product,
    message_bus_mock,
    mock_unit_of_work,
    mock_command,
    mock_version_repo,
    mock_products_repo,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    param_service_mock = mock.create_autospec(spec=parameter_service.ParameterService)
    param_service_mock.get_parameter_value.return_value = 10
    workbench_version_limit_param_name = "workbench_version_limit"
    workbench_rc_version_limit_param_name = "workbench_rc_version_limit_param_name"

    version_query_service_mock.get_latest_version_name_and_id.return_value = (
        fetched_release_name,
        "vers-1234",
    )
    version_query_service_mock.get_distinct_number_of_versions.return_value = 1

    create_product_version_command_mock = mock_command(release_type=release_type)

    test_ami = get_test_ami()
    amis_query_service_mock.get_ami.return_value = test_ami

    # ACT
    create_version_command_handler.handle(
        command=create_product_version_command_mock,
        uow=mock_unit_of_work,
        message_bus=message_bus_mock,
        portf_qry_srv=portfolio_query_service_mock,
        version_qry_srv=version_query_service_mock,
        param_service=param_service_mock,
        product_version_limit_param_name=workbench_version_limit_param_name,
        product_rc_version_limit_param_name=workbench_rc_version_limit_param_name,
        stack_srv=stack_service_mock,
        amis_qry_srv=amis_query_service_mock,
        file_service=file_service_mock,
        template_query_service=template_service_mock,
    )

    # ASSERT
    version_query_service_mock.get_latest_version_name_and_id.assert_called_once_with(
        product_id="prod-11111111", version_name_begins_with=None
    )
    mock_version_repo.add.assert_called_once_with(
        version.Version(
            versionId="vers-11111111",
            projectId="proj-12345",
            productId="prod-11111111",
            scPortfolioId="port-12345",
            versionDescription="Workbench version description",
            versionName=expected_version_name,
            versionType=version.VersionType.ReleaseCandidate.text,
            technologyId="tech-12345",
            awsAccountId="123456789012",
            accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
            stage="DEV",
            region="us-east-1",
            originalAmiId="ami-023c04780e65e723c",
            status=version.VersionStatus.Creating,
            isRecommendedVersion=False,
            parameters=[
                version.VersionParameter(
                    parameterKey="param-1",
                    defaultValue="12345",
                    description="param description",
                ),
                version.VersionParameter(parameterKey="param-2"),
            ],
            componentVersionDetails=test_ami.componentVersionDetails,
            osVersion=test_ami.osVersion,
            platform=test_ami.platform,
            draftTemplateLocation="prod-11111111/vers-11111111/draft_workbench.yml",
            createDate="2023-06-20T00:00:00+00:00",
            lastUpdateDate="2023-06-20T00:00:00+00:00",
            createdBy="T0037SG",
            lastUpdatedBy="T0037SG",
            integrations=["GitHub"],
        )
    )
    mock_unit_of_work.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        product_version_creation_started.ProductVersionCreationStarted(
            product_id="prod-11111111",
            version_id="vers-11111111",
            aws_account_id="123456789012",
            product_type="WORKBENCH",
        )
    )


@pytest.mark.parametrize(
    "fetched_release_name,release_type,expected_version_name",
    (
        ("2.0.0-rc.1", version.VersionReleaseType.Major.value, "3.0.0-rc.1"),
        ("1.2.1-rc.1", version.VersionReleaseType.Minor.value, "1.3.0-rc.1"),
        ("2.5.10-rc.1", version.VersionReleaseType.Patch.value, "2.5.11-rc.1"),
        (None, version.VersionReleaseType.Major.value, "1.0.0-rc.1"),
        (None, version.VersionReleaseType.Minor.value, "1.0.0-rc.1"),
        (None, version.VersionReleaseType.Patch.value, "1.0.0-rc.1"),
    ),
)
@mock.patch("app.publishing.domain.model.version.random.choice", lambda chars: "1")
@freeze_time("2023-06-20")
def test_handle_should_create_new_version_if_version_in_repository_for_container_product(
    fetched_release_name,
    release_type,
    expected_version_name,
    portfolio_query_service_mock,
    version_query_service_mock,
    stack_service_mock,
    amis_query_service_mock,
    get_test_ami,
    file_service_mock,
    template_service_mock,
    get_product,
    message_bus_mock,
    mock_command,
    mock_products_repo,
    mock_version_repo,
    mock_unit_of_work,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product(product_type=product.ProductType.Container)

    param_service_mock = mock.create_autospec(spec=parameter_service.ParameterService)
    param_service_mock.get_parameter_value.return_value = 10
    workbench_version_limit_param_name = "workbench_version_limit"
    workbench_rc_version_limit_param_name = "workbench_rc_version_limit_param_name"

    version_query_service_mock.get_latest_version_name_and_id.return_value = (
        fetched_release_name,
        "vers-1234",
    )
    version_query_service_mock.get_distinct_number_of_versions.return_value = 1

    create_product_version_command_mock = mock_command(
        product_type=product.ProductType.Container, release_type=release_type
    )

    test_ami = get_test_ami()
    amis_query_service_mock.get_ami.return_value = test_ami

    # ACT
    create_version_command_handler.handle(
        command=create_product_version_command_mock,
        uow=mock_unit_of_work,
        message_bus=message_bus_mock,
        portf_qry_srv=portfolio_query_service_mock,
        version_qry_srv=version_query_service_mock,
        param_service=param_service_mock,
        product_version_limit_param_name=workbench_version_limit_param_name,
        product_rc_version_limit_param_name=workbench_rc_version_limit_param_name,
        stack_srv=stack_service_mock,
        amis_qry_srv=amis_query_service_mock,
        file_service=file_service_mock,
        template_query_service=template_service_mock,
    )

    # ASSERT
    version_query_service_mock.get_latest_version_name_and_id.assert_called_once_with(
        product_id="prod-11111111", version_name_begins_with=None
    )
    mock_version_repo.add.assert_called_once_with(
        version.Version(
            versionId="vers-11111111",
            projectId="proj-12345",
            productId="prod-11111111",
            scPortfolioId="port-12345",
            versionDescription="Workbench version description",
            versionName=expected_version_name,
            versionType=version.VersionType.ReleaseCandidate.text,
            technologyId="tech-12345",
            awsAccountId="123456789012",
            accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
            stage="DEV",
            region="us-east-1",
            imageTag="nginx",
            imageDigest="sha256:94afd1f2e64d908bc90dbca0035a5b567EXAMPLE",
            status=version.VersionStatus.Creating,
            isRecommendedVersion=False,
            parameters=[
                version.VersionParameter(
                    parameterKey="param-1",
                    defaultValue="12345",
                    description="param description",
                ),
                version.VersionParameter(parameterKey="param-2"),
            ],
            draftTemplateLocation="prod-11111111/vers-11111111/draft_workbench.yml",
            createDate="2023-06-20T00:00:00+00:00",
            lastUpdateDate="2023-06-20T00:00:00+00:00",
            createdBy="T0037SG",
            lastUpdatedBy="T0037SG",
        )
    )
    mock_unit_of_work.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        product_version_creation_started.ProductVersionCreationStarted(
            product_id="prod-11111111",
            version_id="vers-11111111",
            aws_account_id="123456789012",
            product_type="CONTAINER",
        )
    )


def test_handle_should_raise_exception_when_version_description_exceeds_100_characters():
    # ARRANGE & ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        create_version_command.CreateVersionCommand(
            amiId=ami_id_value_object.from_str("ami-023c04780e65e723c"),
            versionReleaseType=version_release_type_value_object.from_str(version.VersionReleaseType.Major.value),
            versionDescription=version_description_value_object.from_str(
                "A very long version description that will exceed the specified limit set in the command handler and thus should cause an exception to be thrown"
            ),
            versionTemplateDefinition=version_template_definition_value_object.from_str("new version template"),
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-11111111"),
            createdBy=user_id_value_object.from_str("T0037SG"),
        )

    assertpy.assert_that(str(e.value)).is_equal_to(
        "Version description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)"
    )


def test_handle_should_raise_exception_when_major_name_version_is_specified_and_release_type_is_major(
    portfolio_query_service_mock,
    version_query_service_mock,
    stack_service_mock,
    amis_query_service_mock,
    file_service_mock,
    template_service_mock,
    message_bus_mock,
    get_product,
    mock_command,
    mock_unit_of_work,
    mock_products_repo,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    param_service_mock = mock.create_autospec(spec=parameter_service.ParameterService)
    param_service_mock.get_parameter_value.return_value = 10
    workbench_version_limit_param_name = "workbench_version_limit"
    workbench_rc_version_limit_param_name = "workbench_rc_version_limit_param_name"

    version_query_service_mock.get_latest_version_name_and_id.return_value = (
        "2.0.0-rc.1",
        "vers-1234",
    )
    version_query_service_mock.get_distinct_number_of_versions.return_value = 1

    create_product_version_command_mock = mock_command(
        release_type=version.VersionReleaseType.Major.value,
        major_version_name=major_version_name_value_object.from_int(1),
    )

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        create_version_command_handler.handle(
            command=create_product_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            portf_qry_srv=portfolio_query_service_mock,
            version_qry_srv=version_query_service_mock,
            param_service=param_service_mock,
            product_version_limit_param_name=workbench_version_limit_param_name,
            product_rc_version_limit_param_name=workbench_rc_version_limit_param_name,
            stack_srv=stack_service_mock,
            amis_qry_srv=amis_query_service_mock,
            file_service=file_service_mock,
            template_query_service=template_service_mock,
        )

    assertpy.assert_that(str(e.value)).is_equal_to(
        "You cannot create a new major version when selecting an existing major version."
    )


# A test to verify that you can only create a version if there are less than 5 versions available
def test_handle_should_raise_exception_when_version_limit_reached(
    portfolio_query_service_mock,
    version_query_service_mock,
    stack_service_mock,
    amis_query_service_mock,
    file_service_mock,
    template_service_mock,
    mock_unit_of_work,
    message_bus_mock,
    get_product,
    mock_command,
    mock_products_repo,
):
    # ARRANGE
    def count_version(
        product_id: str,
        status: version.VersionStatus | None = None,
        version_name_filter: str = None,
    ) -> int:
        if version_name_filter:
            return 2
        return 5

    def limit_param_fake(parameter_name: str) -> str:
        if parameter_name == "workbench_version_limit_param_name":
            return "5"
        if parameter_name == "workbench_rc_version_limit_param_name":
            return "2"
        return "0"

    mock_products_repo.get.return_value = get_product()

    param_service_mock = mock.create_autospec(spec=parameter_service.ParameterService)
    param_service_mock.get_parameter_value.side_effect = limit_param_fake
    workbench_version_limit_param_name = "workbench_version_limit"
    workbench_rc_version_limit_param_name = "workbench_rc_version_limit_param_name"
    version_query_service_mock.get_distinct_number_of_versions.side_effect = count_version
    create_product_version_command_mock = mock_command()
    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        create_version_command_handler.handle(
            command=create_product_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            portf_qry_srv=portfolio_query_service_mock,
            version_qry_srv=version_query_service_mock,
            param_service=param_service_mock,
            product_version_limit_param_name=workbench_version_limit_param_name,
            product_rc_version_limit_param_name=workbench_rc_version_limit_param_name,
            stack_srv=stack_service_mock,
            amis_qry_srv=amis_query_service_mock,
            file_service=file_service_mock,
            template_query_service=template_service_mock,
        )

    assertpy.assert_that(str(e.value)).is_equal_to(
        "You have reached the maximum number of active versions for this product."
    )


def test_handle_should_raise_exception_when_rc_version_limit_reached(
    portfolio_query_service_mock,
    version_query_service_mock,
    stack_service_mock,
    amis_query_service_mock,
    file_service_mock,
    template_service_mock,
    mock_unit_of_work,
    generic_repo_mock,
    get_product,
    message_bus_mock,
    mock_command,
    mock_products_repo,
):
    # ARRANGE
    def count_version(
        product_id: str,
        status: version.VersionStatus | None = None,
        version_name_filter: str = None,
    ) -> int:
        if version_name_filter:
            return 2
        return 4

    def limit_param_fake(parameter_name: str) -> str:
        if parameter_name == "workbench_version_limit_param_name":
            return "5"
        if parameter_name == "workbench_rc_version_limit_param_name":
            return "2"
        return "0"

    mock_products_repo.get.return_value = get_product()

    param_service_mock = mock.create_autospec(spec=parameter_service.ParameterService)
    param_service_mock.get_parameter_value.side_effect = limit_param_fake
    workbench_version_limit_param_name = "workbench_version_limit_param_name"
    workbench_rc_version_limit_param_name = "workbench_rc_version_limit_param_name"

    version_query_service_mock.get_distinct_number_of_versions.side_effect = count_version
    create_product_version_command_mock = mock_command()

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        create_version_command_handler.handle(
            command=create_product_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            portf_qry_srv=portfolio_query_service_mock,
            version_qry_srv=version_query_service_mock,
            param_service=param_service_mock,
            product_version_limit_param_name=workbench_version_limit_param_name,
            product_rc_version_limit_param_name=workbench_rc_version_limit_param_name,
            stack_srv=stack_service_mock,
            amis_qry_srv=amis_query_service_mock,
            file_service=file_service_mock,
            template_query_service=template_service_mock,
        )

    assertpy.assert_that(str(e.value)).is_equal_to(
        "You have reached the maximum number of active RC versions for this product."
    )
