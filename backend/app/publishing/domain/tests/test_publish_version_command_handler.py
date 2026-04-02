import logging
import tempfile
from unittest import mock

import pytest
from freezegun import freeze_time

from app.publishing.domain.command_handlers import publish_version_command_handler
from app.publishing.domain.commands import publish_version_command
from app.publishing.domain.events import product_version_published
from app.publishing.domain.model import product, shared_ami, version
from app.publishing.domain.ports import (
    catalog_query_service,
    catalog_service,
    projects_query_service,
    shared_amis_query_service,
    template_service,
)
from app.publishing.domain.query_services import template_domain_query_service
from app.publishing.domain.read_models import project
from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    event_name_value_object,
    product_id_value_object,
    version_id_value_object,
)
from app.shared.adapters.message_bus import message_bus

TEST_PROJECT_ID = "proj-12345"
TEST_PRODUCT_ID = "prod-12345"
TEST_VERSION_ID = "vers-12345abc"
TEST_AWS_ACCOUNT_ID = "123456789012"


@pytest.fixture()
def command_mock() -> publish_version_command.PublishVersionCommand:
    return publish_version_command.PublishVersionCommand(
        productId=product_id_value_object.from_str(TEST_PRODUCT_ID),
        versionId=version_id_value_object.from_str(TEST_VERSION_ID),
        awsAccountId=aws_account_id_value_object.from_str(TEST_AWS_ACCOUNT_ID),
        previousEventName=event_name_value_object.from_str("ProductVersionCreationStarted"),
    )


