import json
import unittest
from datetime import datetime, timezone
from unittest import mock

import assertpy
import pydantic
import pytest
from freezegun import freeze_time

from app.publishing.domain.commands import (
    archive_product_command,
    create_product_command,
    create_version_command,
    promote_version_command,
    restore_version_command,
    retire_version_command,
    retry_version_command,
    set_recommended_version_command,
    update_version_command,
    validate_version_command,
)
from app.publishing.domain.model import portfolio, product, version, version_summary
from app.publishing.domain.ports import versions_query_service
from app.publishing.domain.query_services import (
    amis_domain_query_service,
    portfolios_domain_query_service,
    products_domain_query_service,
    template_domain_query_service,
    versions_domain_query_service,
)
from app.publishing.domain.read_models import ami
from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    major_version_name_value_object,
    product_description_value_object,
    product_id_value_object,
    product_name_value_object,
    product_type_value_object,
    project_id_value_object,
    stage_value_object,
    tech_id_value_object,
    tech_name_value_object,
    user_id_value_object,
    user_role_value_object,
    version_description_value_object,
    version_id_value_object,
    version_release_type_value_object,
    version_template_definition_value_object,
)
from app.publishing.entrypoints.api import bootstrapper
from app.publishing.entrypoints.api.model import api_model
from app.shared.adapters.message_bus import in_memory_command_bus
from app.shared.middleware.authorization import VirtualWorkbenchRoles

TEST_PRODUCT_ID = "prod-123"
TEST_VERSION_ID = "vers-123"


@pytest.fixture
def mocked_portfolios_domain_query_service() -> portfolios_domain_query_service.PortfoliosDomainQueryService:
    portfolio_domain_qry_srv_mock = unittest.mock.create_autospec(
        spec=portfolios_domain_query_service.PortfoliosDomainQueryService
    )
    portfolio_domain_qry_srv_mock.get_portfolios_by_tech_and_stage.return_value = [
        portfolio.Portfolio(
            portfolioId=f"port-{i}abc",
            scPortfolioId=f"port-{i}",
            projectId="proj-12345",
            technologyId="tech-12345",
            awsAccountId=f"{i}",
            accountId="1d0b2901-9482-4ce5-9d91-582fe0b14d7b",
            stage="DEV",
            region="us-east-1",
            status=portfolio.PortfolioStatus.Created,
            createDate="2023-06-20T00:00:00+00:00",
            lastUpdateDate="2023-06-20T00:00:00+00:00",
        )
        for i in range(5)
    ]
    return portfolio_domain_qry_srv_mock


@pytest.fixture()
@freeze_time("2023-07-24")
def mocked_products_domain_query_service() -> products_domain_query_service.ProductsDomainQueryService:
    products_domain_query_service_mock = unittest.mock.create_autospec(
        spec=products_domain_query_service.ProductsDomainQueryService
    )
    products_domain_query_service_mock.get_products.return_value = [
        product.Product(
            projectId="proj-12345",
            productId=f"prod-{str(i)}",
            technologyId="tech-1",
            technologyName="Test technology",
            status="CREATED",
            productName=f"Product {str(i)}",
            productType=product.ProductType.Workbench,
            createDate=datetime.now(timezone.utc).isoformat(),
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            createdBy="T0012AB",
            lastUpdatedBy="T0012AB",
        )
        for i in range(5)
    ]
    products_domain_query_service_mock.get_product.return_value = (
        product.Product(
            projectId="proj-12345",
            productId="prod-54321",
            technologyId="tech-1",
            technologyName="Test technology",
            status="CREATED",
            productName="Product A",
            productType=product.ProductType.Workbench,
            createDate=datetime.now(timezone.utc).isoformat(),
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            createdBy="T0012AB",
            lastUpdatedBy="T0012AB",
        ),
        [
            version_summary.VersionSummary(
                versionId=TEST_VERSION_ID,
                name="1.0.0",
                description="Test Description",
                versionType=version.VersionType.Released.text,
                stages=[version.VersionStage.DEV],
                status=version_summary.VersionSummaryStatus.Created,
                recommendedVersion=True,
                lastUpdate="2020-01-01",
                lastUpdatedBy="T0011AA",
                restoredFromVersionName="1.0.0",
            )
        ],
    )
    products_domain_query_service_mock.get_products_ready_for_provisioning.return_value = [
        product.Product(
            projectId="proj-12345",
            productId=f"prod-{str(i)}",
            technologyId="tech-1",
            technologyName="Test technology",
            status=product.ProductStatus.Created,
            productName=f"Product {str(i)}",
            productType=product.ProductType.Workbench,
            availableStages=[
                product.ProductStage.DEV,
                product.ProductStage.QA,
                product.ProductStage.PROD,
            ],
            availableRegions=["us-east-1", "eu-west-3"],
            createDate=datetime.now(timezone.utc).isoformat(),
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            createdBy="T0012AB",
            lastUpdatedBy="T0012AB",
        )
        for i in range(5)
    ]

    return products_domain_query_service_mock


