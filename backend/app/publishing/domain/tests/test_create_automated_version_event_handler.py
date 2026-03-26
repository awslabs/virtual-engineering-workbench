from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time

from app.publishing.domain.event_handlers import create_automated_version_event_handler
from app.publishing.domain.events import product_version_creation_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import portfolio, product, version
from app.publishing.domain.read_models import component_version_detail


# Helper to create default component details for tests
def get_default_component_details():
    return [
        component_version_detail.ComponentVersionDetail(
            componentName="VS Code",
            componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
            softwareVendor="Microsoft",
            softwareVersion="1.87.0",
        )
    ]


# Helper to call handler with common parameters
def call_handler(
    ami_id,
    product_id,
    project_id,
    release_type,
    mock_template_domain_qry_srv,
    mock_logger,
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    component_details=None,
    os_version="Ubuntu 24.04",
    platform="Linux",
    architecture="x86_64",
    integrations=None,
):
    if component_details is None:
        component_details = get_default_component_details()
    if integrations is None:
        integrations = ["GitHub"]

    create_automated_version_event_handler.handle(
        ami_id=ami_id,
        product_id=product_id,
        project_id=project_id,
        release_type=release_type,
        user_id="T123456",
        component_version_details=component_details,
        os_version=os_version,
        platform=platform,
        architecture=architecture,
        integrations=integrations,
        template_domain_qry_srv=mock_template_domain_qry_srv,
        logger=mock_logger,
        uow=mock_unit_of_work,
        message_bus=mock_message_bus,
        portf_qry_srv=mock_portfolios_qry_srv,
        version_qry_srv=mock_versions_qry_srv,
        param_service=mock_param_service,
        product_version_limit_param_name="version-limit",
        product_rc_version_limit_param_name="rc-limit",
        stack_srv=mock_stack_srv,
        file_service=mock_file_service,
    )


@patch(
    "app.publishing.domain.model.version.generate_version_id",
    return_value="vers-11111111",
)
@freeze_time("2023-06-20")
def test_handle_creates_automated_version_successfully_for_workbench_product(
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_template_domain_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    mock_product_entity,
    mock_logger,
):
    # ARRANGE
    ami_id = "ami-12345678"
    product_id = "product-456"
    project_id = "project-123"

    mock_product_repo = Mock()
    mock_product_repo.get.return_value = mock_product_entity

    mock_repo = Mock()

    def get_repository_side_effect(pk_param, entity_param):
        if entity_param == product.Product:
            return mock_product_repo
        return mock_repo

    mock_unit_of_work.get_repository.side_effect = get_repository_side_effect

    # ACT
    call_handler(
        ami_id,
        product_id,
        project_id,
        "MINOR",
        mock_template_domain_qry_srv,
        mock_logger,
        mock_unit_of_work,
        mock_message_bus,
        mock_portfolios_qry_srv,
        mock_versions_qry_srv,
        mock_param_service,
        mock_stack_srv,
        mock_file_service,
    )

    # ASSERT
    mock_versions_qry_srv.get_latest_version_name_and_id.assert_called_once_with(
        product_id=product_id, version_name_begins_with=None
    )
    mock_portfolios_qry_srv.get_portfolios_by_tech_and_stage.assert_called_once_with(
        "tech-789", portfolio.PortfolioStage.DEV.value
    )
    mock_param_service.get_parameter_value.assert_called()
    mock_template_domain_qry_srv.get_latest_draft_template.assert_called_once()
    mock_stack_srv.validate_template.assert_called_once()
    mock_file_service.put_template.assert_called_once()
    mock_repo.add.assert_called_once()
    mock_message_bus.publish.assert_called_once()

    added_version = mock_repo.add.call_args[0][0]
    assert added_version.versionId == "vers-11111111"
    assert added_version.versionName == "1.1.0-rc.1"
    assert added_version.originalAmiId == ami_id
    assert added_version.status == version.VersionStatus.Creating
    assert added_version.createdBy == "T123456"

    published_event = mock_message_bus.publish.call_args[0][0]
    assert isinstance(published_event, product_version_creation_started.ProductVersionCreationStarted)
    assert published_event.product_id == product_id
    assert published_event.version_id == "vers-11111111"


@patch(
    "app.publishing.domain.model.version.generate_version_id",
    return_value="vers-11111111",
)
@freeze_time("2023-06-20")
def test_handle_creates_automated_version_successfully_for_container_product(
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_template_domain_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    mock_container_product_entity,
    mock_logger,
):
    # ARRANGE
    ami_id = "ami-12345678"
    product_id = "product-456"
    project_id = "project-123"

    mock_repo = Mock()
    mock_repo.get.return_value = mock_container_product_entity
    mock_unit_of_work.get_repository.return_value = mock_repo

    mock_versions_qry_srv.get_latest_version_name_and_id.return_value = (
        "1.0.0",
        "vers-12345",
    )

    # ACT
    call_handler(
        ami_id,
        product_id,
        project_id,
        "MAJOR",
        mock_template_domain_qry_srv,
        mock_logger,
        mock_unit_of_work,
        mock_message_bus,
        mock_portfolios_qry_srv,
        mock_versions_qry_srv,
        mock_param_service,
        mock_stack_srv,
        mock_file_service,
    )

    # ASSERT
    added_version = mock_repo.add.call_args[0][0]
    assert added_version.versionId == "vers-11111111"
    assert added_version.versionName == "2.0.0-rc.1"
    assert added_version.imageTag == "automated-ami-12345678"
    assert added_version.imageDigest == "sha256:ami-12345678"
    assert added_version.originalAmiId is None
    assert added_version.componentVersionDetails is None