@pytest.fixture()
def get_product():
    def _get_product(
        product_type: product.ProductType = product.ProductType.Workbench,
        status: product.ProductStatus = product.ProductStatus.Created,
    ):
        return product.Product(
            projectId=TEST_PROJECT_ID,
            productId=TEST_PRODUCT_ID,
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
def get_version():
    def _get_version(
        product_type: product.ProductType = product.ProductType.Workbench,
    ):
        additional_attrs = {}
        additional_attrs["draftTemplateLocation"] = f"{TEST_PRODUCT_ID}/{TEST_VERSION_ID}/workbench-template.yml"
        additional_attrs["originalAmiId"] = "ami-12345"
        additional_attrs["copiedAmiId"] = "ami-12345"
        additional_attrs["platform"] = "Linux"
        additional_attrs["integrations"] = ["GitHub"]
        additional_attrs["hasIntegrations"] = True
        return version.Version(
            projectId=TEST_PROJECT_ID,
            productId=TEST_PRODUCT_ID,
            technologyId="tech-12345",
            versionId=TEST_VERSION_ID,
            versionName="1.0.0-rc.2",
            versionType=version.VersionType.ReleaseCandidate.text,
            awsAccountId=TEST_AWS_ACCOUNT_ID,
            stage=version.VersionStage.DEV,
            region="us-east-1",
            status=version.VersionStatus.Creating,
            scPortfolioId="port-12345",
            isRecommendedVersion=True,
            createDate="2023-07-13T00:00:00+00:00",
            lastUpdateDate="2023-07-13T00:00:00+00:00",
            createdBy="T000001",
            lastUpdatedBy="T000001",
            **additional_attrs,
        )

    return _get_version


@pytest.fixture()
def catalog_service_mock():
    catalog_srv_mock = mock.create_autospec(spec=catalog_service.CatalogService)
    catalog_srv_mock.create_provisioning_artifact.return_value = "pa-12345"
    catalog_srv_mock.create_product.return_value = TEST_PRODUCT_ID, "pa-12345"
    catalog_srv_mock.associate_product_with_portfolio.return_value = None
    catalog_srv_mock.create_launch_constraint.return_value = None
    catalog_srv_mock.create_resource_update_constraint.return_value = None
    catalog_srv_mock.delete_provisioning_artifact.return_value = None
    return catalog_srv_mock


@pytest.fixture()
def catalog_query_service_mock():
    catalog_qry_srv_mock = mock.create_autospec(spec=catalog_query_service.CatalogQueryService)
    catalog_qry_srv_mock.get_sc_product_id.return_value = TEST_PRODUCT_ID
    catalog_qry_srv_mock.get_sc_provisioning_artifact_id.side_effect = [
        "pa-12345",
        "pa-old",
    ]
    catalog_qry_srv_mock.get_launch_constraint_id.return_value = "cons-12345"
    catalog_qry_srv_mock.get_resource_update_constraint_id.return_value = "cons-6789"
    catalog_qry_srv_mock.get_provisioning_parameters.return_value = [
        version.VersionParameter(
            defaultValue="value-1",
            description="description",
            isNoEcho=False,
            parameterConstraints=version.ParameterConstraints(
                allowedPattern="[A-Za-z0-9]+",
                allowedValues=["value-1", "value-2", "value-3"],
                constraintDescription="description",
                maxLength="10",
                maxValue="99999",
                minLength="1",
                minValue="0",
            ),
            parameterKey="key-1",
            parameterType="string",
        ),
        version.VersionParameter(parameterKey="key-2"),
    ], None
    return catalog_qry_srv_mock


@pytest.fixture()
def projects_query_service_mock():
    projects_qs = mock.create_autospec(spec=projects_query_service.ProjectsQueryService)
    projects_qs.get_project.return_value = [
        project.Project(
            projectId="proj-12345",
            projectName="Program A",
            projectDescription="Program A description",
        ),
        project.Project(
            projectId="proj-56789",
            projectName="Program B",
            projectDescription="Program B description",
        ),
    ]
    projects_qs.get_project.return_value = project.Project(
        projectId="proj-12345",
        projectName="Program A",
        projectDescription="Program A description",
    )
    return projects_qs


@pytest.fixture
def shared_amis_query_service_mock():
    shared_amis_qry_srv_mock = mock.create_autospec(spec=shared_amis_query_service.SharedAMIsQueryService)
    shared_amis_qry_srv_mock.get_shared_amis.return_value = [
        shared_ami.SharedAmi(
            originalAmiId="ami-12345",
            copiedAmiId="ami-12345",
            awsAccountId="123456789012",
            region="us-east-1",
            createDate="2023-07-13T00:00:00+00:00",
            lastUpdateDate="2023-07-13T00:00:00+00:00",
        ),
        shared_ami.SharedAmi(
            originalAmiId="ami-12345",
            copiedAmiId="ami-54321",
            awsAccountId="123456789013",
            region="eu-west-3",
            createDate="2023-07-13T00:00:00+00:00",
            lastUpdateDate="2023-07-13T00:00:00+00:00",
        ),
    ]
    return shared_amis_qry_srv_mock


@pytest.fixture
def file_service_mock():
    file_mock = mock.create_autospec(spec=template_service.TemplateService)
    file_mock.put_template.return_value = None
    file_mock.does_template_exist.return_value = False
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(b"my product template")
    file_mock.get_template.return_value = temp_file.name
    temp_file.close()
    return file_mock


@pytest.fixture
def template_service_mock():
    return mock.create_autospec(spec=template_domain_query_service.TemplateDomainQueryService)


@pytest.fixture()
def get_template_path():
    def _get_template_path(
        product_type: product.ProductType = product.ProductType.Workbench,
    ):
        return "workbench-template.yml"

    return _get_template_path


@pytest.fixture()
def logger_mock():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@pytest.fixture()
def message_bus_mock():
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    return message_bus_mock


@freeze_time("2023-07-13")
def test_publish_version_publishes_version_when_product_does_not_exist(
    command_mock,
    mock_unit_of_work,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_version_repo,
    message_bus_mock,
    projects_query_service_mock,
    file_service_mock,
    shared_amis_query_service_mock,
    template_service_mock,
    mock_products_repo,
    get_product,
    get_version,
    get_template_path,
):
    # ARRANGE
    catalog_query_service_mock.get_sc_product_id.return_value = None
    catalog_query_service_mock.get_sc_provisioning_artifact_id.side_effect = [
        None,
        None,
    ]
    catalog_query_service_mock.get_launch_constraint_id.return_value = None
    catalog_query_service_mock.get_resource_update_constraint_id.return_value = None
    product_entity = get_product()
    version_entity = get_version()
    mock_products_repo.get.return_value = product_entity
    mock_version_repo.get.return_value = version_entity
    template_service_mock.get_default_template_file_name.return_value = get_template_path()
    # ACT
    publish_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        projects_qry_srv=projects_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
        file_srv=file_service_mock,
        shared_amis_qry_srv=shared_amis_query_service_mock,
        template_qry_srv=template_service_mock,
    )

    # ASSERT
    catalog_service_mock.create_product.assert_called_once_with(
        region="us-east-1",
        product_name=f"{product_entity.productId}-123456789012",
        owner=version_entity.createdBy,
        product_description=product_entity.productDescription,
        version_id=version_entity.versionId,
        version_name="1.0.0-rc.2",
        version_description=version_entity.versionDescription,
        template_path=f"{product_entity.productId}/vers-12345abc/workbench-template.yml",
    )
    catalog_service_mock.associate_product_with_portfolio.assert_called_once_with(
        region="us-east-1",
        sc_portfolio_id="port-12345",
        sc_product_id=product_entity.productId,
    )
    catalog_service_mock.create_launch_constraint.assert_called_once_with(
        region="us-east-1",
        sc_portfolio_id="port-12345",
        sc_product_id=product_entity.productId,
    )
    catalog_service_mock.create_resource_update_constraint.assert_called_once_with(
        region="us-east-1",
        sc_portfolio_id="port-12345",
        sc_product_id=product_entity.productId,
    )
    mock_version_repo.update_attributes.assert_called_once_with(
        pk=version.VersionPrimaryKey(
            productId=product_entity.productId,
            versionId=version_entity.versionId,
            awsAccountId=version_entity.awsAccountId,
        ),
        scProductId=product_entity.productId,
        scProvisioningArtifactId="pa-12345",
        templateLocation=f"{product_entity.productId}/{version_entity.versionId}/workbench-template.yml",
        status=version.VersionStatus.Created,
        parameters=[
            version.VersionParameter(
                defaultValue="value-1",
                description="description",
                isNoEcho=False,
                parameterConstraints=version.ParameterConstraints(
                    allowedPattern="[A-Za-z0-9]+",
                    allowedValues=["value-1", "value-2", "value-3"],
                    constraintDescription="description",
                    maxLength="10",
                    maxValue="99999",
                    minLength="1",
                    minValue="0",
                ),
                parameterKey="key-1",
                parameterType="string",
            ).model_dump(),
            version.VersionParameter(parameterKey="key-2").model_dump(),
        ],
        metadata=None,
        lastUpdateDate="2023-07-13T00:00:00+00:00",
    )
    mock_unit_of_work.commit.assert_called_once()
    catalog_service_mock.delete_provisioning_artifact.assert_not_called()
    message_bus_mock.publish.assert_called_once_with(
        product_version_published.ProductVersionPublished(
            projectId=TEST_PROJECT_ID,
            projectName="Program A",
            productId=product_entity.productId,
            productName=product_entity.productName,
            versionId=version_entity.versionId,
            awsAccountId=version_entity.awsAccountId,
            stage=version.VersionStage.DEV,
            region=version_entity.region,
            versionName="1.0.0-rc.2",
            versionDescription=version_entity.versionDescription,
            scProductId=product_entity.productId,
            scProvisioningArtifactId="pa-12345",
            amiId="ami-12345",
            platform="Linux",
            integrations=["GitHub"],
            hasIntegrations=True,
        )
    )
    projects_query_service_mock.get_project.assert_called_once()