@pytest.fixture
def mocked_amis_domain_query_service() -> amis_domain_query_service.AMIsDomainQueryService:
    amis_domain_query_service_mock = unittest.mock.create_autospec(
        spec=amis_domain_query_service.AMIsDomainQueryService
    )
    amis_domain_query_service_mock.get_amis.return_value = [
        ami.Ami(
            projectId="proj-12345",
            amiId=f"ami-{str(i)}",
            amiName="Test name",
            amiDescription="Test description",
            createDate=datetime.now(timezone.utc).isoformat(),
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        )
        for i in range(5)
    ]
    amis_domain_query_service_mock.get_used_ami_list.return_value = [
        "ami-1",
        "ami-2",
        "ami-3",
        "ami-4",
        "ami-5",
    ]

    return amis_domain_query_service_mock


@pytest.fixture
def mocked_versions_domain_query_service():
    versions_domain_query_service_mock = unittest.mock.create_autospec(
        spec=versions_domain_query_service.VersionsDomainQueryService
    )
    versions_domain_query_service_mock.get_latest_version_name.return_value = "4.2.3-rc.1"
    versions_domain_query_service_mock.get_product_version.return_value = (
        version_summary.VersionSummary(
            versionId=TEST_VERSION_ID,
            name="1.0.0",
            description="Test Description",
            versionType=version.VersionType.Released.text,
            stages=[version.VersionStage.DEV],
            status=version_summary.VersionSummaryStatus.Created,
            recommendedVersion=True,
            lastUpdate="2020-01-01",
            lastUpdatedBy="T0011AA",
            restoredFromVersionName="1.0.0",
            originalAmiId="ami-123",
        ),
        [
            version.Version(
                projectId="proj-123",
                productId=TEST_PRODUCT_ID,
                technologyId="t-123",
                versionId=TEST_VERSION_ID,
                versionName="1.0.0",
                versionDescription="Test Description",
                versionType=version.VersionType.Released.text,
                awsAccountId="001234567890",
                stage=version.VersionStage.DEV,
                region="us-east-1",
                originalAmiId="ami-123",
                status=version.VersionStatus.Created,
                scPortfolioId="port-123",
                isRecommendedVersion=True,
                createDate="2000-01-01",
                lastUpdateDate="2020-01-01",
                createdBy="T0011AA",
                lastUpdatedBy="T0011AA",
                restoredFromVersionName="1.0.0",
            )
        ],
        "my product template",
    )
    versions_domain_query_service_mock.get_versions_ready_for_provisioning.return_value = [
        version.Version(
            projectId="proj-123",
            productId=TEST_PRODUCT_ID,
            technologyId="t-123",
            versionId=TEST_VERSION_ID,
            versionName="1.0.0",
            versionDescription="Test Description",
            versionType=version.VersionType.Released.text,
            awsAccountId="001234567890",
            stage=version.VersionStage.DEV,
            region="us-east-1",
            originalAmiId="ami-123",
            status=version.VersionStatus.Created,
            scPortfolioId="port-123",
            scProductId=TEST_PRODUCT_ID,
            scProvisioningArtifactId="artifact-123",
            isRecommendedVersion=True,
            createDate="2000-01-01",
            lastUpdateDate="2020-01-01",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            restoredFromVersionName="1.0.0",
            copiedAmiId="ami-1",
            accountId="001234567890",
        )
    ]
    versions_domain_query_service_mock.get_enriched_versions_ready_for_provisioning.return_value = [
        {
            "projectId": "proj-123",
            "productId": TEST_PRODUCT_ID,
            "technologyId": "t-123",
            "versionId": TEST_VERSION_ID,
            "versionName": "1.0.0",
            "versionDescription": "Test Description",
            "versionType": version.VersionType.Released.text,
            "awsAccountId": "001234567890",
            "stage": version.VersionStage.DEV,
            "region": "us-east-1",
            "originalAmiId": "ami-123",
            "status": version.VersionStatus.Created,
            "scPortfolioId": "port-123",
            "scProductId": TEST_PRODUCT_ID,
            "scProvisioningArtifactId": "artifact-123",
            "isRecommendedVersion": True,
            "createDate": "2000-01-01",
            "lastUpdateDate": "2020-01-01",
            "createdBy": "T0011AA",
            "lastUpdatedBy": "T0011AA",
            "restoredFromVersionName": "1.0.0",
            "copiedAmiId": "ami-1",
            "accountId": "001234567890",
            "amiId": "ami-1",
        }
    ]
    versions_domain_query_service_mock.get_version_distribution.return_value = {
        "projectId": "proj-123",
        "productId": TEST_PRODUCT_ID,
        "technologyId": "t-123",
        "versionId": TEST_VERSION_ID,
        "versionName": "1.0.0",
        "versionDescription": "Test Description",
        "versionType": version.VersionType.Released.text,
        "awsAccountId": "001234567890",
        "stage": version.VersionStage.DEV,
        "region": "us-east-1",
        "originalAmiId": "ami-123",
        "status": version.VersionStatus.Created,
        "scPortfolioId": "port-123",
        "scProductId": TEST_PRODUCT_ID,
        "scProvisioningArtifactId": "artifact-123",
        "isRecommendedVersion": True,
        "createDate": "2000-01-01",
        "lastUpdateDate": "2020-01-01",
        "createdBy": "T0011AA",
        "lastUpdatedBy": "T0011AA",
        "restoredFromVersionName": "1.0.0",
        "copiedAmiId": "ami-1",
        "accountId": "001234567890",
        "amiId": "ami-1",
    }
    versions_domain_query_service_mock.get_latest_major_version_summaries.return_value = [
        version_summary.VersionSummary(
            versionId=TEST_VERSION_ID,
            name="1.0.0",
            description="Test Description",
            versionType=version.VersionType.Released.text,
            stages=[
                version.VersionStage.DEV,
                version.VersionStage.QA,
                version.VersionStage.PROD,
            ],
            status=version_summary.VersionSummaryStatus.Created,
            recommendedVersion=True,
            lastUpdate="2020-01-01",
            lastUpdatedBy="T0011AA",
        ),
        version_summary.VersionSummary(
            versionId=TEST_VERSION_ID,
            name="2.0.0-rc1",
            description="Test Description",
            versionType=version.VersionType.ReleaseCandidate.text,
            stages=[version.VersionStage.DEV],
            status=version_summary.VersionSummaryStatus.Created,
            recommendedVersion=False,
            lastUpdate="2020-01-01",
            lastUpdatedBy="T0011AA",
        ),
    ]

    return versions_domain_query_service_mock


