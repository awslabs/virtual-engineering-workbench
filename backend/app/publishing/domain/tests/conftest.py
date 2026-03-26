from datetime import datetime, timezone
from unittest import mock

import pytest
from freezegun import freeze_time

from app.publishing.domain.model import portfolio, product, shared_ami, version
from app.publishing.domain.ports import (
    amis_query_service,
    products_query_service,
    projects_query_service,
)
from app.publishing.domain.read_models import ami
from app.shared.adapters.unit_of_work_v2 import unit_of_work

TEST_PROJECT_ID = "proj-12345"


@pytest.fixture()
def mock_unit_of_work(
    mock_version_repo,
    mock_shared_ami_repo,
    mock_products_repo,
    mock_portfolio_repo,
    mock_amis_repo,
):
    repo_dict = {
        shared_ami.SharedAmi: mock_shared_ami_repo,
        portfolio.Portfolio: mock_portfolio_repo,
        version.Version: mock_version_repo,
        product.Product: mock_products_repo,
        ami.Ami: mock_amis_repo,
    }

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk_param, entity_param: repo_dict.get(entity_param)
    return uow_mock


@pytest.fixture
def mock_portfolio_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)


@pytest.fixture
def mock_version_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)


@pytest.fixture
def mock_shared_ami_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)


@pytest.fixture
def mock_products_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)


@pytest.fixture
def mock_amis_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)


@pytest.fixture
def generic_repo_mock():
    return mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)


@pytest.fixture
def uow_mock(generic_repo_mock):
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork, instance=True)
    uow_mock.get_repository.return_value = generic_repo_mock
    return uow_mock


@pytest.fixture
def projects_query_service_mock():
    qry_srv = mock.create_autospec(spec=projects_query_service.ProjectsQueryService)
    return qry_srv


@pytest.fixture
def product_query_service_mock():
    qry_srv = mock.create_autospec(spec=products_query_service.ProductsQueryService)
    return qry_srv


@pytest.fixture()
def get_sample_product():
    def _get_sample_product(
        product_id="prod-1",
        available_stages=[product.ProductStage.DEV],
    ):
        return product.Product(
            projectId="proj-12345",
            productId=product_id,
            technologyId="tech-12345",
            technologyName="Test technology",
            status=product.ProductStatus.Created,
            productName="Product Name",
            productType=product.ProductType.Workbench,
            availableStages=available_stages,
            availableRegions=["us-east-1"],
            createDate="2023-07-07T00:00:00+00:00",
            lastUpdateDate="2023-07-07T00:00:00+00:00",
            createdBy="T0012AB",
            lastUpdatedBy="T0012AB",
        )

    return _get_sample_product


@pytest.fixture
def get_test_ami():
    def _get_test_ami():
        return ami.Ami(
            projectId=TEST_PROJECT_ID,
            amiId="ami-0001",
            amiName="AMI name",
            amiDescription="AMI description",
            createDate=datetime.now(timezone.utc).isoformat(),
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        )

    return _get_test_ami


@pytest.fixture()
def mock_amis_query_service(get_test_ami):
    qry_srv = mock.create_autospec(amis_query_service.AMIsQueryService)
    qry_srv.get_ami.return_value = get_test_ami()
    qry_srv.get_amis.return_value = [
        get_test_ami(),
        get_test_ami(),
    ]
    return qry_srv


@pytest.fixture
def mock_amis_qry_srv():
    from app.publishing.domain.read_models import ami, component_version_detail

    mock_srv = mock.Mock(spec=amis_query_service.AMIsQueryService)
    mock_ami = ami.Ami(
        projectId=TEST_PROJECT_ID,
        amiId="ami-12345678",
        amiName="Test Ami",
        amiDescription="Test Ami Description",
        componentVersionDetails=[
            component_version_detail.ComponentVersionDetail(
                componentName="VS Code",
                componentVersionType=(component_version_detail.ComponentVersionEntryType.Main),
                softwareVendor="Microsoft",
                softwareVersion="1.87.0",
            )
        ],
        osVersion="Ubuntu 24.04",
        platform="Linux",
        architecture="x86_64",
        integrations=["GitHub"],
        createDate="2024-03-06T00:00:00+00:00",
        lastUpdateDate="2024-03-06T00:00:00+00:00",
    )
    mock_srv.get_ami.return_value = mock_ami
    return mock_srv