@freeze_time("2023-07-13")
def test_publish_version_publishes_version_when_product_exists_version_does_not_exist(
    command_mock,
    mock_unit_of_work,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_version_repo,
    message_bus_mock,
    projects_query_service_mock,
    file_service_mock,
    shared_amis_query_service_mock,
    template_service_mock,
    mock_products_repo,
    get_product,
    get_version,
    get_template_path,
):
    # ARRANGE
    catalog_query_service_mock.get_sc_provisioning_artifact_id.side_effect = [
        None,
        None,
    ]
    product_entity = get_product()
    version_entity = get_version()
    template_entity = get_template_path()
    mock_products_repo.get.return_value = product_entity
    mock_version_repo.get.return_value = version_entity
    template_service_mock.get_default_template_file_name.return_value = template_entity
    # ACT
    publish_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
        projects_qry_srv=projects_query_service_mock,
        file_srv=file_service_mock,
        shared_amis_qry_srv=shared_amis_query_service_mock,
        template_qry_srv=template_service_mock,
    )

    # ASSERT
    catalog_service_mock.create_provisioning_artifact.assert_called_once_with(
        region=version_entity.region,
        version_id=version_entity.versionId,
        version_name="1.0.0-rc.2",
        sc_product_id="prod-12345",
        description=None,
        template_path=f"{product_entity.productId}/{version_entity.versionId}/{template_entity}",
    )
    mock_version_repo.update_attributes.assert_called_once_with(
        pk=version.VersionPrimaryKey(
            productId=product_entity.productId,
            versionId=version_entity.versionId,
            awsAccountId=version_entity.awsAccountId,
        ),
        scProductId=product_entity.productId,
        scProvisioningArtifactId="pa-12345",
        templateLocation=f"{product_entity.productId}/{version_entity.versionId}/{template_entity}",
        status=version.VersionStatus.Created,
        parameters=[
            version.VersionParameter(
                defaultValue="value-1",
                description="description",
                isNoEcho=False,
                parameterConstraints=version.ParameterConstraints(
                    allowedPattern="[A-Za-z0-9]+",
                    allowedValues=["value-1", "value-2", "value-3"],
                    constraintDescription="description",
                    maxLength="10",
                    maxValue="99999",
                    minLength="1",
                    minValue="0",
                ),
                parameterKey="key-1",
                parameterType="string",
            ).model_dump(),
            version.VersionParameter(parameterKey="key-2").model_dump(),
        ],
        metadata=None,
        lastUpdateDate="2023-07-13T00:00:00+00:00",
    )
    mock_unit_of_work.commit.assert_called_once()
    catalog_service_mock.delete_provisioning_artifact.assert_not_called()
    message_bus_mock.publish.assert_called_once_with(
        product_version_published.ProductVersionPublished(
            projectId=TEST_PROJECT_ID,
            projectName="Program A",
            productId=product_entity.productId,
            productName=product_entity.productName,
            versionId=version_entity.versionId,
            versionDescription=version_entity.versionDescription,
            awsAccountId=version_entity.awsAccountId,
            stage=version.VersionStage.DEV,
            region=version_entity.region,
            versionName="1.0.0-rc.2",
            scProductId=product_entity.productId,
            scProvisioningArtifactId="pa-12345",
            amiId="ami-12345",
            platform="Linux",
            integrations=["GitHub"],
            hasIntegrations=True,
        )
    )
    projects_query_service_mock.get_project.assert_called_once()