def test_handle_raises_exception_when_no_released_version_found(
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_template_domain_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    mock_product_entity,
    mock_logger,
):
    # ARRANGE
    ami_id = "ami-12345678"
    product_id = "product-456"
    project_id = "project-123"

    mock_product_repo = Mock()
    mock_product_repo.get.return_value = mock_product_entity

    def get_repository_side_effect(pk_param, entity_param):
        if entity_param == product.Product:
            return mock_product_repo
        return Mock()

    mock_unit_of_work.get_repository.side_effect = get_repository_side_effect

    mock_versions_qry_srv.get_latest_version_name_and_id.return_value = (None, None)

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException, match="No released version found"):
        call_handler(
            ami_id,
            product_id,
            project_id,
            "PATCH",
            mock_template_domain_qry_srv,
            mock_logger,
            mock_unit_of_work,
            mock_message_bus,
            mock_portfolios_qry_srv,
            mock_versions_qry_srv,
            mock_param_service,
            mock_stack_srv,
            mock_file_service,
        )


def test_handle_raises_exception_when_product_not_created(
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_template_domain_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    mock_logger,
):
    # ARRANGE
    ami_id = "ami-12345678"
    product_id = "product-456"
    project_id = "project-123"

    non_created_product = product.Product(
        projectId="project-123",
        productId="product-456",
        productName="Test Container Product",
        productType=product.ProductType.Container,
        status=product.ProductStatus.Creating,
        technologyId="tech-789",
        technologyName="Test Technology",
        createDate="2025-07-30T13:35:02.425779+00:00",
        lastUpdateDate="2025-07-30T13:35:02.425785+00:00",
        createdBy="user-123",
        lastUpdatedBy="user-123",
    )

    mock_product_repo = Mock()
    mock_product_repo.get.return_value = non_created_product

    def get_repository_side_effect(pk_param, entity_param):
        if entity_param == product.Product:
            return mock_product_repo
        return Mock()

    mock_unit_of_work.get_repository.side_effect = get_repository_side_effect

    # ACT & ASSERT
    with pytest.raises(
        domain_exception.DomainException,
        match="New product version can be created only from product with status 'Created'",
    ):
        call_handler(
            ami_id,
            product_id,
            project_id,
            "MINOR",
            mock_template_domain_qry_srv,
            mock_logger,
            mock_unit_of_work,
            mock_message_bus,
            mock_portfolios_qry_srv,
            mock_versions_qry_srv,
            mock_param_service,
            mock_stack_srv,
            mock_file_service,
        )


def test_handle_raises_exception_when_no_dev_portfolios(
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_template_domain_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    mock_product_entity,
    mock_logger,
):
    # ARRANGE
    ami_id = "ami-12345678"
    product_id = "product-456"
    project_id = "project-123"

    mock_product_repo = Mock()
    mock_product_repo.get.return_value = mock_product_entity

    def get_repository_side_effect(pk_param, entity_param):
        if entity_param == product.Product:
            return mock_product_repo
        return Mock()

    mock_unit_of_work.get_repository.side_effect = get_repository_side_effect

    mock_portfolios_qry_srv.get_portfolios_by_tech_and_stage.return_value = []

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException, match="No portfolio found for DEV stage"):
        call_handler(
            ami_id,
            product_id,
            project_id,
            "PATCH",
            mock_template_domain_qry_srv,
            mock_logger,
            mock_unit_of_work,
            mock_message_bus,
            mock_portfolios_qry_srv,
            mock_versions_qry_srv,
            mock_param_service,
            mock_stack_srv,
            mock_file_service,
        )


def test_handle_raises_exception_when_version_limit_exceeded(
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_template_domain_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    mock_product_entity,
    mock_logger,
):
    # ARRANGE
    ami_id = "ami-12345678"
    product_id = "product-456"
    project_id = "project-123"

    mock_product_repo = Mock()
    mock_product_repo.get.return_value = mock_product_entity

    def get_repository_side_effect(pk_param, entity_param):
        if entity_param == product.Product:
            return mock_product_repo
        return Mock()

    mock_unit_of_work.get_repository.side_effect = get_repository_side_effect

    def count_version(product_id: str, status=None, version_name_filter=None):
        if version_name_filter:
            return 1
        return 10

    mock_versions_qry_srv.get_distinct_number_of_versions.side_effect = count_version

    def mock_get_parameter_value(parameter_name):
        if "version_limit" in parameter_name or "version-limit" in parameter_name:
            return "5"
        else:
            return "2"

    mock_param_service.get_parameter_value.side_effect = mock_get_parameter_value

    # ACT & ASSERT
    with pytest.raises(
        domain_exception.DomainException,
        match="You have reached the maximum number of active versions for this product",
    ):
        call_handler(
            ami_id,
            product_id,
            project_id,
            "MAJOR",
            mock_template_domain_qry_srv,
            mock_logger,
            mock_unit_of_work,
            mock_message_bus,
            mock_portfolios_qry_srv,
            mock_versions_qry_srv,
            mock_param_service,
            mock_stack_srv,
            mock_file_service,
        )