@pytest.fixture
def mock_message_bus():
    from app.shared.adapters.message_bus import message_bus

    return mock.Mock(spec=message_bus.MessageBus)


@pytest.fixture
def mock_command_bus():
    from app.shared.adapters.message_bus import command_bus

    return mock.Mock(spec=command_bus.CommandBus)


@pytest.fixture
def mock_portfolios_qry_srv():
    from app.publishing.domain.model import portfolio
    from app.publishing.domain.ports import portfolios_query_service

    mock_srv = mock.Mock(spec=portfolios_query_service.PortfoliosQueryService)
    current_time = datetime.now(timezone.utc).isoformat()
    mock_portfolio = portfolio.Portfolio(
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
    mock_srv.get_portfolios_by_tech_and_stage.return_value = [mock_portfolio]
    return mock_srv


@pytest.fixture
def mock_versions_qry_srv():
    from app.publishing.domain.ports import versions_query_service

    mock_srv = mock.Mock(spec=versions_query_service.VersionsQueryService)
    mock_srv.get_latest_version_name_and_id.return_value = ("1.0.0", "vers-12345")
    mock_srv.get_distinct_number_of_versions.return_value = 1

    mock_version = mock.Mock()
    mock_version.draftTemplateLocation = "template/path/template.yaml"
    mock_srv.get_product_version_distributions.return_value = [mock_version]

    return mock_srv


@pytest.fixture
def mock_template_domain_qry_srv():
    from app.publishing.domain.query_services import template_domain_query_service

    mock_srv = mock.Mock(spec=template_domain_query_service.TemplateDomainQueryService)
    mock_srv.get_default_template_file_name.return_value = "draft_workbench.yml"
    return mock_srv


@pytest.fixture
def mock_param_service():
    from app.shared.api import parameter_service

    mock_srv = mock.Mock(spec=parameter_service.ParameterService)
    mock_srv.get_parameter_value.return_value = "10"
    return mock_srv


@pytest.fixture
def mock_stack_srv():
    from app.publishing.domain.model import version
    from app.publishing.domain.ports import iac_service

    mock_srv = mock.Mock(spec=iac_service.IACService)
    mock_srv.validate_template.return_value = (
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
    return mock_srv


@pytest.fixture
def mock_file_service():
    from app.publishing.domain.ports import template_service

    mock_srv = mock.Mock(spec=template_service.TemplateService)
    mock_srv.get_template.return_value = "template content from latest version"
    mock_srv.put_template.return_value = None
    return mock_srv


@pytest.fixture
def mock_product_entity():
    return product.Product(
        projectId="project-123",
        productId="product-456",
        productName="Test Product",
        productType=product.ProductType.Workbench,
        status=product.ProductStatus.Created,
        technologyId="tech-789",
        technologyName="Test Technology",
        createDate=datetime.now(timezone.utc).isoformat(),
        lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        createdBy="user-123",
        lastUpdatedBy="user-123",
    )


@pytest.fixture
def mock_container_product_entity():
    return product.Product(
        projectId="project-123",
        productId="product-456",
        productName="Test Container Product",
        productType=product.ProductType.Container,
        status=product.ProductStatus.Created,
        technologyId="tech-789",
        technologyName="Test Technology",
        createDate=datetime.now(timezone.utc).isoformat(),
        lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        createdBy="user-123",
        lastUpdatedBy="user-123",
    )


@pytest.fixture
def mock_logger():
    return mock.Mock()


@pytest.fixture(autouse=True)
def frozen_time():
    with freeze_time("2025-01-01 12:00:00"):
        yield