@freeze_time("2023-07-13")
def test_publish_version_publishes_version_when_product_and_version_exist(
    command_mock,
    mock_unit_of_work,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_version_repo,
    message_bus_mock,
    projects_query_service_mock,
    file_service_mock,
    shared_amis_query_service_mock,
    template_service_mock,
    get_product,
    get_version,
    get_template_path,
    mock_products_repo,
):
    # ARRANGE
    catalog_query_service_mock.get_sc_provisioning_artifact_id.side_effect = [
        "pa-12345",
        "pa-old",
    ]
    command_mock.previousEventName = event_name_value_object.from_str("ProductVersionUpdateStarted")
    product_entity = get_product()
    version_entity = get_version()
    template_entity = get_template_path()
    mock_products_repo.get.return_value = product_entity
    mock_version_repo.get.return_value = version_entity
    template_service_mock.get_default_template_file_name.return_value = template_entity

    # ACT
    publish_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
        projects_qry_srv=projects_query_service_mock,
        file_srv=file_service_mock,
        shared_amis_qry_srv=shared_amis_query_service_mock,
        template_qry_srv=template_service_mock,
    )

    # ASSERT
    mock_version_repo.update_attributes.assert_called_once_with(
        pk=version.VersionPrimaryKey(
            productId=product_entity.productId,
            versionId=version_entity.versionId,
            awsAccountId=version_entity.awsAccountId,
        ),
        scProductId=product_entity.productId,
        scProvisioningArtifactId="pa-12345",
        templateLocation=f"{product_entity.productId}/{version_entity.versionId}/{template_entity}",
        status=version.VersionStatus.Created,
        parameters=[
            version.VersionParameter(
                defaultValue="value-1",
                description="description",
                isNoEcho=False,
                parameterConstraints=version.ParameterConstraints(
                    allowedPattern="[A-Za-z0-9]+",
                    allowedValues=["value-1", "value-2", "value-3"],
                    constraintDescription="description",
                    maxLength="10",
                    maxValue="99999",
                    minLength="1",
                    minValue="0",
                ),
                parameterKey="key-1",
                parameterType="string",
            ).model_dump(),
            version.VersionParameter(parameterKey="key-2").model_dump(),
        ],
        metadata=None,
        lastUpdateDate="2023-07-13T00:00:00+00:00",
    )
    mock_unit_of_work.commit.assert_called_once()
    catalog_service_mock.delete_provisioning_artifact.assert_called_once_with(
        region="us-east-1",
        sc_product_id="prod-12345",
        sc_provisioning_artifact_id="pa-old",
    )
    message_bus_mock.publish.assert_called_once_with(
        product_version_published.ProductVersionPublished(
            projectId=TEST_PROJECT_ID,
            projectName="Program A",
            productId=product_entity.productId,
            productName=product_entity.productName,
            versionId=version_entity.versionId,
            versionDescription=version_entity.versionDescription,
            awsAccountId=version_entity.awsAccountId,
            stage=version.VersionStage.DEV,
            region=version_entity.region,
            versionName="1.0.0-rc.2",
            scProductId=product_entity.productId,
            scProvisioningArtifactId="pa-12345",
            amiId="ami-12345",
            platform="Linux",
            integrations=["GitHub"],
            hasIntegrations=True,
        )
    )
    projects_query_service_mock.get_project.assert_called_once()