@pytest.fixture
def mocked_versions_query_service() -> versions_query_service.VersionsQueryService:
    versions_query_service_mock = unittest.mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    versions_query_service_mock.get_product_version_distributions.return_value = (
        [
            version.Version(
                projectId="proj-123",
                productId=TEST_PRODUCT_ID,
                technologyId="t-123",
                versionId=TEST_VERSION_ID,
                versionName="1.0.0",
                versionDescription="Test Description",
                versionType=version.VersionType.Released.text,
                awsAccountId=f"{i}",
                stage=version.VersionStage.DEV,
                region="us-east-1",
                originalAmiId="ami-123",
                status=version.VersionStatus.Created,
                scPortfolioId="port-123",
                isRecommendedVersion=True,
                createDate="2000-01-01",
                lastUpdateDate="2020-01-01",
                createdBy="T0011AA",
                lastUpdatedBy="T0011AA",
                restoredFromVersionName="1.0.0",
                copiedAmiId="ami-1",
            )
            for i in range(1, 4)
        ],
    )

    return versions_query_service_mock


@pytest.fixture
def mocked_templates_domain_query_service() -> template_domain_query_service.TemplateDomainQueryService:
    template_domain_qry_srv_mock = unittest.mock.create_autospec(
        template_domain_query_service.TemplateDomainQueryService
    )
    template_domain_qry_srv_mock.get_latest_draft_template.return_value = "Latest product template"
    return template_domain_qry_srv_mock


