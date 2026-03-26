from datetime import datetime, timezone
from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import update_version_command_handler
from app.publishing.domain.commands import update_version_command
from app.publishing.domain.events import product_version_update_started
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.model import product, version
from app.publishing.domain.ports import (
    amis_query_service,
    iac_service,
    template_service,
    versions_query_service,
)
from app.publishing.domain.query_services import template_domain_query_service
from app.publishing.domain.read_models import ami, component_version_detail
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    image_digest_value_object,
    image_tag_value_object,
    product_id_value_object,
    project_id_value_object,
    user_id_value_object,
    version_description_value_object,
    version_id_value_object,
    version_template_definition_value_object,
)
from app.shared.adapters.message_bus import message_bus


@pytest.fixture()
def get_test_versions(previous_release_name, version_type):
    def _get_test_versions(version_id: str = "version-123"):
        return [
            version.Version(
                projectId="proj-12345",
                productId="prod-11111111",
                versionId=version_id,
                scPortfolioId="port-12345",
                versionDescription="Product version description",
                versionName=previous_release_name,
                versionType=version_type,
                draftTemplateLocation="prod-11111111/vers-11111111/draft_workbench.yml",
                technologyId="tech-12345",
                awsAccountId=f"{i}",
                stage="DEV",
                region="us-east-1",
                originalAmiId="ami-023c04780e65e723c",
                status=version.VersionStatus.Created,
                isRecommendedVersion=True,
                createDate="2023-06-20T00:00:00+00:00",
                lastUpdateDate="2023-06-20T00:00:00+00:00",
                createdBy="T0037SG",
                lastUpdatedBy="T0037SG",
            )
            for i in range(1, 4)
        ]

    return _get_test_versions