@freeze_time("2023-07-13")
def test_publish_version_publishes_version_when_product_and_version_exist_for(
    command_mock,
    mock_unit_of_work,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_version_repo,
    message_bus_mock,
    projects_query_service_mock,
    file_service_mock,
    shared_amis_query_service_mock,
    template_service_mock,
    get_product,
    get_version,
    get_template_path,
    mock_products_repo,
):
    # ARRANGE
    catalog_query_service_mock.get_sc_provisioning_artifact_id.side_effect = [
        "pa-12345",
        "pa-old",
    ]
    command_mock.previousEventName = event_name_value_object.from_str("ProductVersionUpdateStarted")
    product_entity = get_product()
    version_entity = get_version()
    template_entity = get_template_path()
    mock_products_repo.get.return_value = product_entity
    mock_version_repo.get.return_value = version_entity
    template_service_mock.get_default_template_file_name.return_value = template_entity

    # ACT
    publish_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
        projects_qry_srv=projects_query_service_mock,
        file_srv=file_service_mock,
        shared_amis_qry_srv=shared_amis_query_service_mock,
        template_qry_srv=template_service_mock,
    )

    # ASSERT
    mock_version_repo.update_attributes.assert_called_once_with(
        pk=version.VersionPrimaryKey(
            productId=product_entity.productId,
            versionId=version_entity.versionId,
            awsAccountId=version_entity.awsAccountId,
        ),
        scProductId=product_entity.productId,
        scProvisioningArtifactId="pa-12345",
        templateLocation=f"{product_entity.productId}/{version_entity.versionId}/{template_entity}",
        status=version.VersionStatus.Created,
        parameters=[
            version.VersionParameter(
                defaultValue="value-1",
                description="description",
                isNoEcho=False,
                parameterConstraints=version.ParameterConstraints(
                    allowedPattern="[A-Za-z0-9]+",
                    allowedValues=["value-1", "value-2", "value-3"],
                    constraintDescription="description",
                    maxLength="10",
                    maxValue="99999",
                    minLength="1",
                    minValue="0",
                ),
                parameterKey="key-1",
                parameterType="string",
            ).model_dump(),
            version.VersionParameter(parameterKey="key-2").model_dump(),
        ],
        metadata=None,
        lastUpdateDate="2023-07-13T00:00:00+00:00",
    )
    mock_unit_of_work.commit.assert_called_once()
    catalog_service_mock.delete_provisioning_artifact.assert_called_once_with(
        region="us-east-1",
        sc_product_id="prod-12345",
        sc_provisioning_artifact_id="pa-old",
    )
    message_bus_mock.publish.assert_called_once_with(
        product_version_published.ProductVersionPublished(
            projectId=TEST_PROJECT_ID,
            projectName="Program A",
            productId=product_entity.productId,
            productName=product_entity.productName,
            versionId=version_entity.versionId,
            versionDescription=version_entity.versionDescription,
            awsAccountId=version_entity.awsAccountId,
            stage=version.VersionStage.DEV,
            region=version_entity.region,
            versionName="1.0.0-rc.2",
            scProductId=product_entity.productId,
            scProvisioningArtifactId="pa-12345",
            amiId="ami-12345",
            platform="Linux",
            integrations=["GitHub"],
            hasIntegrations=True,
        )
    )
    projects_query_service_mock.get_project.assert_called_once()