@pytest.fixture
def mocked_create_product_cmd_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_create_version_cmd_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_validate_version_cmd_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_update_version_cmd_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_retry_version_cmd_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_promote_version_cmd_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_archive_product_cmd_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_restore_version_cmd_handler():
    mocked_cmd_handler = unittest.mock.MagicMock()
    mocked_cmd_handler.return_value = "2.4.0-rc.1"
    return mocked_cmd_handler


@pytest.fixture
def mocked_retire_version_cmd_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_set_recommended_version_cmd_handler():
    return unittest.mock.MagicMock()


@pytest.fixture
def mocked_dependencies(
    mocked_versions_domain_query_service,
    mocked_versions_query_service,
    mocked_amis_domain_query_service,
    mocked_products_domain_query_service,
    mocked_create_product_cmd_handler,
    mocked_create_version_cmd_handler,
    mocked_validate_version_cmd_handler,
    mocked_update_version_cmd_handler,
    mocked_portfolios_domain_query_service,
    mocked_retry_version_cmd_handler,
    mocked_promote_version_cmd_handler,
    mocked_restore_version_cmd_handler,
    mocked_retire_version_cmd_handler,
    mocked_archive_product_cmd_handler,
    mocked_set_recommended_version_cmd_handler,
    mocked_templates_domain_query_service,
) -> bootstrapper.Dependencies:
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=unittest.mock.MagicMock(),
        )
        .register_handler(
            create_product_command.CreateProductCommand,
            mocked_create_product_cmd_handler,
        )
        .register_handler(
            create_version_command.CreateVersionCommand,
            mocked_create_version_cmd_handler,
        )
        .register_handler(
            validate_version_command.ValidateVersionCommand,
            mocked_validate_version_cmd_handler,
        )
        .register_handler(
            update_version_command.UpdateVersionCommand,
            mocked_update_version_cmd_handler,
        )
        .register_handler(
            retry_version_command.RetryVersionCommand,
            mocked_retry_version_cmd_handler,
        )
        .register_handler(
            promote_version_command.PromoteVersionCommand,
            mocked_promote_version_cmd_handler,
        )
        .register_handler(
            restore_version_command.RestoreVersionCommand,
            mocked_restore_version_cmd_handler,
        )
        .register_handler(
            retire_version_command.RetireVersionCommand,
            mocked_retire_version_cmd_handler,
        )
        .register_handler(
            archive_product_command.ArchiveProductCommand,
            mocked_archive_product_cmd_handler,
        )
        .register_handler(
            set_recommended_version_command.SetRecommendedVersionCommand,
            mocked_set_recommended_version_cmd_handler,
        ),
        products_domain_qry_srv=mocked_products_domain_query_service,
        amis_domain_qry_srv=mocked_amis_domain_query_service,
        versions_domain_qry_srv=mocked_versions_domain_query_service,
        portfolios_domain_qry_srv=mocked_portfolios_domain_query_service,
        version_qry_srv=mocked_versions_query_service,
        template_domain_qry_srv=mocked_templates_domain_query_service,
    )