@pytest.fixture()
def version_query_service_mock(get_test_versions):
    version_qry_srv = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    version_qry_srv.get_product_version_distributions.return_value = get_test_versions()
    return version_qry_srv


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
def mock_command():
    def _mock_command(
        product_type: product.ProductType = product.ProductType.Workbench,
    ) -> update_version_command.UpdateVersionCommand:
        if product_type is product.ProductType.Container:
            return update_version_command.UpdateVersionCommand(
                imageTag=image_tag_value_object.from_str("nginx"),
                imageDigest=image_digest_value_object.from_str("sha256:94afd1f2e64d908bc90dbca0035a5b567EXAMPLE"),
                versionId=version_id_value_object.from_str("version-123"),
                versionDescription=version_description_value_object.from_str("Workbench version description"),
                versionTemplateDefinition=version_template_definition_value_object.from_str(
                    "Updated template definition"
                ),
                projectId=project_id_value_object.from_str("proj-12345"),
                productId=product_id_value_object.from_str("prod-11111111"),
                lastUpdatedBy=user_id_value_object.from_str("user-12345"),
            )
        else:
            return update_version_command.UpdateVersionCommand(
                amiId=ami_id_value_object.from_str("ami-023c04780e65e723c"),
                versionId=version_id_value_object.from_str("version-123"),
                versionDescription=version_description_value_object.from_str("Workbench version description"),
                versionTemplateDefinition=version_template_definition_value_object.from_str(
                    "Updated template definition"
                ),
                projectId=project_id_value_object.from_str("proj-12345"),
                productId=product_id_value_object.from_str("prod-11111111"),
                lastUpdatedBy=user_id_value_object.from_str("user-12345"),
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
    def _get_test_ami(ami_id: str = "ami-023c04780e65e723c", has_components_details: bool = True) -> ami.Ami:
        return ami.Ami(
            projectId="proj-12345",
            amiId=ami_id,
            amiName="Test Ami",
            amiDescription="Test Ami Description",
            componentVersionDetails=(
                [
                    component_version_detail.ComponentVersionDetail(
                        componentName="VS Code",
                        componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
                        softwareVendor="Microsoft",
                        softwareVersion="1.87.0",
                    )
                ]
                if has_components_details
                else None
            ),
            osVersion="Ubuntu 24",
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
    "previous_release_name,new_version_name,version_type",
    (
        ("1.2.3-rc.1", "1.2.3-rc.2", version.VersionType.ReleaseCandidate.text),
        ("1.3.7-rc.56", "1.3.7-rc.57", version.VersionType.ReleaseCandidate.text),
    ),
)
@mock.patch("app.publishing.domain.model.version.random.choice", lambda chars: "1")
@freeze_time("2023-06-20")
def test_handle_should_update_version_if_version_in_repository(
    previous_release_name,
    new_version_name,
    version_type,
    version_query_service_mock,
    stack_service_mock,
    amis_query_service_mock,
    get_test_ami,
    file_service_mock,
    template_service_mock,
    message_bus_mock,
    mock_unit_of_work,
    get_product,
    mock_command,
    mock_version_repo,
    mock_products_repo,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    test_ami = get_test_ami()
    amis_query_service_mock.get_ami.return_value = test_ami
    update_product_version_command_mock = mock_command()

    # ACT
    update_version_command_handler.handle(
        command=update_product_version_command_mock,
        uow=mock_unit_of_work,
        message_bus=message_bus_mock,
        version_qry_srv=version_query_service_mock,
        stack_srv=stack_service_mock,
        amis_qry_srv=amis_query_service_mock,
        file_service=file_service_mock,
        template_query_service=template_service_mock,
    )

    # ASSERT
    version_query_service_mock.get_product_version_distributions.assert_any_call(
        product_id="prod-11111111", version_id="version-123"
    )
    current_time = datetime.now(timezone.utc).isoformat()
    mock_version_repo.update_attributes.assert_called_with(
        pk=version.VersionPrimaryKey(
            productId="prod-11111111",
            versionId="version-123",
            awsAccountId="3",
        ),
        copiedAmiId=None,
        originalAmiId="ami-023c04780e65e723c",
        lastUpdateDate=current_time,
        lastUpdatedBy="user-12345",
        versionName=new_version_name,
        versionDescription="Workbench version description",
        status=version.VersionStatus.Updating,
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
        draftTemplateLocation="prod-11111111/version-123/draft_workbench.yml",
    )
    mock_unit_of_work.commit.assert_called()
    message_bus_mock.publish.assert_called_with(
        product_version_update_started.ProductVersionUpdateStarted(
            product_id="prod-11111111",
            version_id="version-123",
            aws_account_id="3",
            product_type="WORKBENCH",
        )
    )


@pytest.mark.parametrize(
    "previous_release_name,new_version_name,version_type",
    (
        ("1.2.3-rc.1", "1.2.3-rc.2", version.VersionType.ReleaseCandidate.text),
        ("1.3.7-rc.56", "1.3.7-rc.57", version.VersionType.ReleaseCandidate.text),
    ),
)
@mock.patch("app.publishing.domain.model.version.random.choice", lambda chars: "1")
@freeze_time("2023-06-20")
def test_handle_should_update_version_if_version_in_repository_for_container_product(
    previous_release_name,
    new_version_name,
    version_type,
    version_query_service_mock,
    stack_service_mock,
    amis_query_service_mock,
    file_service_mock,
    template_service_mock,
    message_bus_mock,
    mock_unit_of_work,
    get_product,
    mock_command,
    mock_products_repo,
    mock_version_repo,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product(product_type=product.ProductType.Container)

    update_product_version_command_mock = mock_command(product_type=product.ProductType.Container)

    # ACT
    update_version_command_handler.handle(
        command=update_product_version_command_mock,
        uow=mock_unit_of_work,
        message_bus=message_bus_mock,
        version_qry_srv=version_query_service_mock,
        stack_srv=stack_service_mock,
        amis_qry_srv=amis_query_service_mock,
        file_service=file_service_mock,
        template_query_service=template_service_mock,
    )

    # ASSERT
    version_query_service_mock.get_product_version_distributions.assert_any_call(
        product_id="prod-11111111", version_id="version-123"
    )
    current_time = datetime.now(timezone.utc).isoformat()
    mock_version_repo.update_attributes.assert_called_with(
        pk=version.VersionPrimaryKey(
            productId="prod-11111111",
            versionId="version-123",
            awsAccountId="3",
        ),
        copiedAmiId=None,
        imageTag="nginx",
        imageDigest="sha256:94afd1f2e64d908bc90dbca0035a5b567EXAMPLE",
        lastUpdateDate=current_time,
        lastUpdatedBy="user-12345",
        versionName=new_version_name,
        versionDescription="Workbench version description",
        status=version.VersionStatus.Updating,
        parameters=[
            version.VersionParameter(
                parameterKey="param-1",
                defaultValue="12345",
                description="param description",
            ),
            version.VersionParameter(parameterKey="param-2"),
        ],
        draftTemplateLocation="prod-11111111/version-123/draft_workbench.yml",
    )
    mock_unit_of_work.commit.assert_called()
    message_bus_mock.publish.assert_called_with(
        product_version_update_started.ProductVersionUpdateStarted(
            product_id="prod-11111111",
            version_id="version-123",
            aws_account_id="3",
            product_type="CONTAINER",
        )
    )


@pytest.mark.parametrize(
    "previous_release_name,new_version_name,version_type",
    (("1.2.3-restored.1", "", version.VersionType.Restored.text),),
)
@mock.patch("app.publishing.domain.model.version.random.choice", lambda chars: "1")
@freeze_time("2023-06-20")
def test_handle_should_raise_error_when_updating_restored_version(
    previous_release_name,
    new_version_name,
    version_type,
    version_query_service_mock,
    stack_service_mock,
    amis_query_service_mock,
    get_test_ami,
    file_service_mock,
    template_service_mock,
    generic_repo_mock,
    get_product,
    mock_unit_of_work,
    message_bus_mock,
    mock_command,
    mock_products_repo,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    test_ami = get_test_ami()
    amis_query_service_mock.get_ami.return_value = test_ami
    update_product_version_command_mock = mock_command()
    # ACT
    with pytest.raises(domain_exception.DomainException) as error:
        update_version_command_handler.handle(
            command=update_product_version_command_mock,
            uow=mock_unit_of_work,
            message_bus=message_bus_mock,
            version_qry_srv=version_query_service_mock,
            stack_srv=stack_service_mock,
            amis_qry_srv=amis_query_service_mock,
            file_service=file_service_mock,
            template_query_service=template_service_mock,
        )
    assertpy.assert_that(str(error.value)).is_equal_to("Only release candidate versions can be updated")


@pytest.mark.parametrize(
    "previous_release_name,new_version_name,version_type,has_component_details",
    (
        ("1.2.3-rc.1", "1.2.3-rc.2", version.VersionType.ReleaseCandidate.text, True),
        (
            "1.3.7-rc.56",
            "1.3.7-rc.57",
            version.VersionType.ReleaseCandidate.text,
            False,
        ),
    ),
)
@mock.patch("app.publishing.domain.model.version.random.choice", lambda chars: "1")
@freeze_time("2023-06-20")
def test_handle_should_update_version_if_ami_has_no_components_details(
    previous_release_name,
    new_version_name,
    version_type,
    has_component_details,
    mock_command,
    version_query_service_mock,
    stack_service_mock,
    amis_query_service_mock,
    get_test_ami,
    file_service_mock,
    template_service_mock,
    generic_repo_mock,
    mock_unit_of_work,
    message_bus_mock,
    get_product,
    mock_products_repo,
    mock_version_repo,
):
    # ARRANGE
    mock_products_repo.get.return_value = get_product()

    test_ami = get_test_ami(has_components_details=has_component_details)
    amis_query_service_mock.get_ami.return_value = test_ami
    update_product_version_command_mock = mock_command()
    # ACT
    update_version_command_handler.handle(
        command=update_product_version_command_mock,
        uow=mock_unit_of_work,
        message_bus=message_bus_mock,
        version_qry_srv=version_query_service_mock,
        stack_srv=stack_service_mock,
        amis_qry_srv=amis_query_service_mock,
        file_service=file_service_mock,
        template_query_service=template_service_mock,
    )

    # ASSERT
    version_query_service_mock.get_product_version_distributions.assert_any_call(
        product_id="prod-11111111", version_id="version-123"
    )
    current_time = datetime.now(timezone.utc).isoformat()
    mock_version_repo.update_attributes.assert_called_with(
        pk=version.VersionPrimaryKey(
            productId="prod-11111111",
            versionId="version-123",
            awsAccountId="3",
        ),
        copiedAmiId=None,
        originalAmiId="ami-023c04780e65e723c",
        lastUpdateDate=current_time,
        lastUpdatedBy="user-12345",
        versionName=new_version_name,
        versionDescription="Workbench version description",
        status=version.VersionStatus.Updating,
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
        draftTemplateLocation="prod-11111111/version-123/draft_workbench.yml",
    )
    mock_unit_of_work.commit.assert_called()
    message_bus_mock.publish.assert_called_with(
        product_version_update_started.ProductVersionUpdateStarted(
            product_id="prod-11111111",
            version_id="version-123",
            aws_account_id="3",
            product_type="WORKBENCH",
        )
    )