@freeze_time("2023-07-13")
def test_publish_version_when_contains_metadata_should_store_metadata_in_db(
    command_mock,
    mock_unit_of_work,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_version_repo,
    message_bus_mock,
    projects_query_service_mock,
    file_service_mock,
    shared_amis_query_service_mock,
    template_service_mock,
    get_product,
    get_version,
    get_template_path,
    mock_products_repo,
):
    # ARRANGE
    catalog_query_service_mock.get_sc_provisioning_artifact_id.side_effect = [
        "pa-12345",
        "pa-old",
    ]
    catalog_query_service_mock.get_provisioning_parameters.return_value = [], {
        "MyMetadataKey": version.ProductVersionMetadataItem(label="My meta label", value=["My meta value"])
    }
    command_mock.previousEventName = event_name_value_object.from_str("ProductVersionUpdateStarted")
    product_entity = get_product()
    version_entity = get_version()
    template_entity = get_template_path()
    mock_products_repo.get.return_value = product_entity
    mock_version_repo.get.return_value = version_entity
    template_service_mock.get_default_template_file_name.return_value = template_entity

    # ACT
    publish_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
        projects_qry_srv=projects_query_service_mock,
        file_srv=file_service_mock,
        shared_amis_qry_srv=shared_amis_query_service_mock,
        template_qry_srv=template_service_mock,
    )

    # ASSERT
    mock_version_repo.update_attributes.assert_called_once_with(
        pk=version.VersionPrimaryKey(
            productId=product_entity.productId,
            versionId=version_entity.versionId,
            awsAccountId=version_entity.awsAccountId,
        ),
        scProductId=product_entity.productId,
        scProvisioningArtifactId="pa-12345",
        templateLocation=f"{product_entity.productId}/{version_entity.versionId}/{template_entity}",
        status=version.VersionStatus.Created,
        parameters=[],
        metadata={"MyMetadataKey": {"label": "My meta label", "value": ["My meta value"]}},
        lastUpdateDate="2023-07-13T00:00:00+00:00",
    )
    mock_unit_of_work.commit.assert_called_once()
    projects_query_service_mock.get_project.assert_called_once()