@mock.patch(
    "app.publishing.domain.value_objects.product_id_value_object.random.choice",
    lambda chars: "1",
)
def test_create_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_product_cmd_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    request = api_model.CreateProductRequest(
        productName="fakeProductName",
        productType="Workbench",
        productDescription="fakeProductDescription",
        technologyId="fakeTechnologyId",
        technologyName="Test technology",
    )

    project_id = "proj-12345"
    minimal_event = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/products", "POST")

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_create_product_cmd_handler.assert_called_once_with(
        create_product_command.CreateProductCommand(
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-11111111"),
            productName=product_name_value_object.from_str("fakeProductName"),
            productType=product_type_value_object.from_str("Workbench"),
            productDescription=product_description_value_object.from_str("fakeProductDescription"),
            technologyId=tech_id_value_object.from_str("fakeTechnologyId"),
            technologyName=tech_name_value_object.from_str("Test technology"),
            userId=user_id_value_object.from_str("T00123122"),
        )
    )


def test_archive_product(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_archive_product_cmd_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    product_id = "prod-12345"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/products/{product_id}", "DELETE")

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_archive_product_cmd_handler.assert_called_once_with(
        archive_product_command.ArchiveProductCommand(
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-12345"),
            archivedBy=user_id_value_object.from_str("T00123122"),
        )
    )


@pytest.mark.parametrize(
    "major_version_name",
    (None, 1),
)
def test_create_product_version(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_version_cmd_handler,
    major_version_name,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    request = api_model.CreateProductVersionRequest(
        amiId="fakeAMIId",
        majorVersionName=major_version_name,
        productVersionDescription="fakeProductVersionDescription",
        versionReleaseType="MINOR",
        versionTemplateDefinition="New template definition",
    )

    project_id = "proj-12345"
    product_id = "prod-12345"
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()),
        f"/projects/{project_id}/products/{product_id}/versions",
        "POST",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_create_version_cmd_handler.assert_called_once_with(
        create_version_command.CreateVersionCommand(
            amiId=ami_id_value_object.from_str("fakeAMIId"),
            majorVersionName=(
                major_version_name_value_object.from_int(major_version_name) if major_version_name else None
            ),
            versionReleaseType=version_release_type_value_object.from_str("MINOR"),
            versionDescription=version_description_value_object.from_str("fakeProductVersionDescription"),
            versionTemplateDefinition=version_template_definition_value_object.from_str("New template definition"),
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-12345"),
            createdBy=user_id_value_object.from_str("T00123122"),
        )
    )


def test_validate_product_version(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_validate_version_cmd_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    request = api_model.ValidateProductVersionRequest(
        versionTemplateDefinition="fakeTemplate",
    )

    project_id = "proj-12345"
    product_id = "prod-12345"
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()),
        f"/projects/{project_id}/products/{product_id}/versions/validate",
        "POST",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_validate_version_cmd_handler.assert_called_once_with(
        validate_version_command.ValidateVersionCommand(
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-12345"),
            versionTemplateDefinition=version_template_definition_value_object.from_str("fakeTemplate"),
        )
    )


def test_update_product_version(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_update_version_cmd_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    request = api_model.UpdateProductVersionRequest(
        amiId="fakeAMIId",
        productVersionDescription="fakeProductVersionDescription",
        versionTemplateDefinition="Updated template definition",
    )

    project_id = "proj-12345"
    product_id = "prod-12345"
    version_id = "ver-12345"
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()),
        f"/projects/{project_id}/products/{product_id}/versions/{version_id}",
        "PUT",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_update_version_cmd_handler.assert_called_once_with(
        update_version_command.UpdateVersionCommand(
            amiId=ami_id_value_object.from_str("fakeAMIId"),
            versionDescription=version_description_value_object.from_str("fakeProductVersionDescription"),
            versionTemplateDefinition=version_template_definition_value_object.from_str("Updated template definition"),
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-12345"),
            versionId=version_id_value_object.from_str("ver-12345"),
            lastUpdatedBy=user_id_value_object.from_str("T00123122"),
        )
    )


def test_retry_product_version(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_retry_version_cmd_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    request = api_model.RetryProductVersionRequest(awsAccountIds=["123456789012", "123456789013"])

    project_id = "proj-12345"
    product_id = "prod-12345"
    version_id = "ver-12345"
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()),
        f"/projects/{project_id}/products/{product_id}/versions/{version_id}",
        "PATCH",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_retry_version_cmd_handler.assert_called_once_with(
        retry_version_command.RetryVersionCommand(
            projectId=project_id_value_object.from_str(project_id),
            productId=product_id_value_object.from_str("prod-12345"),
            versionId=version_id_value_object.from_str("ver-12345"),
            awsAccountIds=[
                aws_account_id_value_object.from_str("123456789012"),
                aws_account_id_value_object.from_str("123456789013"),
            ],
            lastUpdatedBy=user_id_value_object.from_str("T00123122"),
        )
    )


def test_promote_product_version(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_promote_version_cmd_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    request = api_model.PromoteProductVersionRequest(stage="QA")

    project_id = "proj-12345"
    product_id = "prod-12345"
    version_id = "ver-12345"
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()),
        f"/projects/{project_id}/products/{product_id}/versions/{version_id}",
        "POST",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_promote_version_cmd_handler.assert_called_once_with(
        promote_version_command.PromoteVersionCommand(
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-12345"),
            versionId=version_id_value_object.from_str("ver-12345"),
            createdBy=user_id_value_object.from_str("T00123122"),
            userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.Admin)],
            stage=stage_value_object.from_str("QA"),
        )
    )