def test_handle_raises_exception_when_rc_version_limit_exceeded(
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_template_domain_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    mock_product_entity,
    mock_logger,
):
    # ARRANGE
    ami_id = "ami-12345678"
    product_id = "product-456"
    project_id = "project-123"

    mock_product_repo = Mock()
    mock_product_repo.get.return_value = mock_product_entity

    def get_repository_side_effect(pk_param, entity_param):
        if entity_param == product.Product:
            return mock_product_repo
        return Mock()

    mock_unit_of_work.get_repository.side_effect = get_repository_side_effect

    def count_version(product_id: str, status=None, version_name_filter=None):
        if version_name_filter:
            return 5
        return 3

    mock_versions_qry_srv.get_distinct_number_of_versions.side_effect = count_version

    def mock_get_parameter_value(parameter_name):
        if "version-limit" in parameter_name:
            return "10"
        elif "rc-limit" in parameter_name:
            return "2"
        else:
            return "10"

    mock_param_service.get_parameter_value.side_effect = mock_get_parameter_value

    # ACT & ASSERT
    with pytest.raises(
        domain_exception.DomainException,
        match="You have reached the maximum number of active RC versions for this product",
    ):
        call_handler(
            ami_id,
            product_id,
            project_id,
            "MINOR",
            mock_template_domain_qry_srv,
            mock_logger,
            mock_unit_of_work,
            mock_message_bus,
            mock_portfolios_qry_srv,
            mock_versions_qry_srv,
            mock_param_service,
            mock_stack_srv,
            mock_file_service,
        )


def test_handle_raises_exception_when_template_invalid(
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_template_domain_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    mock_product_entity,
    mock_logger,
):
    # ARRANGE
    ami_id = "ami-12345678"
    product_id = "product-456"
    project_id = "project-123"

    mock_product_repo = Mock()
    mock_product_repo.get.return_value = mock_product_entity

    def get_repository_side_effect(pk_param, entity_param):
        if entity_param == product.Product:
            return mock_product_repo
        return Mock()

    mock_unit_of_work.get_repository.side_effect = get_repository_side_effect

    mock_template_domain_qry_srv.get_latest_draft_template.return_value = "invalid template content"
    mock_stack_srv.validate_template.return_value = (
        False,
        None,
        "Template validation error",
    )

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException, match="The template is invalid"):
        call_handler(
            ami_id,
            product_id,
            project_id,
            "MAJOR",
            mock_template_domain_qry_srv,
            mock_logger,
            mock_unit_of_work,
            mock_message_bus,
            mock_portfolios_qry_srv,
            mock_versions_qry_srv,
            mock_param_service,
            mock_stack_srv,
            mock_file_service,
        )


@pytest.mark.parametrize(
    "latest_version_name,expected_new_version",
    [
        ("1.0.0", "1.0.1-rc.1"),
        ("2.5.10", "2.5.11-rc.1"),
        ("1.2.3-rc.1", "1.2.4-rc.1"),
        ("3.0.0-rc.5", "3.0.1-rc.1"),
    ],
)
@patch(
    "app.publishing.domain.model.version.generate_version_id",
    return_value="vers-11111111",
)
@freeze_time("2023-06-20")
def test_handle_calculates_correct_patch_version_name(
    mock_unit_of_work,
    mock_message_bus,
    mock_portfolios_qry_srv,
    mock_versions_qry_srv,
    mock_template_domain_qry_srv,
    mock_param_service,
    mock_stack_srv,
    mock_file_service,
    mock_product_entity,
    mock_logger,
    latest_version_name,
    expected_new_version,
):
    # ARRANGE
    ami_id = "ami-12345678"
    product_id = "product-456"
    project_id = "project-123"

    mock_repo = Mock()
    mock_repo.get.return_value = mock_product_entity
    mock_unit_of_work.get_repository.return_value = mock_repo

    mock_versions_qry_srv.get_latest_version_name_and_id.return_value = (
        latest_version_name,
        "vers-12345",
    )

    # ACT
    call_handler(
        ami_id,
        product_id,
        project_id,
        "PATCH",
        mock_template_domain_qry_srv,
        mock_logger,
        mock_unit_of_work,
        mock_message_bus,
        mock_portfolios_qry_srv,
        mock_versions_qry_srv,
        mock_param_service,
        mock_stack_srv,
        mock_file_service,
    )

    # ASSERT
    added_version = mock_repo.add.call_args[0][0]
    assert added_version.versionName == expected_new_version