@freeze_time("2023-07-13")
def test_publish_version_publishes_version_when_promoted(
    command_mock,
    mock_unit_of_work,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    mock_version_repo,
    message_bus_mock,
    projects_query_service_mock,
    file_service_mock,
    shared_amis_query_service_mock,
    template_service_mock,
    get_product,
    get_version,
    get_template_path,
    mock_products_repo,
):
    # ARRANGE
    catalog_query_service_mock.get_sc_product_id.return_value = None
    catalog_query_service_mock.get_sc_provisioning_artifact_id.side_effect = [
        None,
        None,
    ]
    catalog_query_service_mock.get_launch_constraint_id.return_value = None
    catalog_query_service_mock.get_resource_update_constraint_id.return_value = None
    command_mock.previousEventName = event_name_value_object.from_str("ProductVersionPromotionStarted")
    product_entity = get_product()
    version_entity = get_version()
    template_entity = get_template_path()
    mock_products_repo.get.return_value = product_entity
    mock_version_repo.get.return_value = version_entity
    template_service_mock.get_default_template_file_name.return_value = template_entity

    # ACT
    publish_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
        projects_qry_srv=projects_query_service_mock,
        file_srv=file_service_mock,
        shared_amis_qry_srv=shared_amis_query_service_mock,
        template_qry_srv=template_service_mock,
    )

    # ASSERT
    catalog_service_mock.create_product.assert_called_once_with(
        region="us-east-1",
        product_name=f"{product_entity.productId}-123456789012",
        owner=version_entity.createdBy,
        product_description=product_entity.productDescription,
        version_id=version_entity.versionId,
        version_name="1.0.0-rc.2",
        version_description=None,
        template_path=f"{product_entity.productId}/{version_entity.versionId}/{template_entity}",
    )
    catalog_service_mock.associate_product_with_portfolio.assert_called_once_with(
        region="us-east-1", sc_portfolio_id="port-12345", sc_product_id="prod-12345"
    )
    catalog_service_mock.create_launch_constraint.assert_called_once_with(
        region="us-east-1",
        sc_portfolio_id="port-12345",
        sc_product_id=product_entity.productId,
    )
    catalog_service_mock.create_resource_update_constraint.assert_called_once_with(
        region="us-east-1",
        sc_portfolio_id="port-12345",
        sc_product_id=product_entity.productId,
    )
    mock_version_repo.update_attributes.assert_called_once_with(
        version.VersionPrimaryKey(
            productId=product_entity.productId,
            versionId=version_entity.versionId,
            awsAccountId=version_entity.awsAccountId,
        ),
        scProductId=product_entity.productId,
        scProvisioningArtifactId="pa-12345",
        templateLocation=f"{product_entity.productId}/{version_entity.versionId}/{template_entity}",
        status=version.VersionStatus.Created,
        parameters=[
            version.VersionParameter(
                defaultValue="value-1",
                description="description",
                isNoEcho=False,
                parameterConstraints=version.ParameterConstraints(
                    allowedPattern="[A-Za-z0-9]+",
                    allowedValues=["value-1", "value-2", "value-3"],
                    constraintDescription="description",
                    maxLength="10",
                    maxValue="99999",
                    minLength="1",
                    minValue="0",
                ),
                parameterKey="key-1",
                parameterType="string",
            ).model_dump(),
            version.VersionParameter(parameterKey="key-2").model_dump(),
        ],
        metadata=None,
        lastUpdateDate="2023-07-13T00:00:00+00:00",
    )
    mock_unit_of_work.commit.assert_called_once()
    catalog_service_mock.delete_provisioning_artifact.assert_not_called()
    message_bus_mock.publish.assert_called_once_with(
        product_version_published.ProductVersionPublished(
            projectId=TEST_PROJECT_ID,
            projectName="Program A",
            productId=product_entity.productId,
            productName=product_entity.productName,
            versionId=version_entity.versionId,
            versionDescription=version_entity.versionDescription,
            awsAccountId=version_entity.awsAccountId,
            stage=version.VersionStage.DEV,
            region=version_entity.region,
            versionName="1.0.0-rc.2",
            scProductId=product_entity.productId,
            scProvisioningArtifactId="pa-12345",
            amiId="ami-12345",
            platform="Linux",
            integrations=["GitHub"],
            hasIntegrations=True,
        )
    )
    projects_query_service_mock.get_project.assert_called_once()