def test_restore_product_version(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_restore_version_cmd_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    product_id = "prod-12345"
    version_id = "ver-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/{product_id}/versions/{version_id}/restore",
        "POST",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_restore_version_cmd_handler.assert_called_once_with(
        restore_version_command.RestoreVersionCommand(
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-12345"),
            versionId=version_id_value_object.from_str("ver-12345"),
            restoredBy=user_id_value_object.from_str("T00123122"),
        )
    )
    response = api_model.RestoreProductVersionResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.restoredVersionName).is_equal_to("2.4.0-rc.1")


def test_get_products(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/products", "GET")

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProductsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.products).is_not_none()
    assertpy.assert_that(len(response.products)).is_equal_to(5)


def test_can_get_a_single_product_for_a_program(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    project_id = "proj-12345"
    product_id = "prod-54321"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/products/{product_id}", "GET")
    sample_prod = product.Product(
        projectId="proj-12345",
        productId="prod-54321",
        technologyId="tech-1",
        technologyName="Test technology",
        status="CREATED",
        productName="Product A",
        productType=product.ProductType.Workbench,
        createDate=datetime.now(timezone.utc).isoformat(),
        lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        createdBy="T0012AB",
        lastUpdatedBy="T0012AB",
    )
    handler.dependencies = mocked_dependencies

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    try:
        response = api_model.GetProductResponse.model_validate(json.loads(result["body"]))
        assertpy.assert_that(response.product.technologyId).is_equal_to(sample_prod.technologyId)
        assertpy.assert_that(response.product.productId).is_equal_to(sample_prod.productId)
        assertpy.assert_that(response.product.versions).is_length(1)
    except pydantic.ValidationError:
        assertpy.assert_that(False).is_true()


def test_get_amis(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12395"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/amis", "GET")

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetAmisResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.amis).is_not_none()
    assertpy.assert_that(len(response.amis)).is_equal_to(5)


def test_get_available_product_versions(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-123"
    product_id = "prod-123"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/available-products/{product_id}/versions",
        "GET",
        {"region": "us-east-1", "stage": "DEV"},
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetAvailableProductVersionsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.availableProductVersions).is_not_none()
    assertpy.assert_that(len(response.availableProductVersions)).is_equal_to(1)