def test_publish_when_no_notification_constraint_should_assign_notification_constraint(
    command_mock,
    mock_unit_of_work,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    message_bus_mock,
    projects_query_service_mock,
    file_service_mock,
    shared_amis_query_service_mock,
    template_service_mock,
    get_product,
    get_version,
    get_template_path,
    mock_products_repo,
    mock_version_repo,
):
    # ARRANGE
    catalog_query_service_mock.get_sc_product_id.return_value = None
    catalog_query_service_mock.get_sc_provisioning_artifact_id.side_effect = [
        None,
        None,
    ]
    catalog_query_service_mock.get_launch_constraint_id.return_value = None
    catalog_query_service_mock.get_notification_constraint_id.return_value = None
    catalog_query_service_mock.get_resource_update_constraint_id.return_value = None
    product_entity = get_product()
    version_entity = get_version()
    template_entity = get_template_path()
    mock_products_repo.get.return_value = product_entity
    mock_version_repo.get.return_value = version_entity
    template_service_mock.get_default_template_file_name.return_value = template_entity
    # ACT
    publish_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
        projects_qry_srv=projects_query_service_mock,
        file_srv=file_service_mock,
        shared_amis_qry_srv=shared_amis_query_service_mock,
        template_qry_srv=template_service_mock,
    )

    # ASSERT
    catalog_service_mock.create_notification_constraint.assert_called_once_with(
        region="us-east-1",
        sc_portfolio_id="port-12345",
        sc_product_id="prod-12345",
    )
    catalog_service_mock.create_resource_update_constraint.assert_called_once_with(
        region="us-east-1",
        sc_portfolio_id="port-12345",
        sc_product_id="prod-12345",
    )
    projects_query_service_mock.get_project.assert_called_once()


def test_publish_when_notification_constraint_exists_should_not_assign_notification_constraint(
    command_mock,
    mock_unit_of_work,
    catalog_service_mock,
    catalog_query_service_mock,
    logger_mock,
    message_bus_mock,
    projects_query_service_mock,
    file_service_mock,
    shared_amis_query_service_mock,
    template_service_mock,
    get_product,
    get_version,
    get_template_path,
    mock_products_repo,
    mock_version_repo,
):
    # ARRANGE
    catalog_query_service_mock.get_sc_product_id.return_value = None
    catalog_query_service_mock.get_sc_provisioning_artifact_id.side_effect = [
        None,
        None,
    ]
    catalog_query_service_mock.get_launch_constraint_id.return_value = None
    catalog_query_service_mock.get_notification_constraint_id.return_value = "notification-arn"
    product_entity = get_product()
    version_entity = get_version()
    template_entity = get_template_path()
    mock_products_repo.get.return_value = product_entity
    mock_version_repo.get.return_value = version_entity
    template_service_mock.get_default_template_file_name.return_value = template_entity

    # ACT
    publish_version_command_handler.handle(
        cmd=command_mock,
        uow=mock_unit_of_work,
        catalog_qry_srv=catalog_query_service_mock,
        catalog_srv=catalog_service_mock,
        logger=logger_mock,
        msg_bus=message_bus_mock,
        projects_qry_srv=projects_query_service_mock,
        file_srv=file_service_mock,
        shared_amis_qry_srv=shared_amis_query_service_mock,
        template_qry_srv=template_service_mock,
    )

    # ASSERT
    catalog_service_mock.create_notification_constraint.assert_not_called()
    projects_query_service_mock.get_project.assert_called_once()