@freeze_time("2023-07-24")
def test_get_product_version_returns_summary_distributions_and_template(
    lambda_context, authenticated_event, mocked_dependencies
):
    # ARRANGE

    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    api_request = authenticated_event(
        None,
        f"/projects/prog-123/products/{TEST_PRODUCT_ID}/versions/{TEST_VERSION_ID}",
        "GET",
    )

    # ACT
    result = handler.handler(api_request, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result.get("statusCode")).is_equal_to(200)
    body = json.loads(result.get("body"))
    prd = api_model.Product.model_validate(body["product"])
    assertpy.assert_that(prd).is_equal_to(
        api_model.Product(
            projectId="proj-12345",
            productId="prod-54321",
            technologyId="tech-1",
            technologyName="Test technology",
            status="CREATED",
            productName="Product A",
            productType=product.ProductType.Workbench,
            createDate="2023-07-24T00:00:00+00:00",
            lastUpdateDate="2023-07-24T00:00:00+00:00",
            createdBy="T0012AB",
            lastUpdatedBy="T0012AB",
        ),
    )
    summary = api_model.VersionSummary.model_validate(body["version"])
    assertpy.assert_that(summary).is_equal_to(
        api_model.VersionSummary(
            versionId=TEST_VERSION_ID,
            name="1.0.0",
            description="Test Description",
            versionType=version.VersionType.Released.text,
            stages=["DEV"],
            status="CREATED",
            recommendedVersion=True,
            lastUpdate="2020-01-01",
            lastUpdatedBy="T0011AA",
            restoredFromVersionName="1.0.0",
            originalAmiId="ami-123",
        )
    )
    distributions = [api_model.VersionDistribution.model_validate(dist) for dist in body["distributions"]]
    assertpy.assert_that(distributions).is_equal_to(
        [
            api_model.VersionDistribution(
                projectId="proj-123",
                productId=TEST_PRODUCT_ID,
                versionId=TEST_VERSION_ID,
                versionType=version.VersionType.Released.text,
                awsAccountId="001234567890",
                copiedAmiId=None,
                originalAmiId="ami-123",
                region="us-east-1",
                stage="DEV",
                status="CREATED",
                lastUpdateDate="2020-01-01",
                restoredFromVersionName="1.0.0",
            )
        ]
    )
    draft_template = body["draft_template"]
    assertpy.assert_that(draft_template).is_equal_to("my product template")


def test_retire_product_version(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_retire_version_cmd_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    request = api_model.RetireProductVersionRequest(retireReason="Test reason")

    project_id = "proj-12345"
    product_id = "prod-12345"
    version_id = "ver-12345"
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()),
        f"/projects/{project_id}/products/{product_id}/versions/{version_id}",
        "DELETE",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_retire_version_cmd_handler.assert_called_once_with(
        retire_version_command.RetireVersionCommand(
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-12345"),
            versionId=version_id_value_object.from_str("ver-12345"),
            retiredBy=user_id_value_object.from_str("T00123122"),
            userRoles=[user_role_value_object.from_str(VirtualWorkbenchRoles.Admin)],
            retireReason="Test reason",
        )
    )


def test_get_available_products(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/available-products",
        "GET",
        {"productType": "Workbench"},
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetAvailableProductsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.availableProducts).is_not_none()
    assertpy.assert_that(len(response.availableProducts)).is_equal_to(5)


def test_set_recommended_product_version(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_set_recommended_version_cmd_handler,
):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    request = api_model.SetRecommendedVersionResponse()

    project_id = "proj-12345"
    product_id = "prod-12345"
    version_id = "ver-12345"
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()),
        f"/projects/{project_id}/products/{product_id}/versions/{version_id}/set-recommended",
        "PUT",
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mocked_set_recommended_version_cmd_handler.assert_called_once_with(
        set_recommended_version_command.SetRecommendedVersionCommand(
            projectId=project_id_value_object.from_str("proj-12345"),
            productId=product_id_value_object.from_str("prod-12345"),
            versionId=version_id_value_object.from_str("ver-12345"),
            userId=user_id_value_object.from_str("T00123122"),
        )
    )


def test_get_swagger_json(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    minimal_event = authenticated_event(None, "/_swagger", "GET", query_params={"format": "json"})

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)


@pytest.mark.parametrize("version_id", ["vers-12345", None])
def test_get_latest_template(version_id, lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    project_id = "proj-12345"
    product_id = "prod-12345"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/products/{product_id}/latest-template",
        "GET",
        {"versionId": version_id} if version_id else None,
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetLatestTemplateResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.template).is_equal_to("Latest product template")


def test_get_available_product_versions_internal(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    product_id = "prod-123"
    minimal_event = authenticated_event(
        None,
        f"/internal/available-products/{product_id}/versions",
        "GET",
        {},
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetAvailableProductVersionsInternalResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.availableProductVersions).is_not_none()
    assertpy.assert_that(len(response.availableProductVersions)).is_equal_to(1)


def test_get_available_product_version_internal(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    product_id = "prod-123"
    version_id = "vers-123"
    minimal_event = authenticated_event(
        None,
        f"/internal/available-products/{product_id}/versions/{version_id}",
        "GET",
        {},
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetAvailableProductVersionsInternalResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.availableProductVersions).is_not_none()
    assertpy.assert_that(len(response.availableProductVersions)).is_equal_to(1)


def test_get_product_version_distribution_internal(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    product_id = "prod-123"
    version_id = "vers-123"
    aws_account_id = "123456789012"
    minimal_event = authenticated_event(
        None,
        f"/internal/products/{product_id}/versions/{version_id}",
        "GET",
        {"awsAccountId": aws_account_id},
    )

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProductVersionInternalResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.version).is_not_none()
    assertpy.assert_that(response.version).is_equal_to(
        api_model.AvailableVersionDistributionEnriched.model_validate(
            {
                "projectId": "proj-123",
                "productId": TEST_PRODUCT_ID,
                "technologyId": "t-123",
                "versionId": TEST_VERSION_ID,
                "versionName": "1.0.0",
                "versionDescription": "Test Description",
                "versionType": version.VersionType.Released.text,
                "awsAccountId": "001234567890",
                "stage": version.VersionStage.DEV,
                "region": "us-east-1",
                "originalAmiId": "ami-123",
                "status": version.VersionStatus.Created,
                "scPortfolioId": "port-123",
                "scProductId": TEST_PRODUCT_ID,
                "scProvisioningArtifactId": "artifact-123",
                "isRecommendedVersion": True,
                "createDate": "2000-01-01",
                "lastUpdateDate": "2020-01-01",
                "createdBy": "T0011AA",
                "lastUpdatedBy": "T0011AA",
                "restoredFromVersionName": "1.0.0",
                "copiedAmiId": "ami-1",
                "accountId": "001234567890",
                "amiId": "ami-1",
            }
        )
    )


def test_get_latest_major_versions(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE

    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    api_request = authenticated_event(
        None,
        f"/projects/proj-123/products/{TEST_PRODUCT_ID}/latest-major-versions",
        "GET",
    )

    # ACT
    result = handler.handler(api_request, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result.get("statusCode")).is_equal_to(200)
    body = json.loads(result.get("body"))
    sumaries = [api_model.VersionSummary.model_validate(summary) for summary in body["versions"]]
    assertpy.assert_that(sumaries).is_equal_to(
        [
            api_model.VersionSummary(
                versionId=TEST_VERSION_ID,
                name="1.0.0",
                description="Test Description",
                versionType=version.VersionType.Released.text,
                stages=["DEV", "QA", "PROD"],
                status="CREATED",
                recommendedVersion=True,
                lastUpdate="2020-01-01",
                lastUpdatedBy="T0011AA",
            ),
            api_model.VersionSummary(
                versionId=TEST_VERSION_ID,
                name="2.0.0-rc1",
                description="Test Description",
                versionType=version.VersionType.ReleaseCandidate.text,
                stages=["DEV"],
                status="CREATED",
                recommendedVersion=False,
                lastUpdate="2020-01-01",
                lastUpdatedBy="T0011AA",
            ),
        ]
    )


def test_get_published_amis_internal(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.publishing.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    minimal_event = authenticated_event(None, "/internal/published-amis", "GET")

    # ACT
    result = handler.handler(minimal_event, lambda_context)

    # ASSERT
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetPublishedAmisResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.amis).is_length(5)
