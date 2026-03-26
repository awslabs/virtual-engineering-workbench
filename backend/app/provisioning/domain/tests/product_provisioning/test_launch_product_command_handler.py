from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import launch
from app.provisioning.domain.commands.product_provisioning import launch_product_command
from app.provisioning.domain.events.product_provisioning import product_launch_started
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import (
    additional_configuration,
    product_status,
    provisioned_product,
    provisioning_parameter,
)
from app.provisioning.domain.ports import products_query_service, versions_query_service
from app.provisioning.domain.read_models import product, version
from app.provisioning.domain.value_objects import (
    additional_configurations_value_object,
    deployment_option_value_object,
    ip_address_value_object,
    product_id_value_object,
    product_version_id_value_object,
    project_id_value_object,
    provisioned_compound_product_id_value_object,
    provisioned_product_id_value_object,
    provisioned_product_stage_value_object,
    provisioning_parameters_value_object,
    region_value_object,
    user_domains_value_object,
    user_id_value_object,
)


@pytest.fixture()
def mock_products_query_service(mock_product):
    qs_mock = mock.create_autospec(spec=products_query_service.ProductsQueryService)
    qs_mock.get_product.return_value = mock_product
    return qs_mock


@pytest.fixture()
def mock_versions_query_service():
    qs_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    qs_mock.get_product_version_distributions.return_value = [
        get_mocked_product_version(
            region="us-east-1",
            stage=version.VersionStage.DEV,
            sc_product_id="sc-prod-123",
            sc_provisioning_artifact_id="sc-pa-123",
            aws_account_id="001234567890",
        )
    ]
    return qs_mock


@pytest.fixture()
def mock_product():
    return product.Product(
        projectId="proj-123",
        productId="prod-123",
        technologyId="tech-123",
        technologyName="Test Tech",
        productName="Pied Piper",
        productType=product.ProductType.VirtualTarget,
        productDescription="Compression",
        availableStages=[product.ProductStage.DEV],
        availableRegions=["us-east-1", "eu-west-3"],
        pausedStages=[product.ProductStage.QA],
        pausedRegions=["eu-west-3"],
        lastUpdateDate="2023-12-05",
    )


@pytest.fixture()
def mock_product_container():
    return product.Product(
        projectId="proj-123",
        productId="prod-123",
        technologyId="tech-123",
        technologyName="Test Tech",
        productName="Pied Piper",
        productType=product.ProductType.Container,
        productDescription="Compression",
        availableStages=[product.ProductStage.DEV],
        availableRegions=["us-east-1", "eu-west-3"],
        pausedStages=[product.ProductStage.QA],
        pausedRegions=["eu-west-3"],
        lastUpdateDate="2023-12-05",
    )


def get_mocked_product_version(
    region: str = "us-east-1",
    stage: version.VersionStage = version.VersionStage.DEV,
    sc_product_id: str = "sc-prod-123",
    sc_provisioning_artifact_id: str = "sc-pa-123",
    aws_account_id: str = "001234567890",
    is_container: bool = False,
):
    return version.Version(
        projectId="proj-123",
        productId="prod-123",
        technologyId="tech-123",
        versionId="ver-123",
        versionName="v1.0.0",
        versionDescription="Initial release",
        awsAccountId=aws_account_id,
        accountId="acc-123",
        stage=stage,
        region=region,
        amiId="ami-123" if not is_container else None,
        scProductId=sc_product_id,
        scProvisioningArtifactId=sc_provisioning_artifact_id,
        isRecommendedVersion=True,
        parameters=[
            version.VersionParameter(
                parameterKey="SomeParam",
                defaultValue="some-default",
                parameterType="String",
            ),
            version.VersionParameter(
                parameterKey="SomeTechParam",
                defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                parameterType="AWS::SSM::Parameter::Value<String>",
            ),
            version.VersionParameter(
                parameterKey="Experimental",
                defaultValue="False",
                parameterType="String",
            ),
        ],
        lastUpdateDate="2023-12-05",
    )


@freeze_time("2023-12-05")
@mock.patch("random.randrange", return_value=12345)
def test_launch_product_stores_and_publishes_event_for_container(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_versions_query_service,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    get_test_version,
    mock_product_container,
    publishing_qry_svc_mock,
    mocked_projects_qs,
):
    # ARRANGE
    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [
                {
                    "key": "SomeParam",
                    "value": "some-test-param-value",
                },
                {
                    "key": "Experimental",
                    "value": "False",
                },
            ]
        ),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        provisioned_compound_product_id=provisioned_compound_product_id_value_object.from_string("cpp-123"),
        deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
    )
    mock_versions_query_service.get_product_version_distributions.return_value = [
        get_mocked_product_version(
            region="us-east-1",
            stage=version.VersionStage.DEV,
            sc_product_id="sc-prod-123",
            sc_provisioning_artifact_id="sc-pa-123",
            aws_account_id="001234567890",
            is_container=True,
        )
    ]
    mock_products_query_service.get_product.return_value = mock_product_container
    # ACT
    launch.handle(
        command=command,
        publisher=mock_publisher,
        products_qs=mock_products_query_service,
        versions_qs=mock_versions_query_service,
        logger=mock_logger,
        provisioned_products_qs=mock_provisioned_products_qs,
        uow=mock_unit_of_work,
        feature_toggles_srv=mock_be_feature_toggles_srv,
        experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
        projects_qs=mocked_projects_qs,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_started.ProductLaunchStarted(provisionedProductId="pp-123", userIpAddress="127.0.0.1")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.add.assert_called_once_with(
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName="prod-123-vers-123-T0011AA-12345",
            provisionedProductType=provisioned_product.ProvisionedProductType.Container,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Provisioning,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="v1.0.0",
            versionDescription="Initial release",
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId=None,
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(
                    key="SomeParam",
                    value="some-test-param-value",
                    parameterType="String",
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
                provisioning_parameter.ProvisioningParameter(key="Experimental", value="False", parameterType="String"),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            additionalConfigurations=[],
            experimental=False,
            userIpAddress="127.0.0.1",
            provisionedCompoundProductId="cpp-123",
            deploymentOption="MULTI_AZ",
        )
    )
    mock_products_query_service.get_product.assert_called_once_with(project_id="proj-123", product_id="prod-123")
    mock_versions_query_service.get_product_version_distributions.assert_called_once_with(
        product_id="prod-123",
        version_id="vers-123",
        region="us-east-1",
        stage=version.VersionStage.DEV,
    )


@freeze_time("2023-12-05")
def test_launch_product_stores_and_publishes_event(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_versions_query_service,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    mocked_projects_qs,
):
    # ARRANGE
    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [
                {
                    "key": "SomeParam",
                    "value": "some-test-param-value",
                },
                {
                    "key": "Experimental",
                    "value": "False",
                },
            ]
        ),
        additional_configurations=additional_configurations_value_object.from_list(
            [
                {
                    "type": additional_configuration.ProvisionedProductConfigurationTypeEnum.VVPLProvisionedProductConfiguration,
                    "parameters": [
                        {
                            "key": "conf_a",
                            "value": "a",
                        },
                        {
                            "key": "conf_b",
                            "value": "b",
                        },
                    ],
                }
            ]
        ),
        stage=provisioned_product_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
    )

    # ACT
    launch.handle(
        command=command,
        publisher=mock_publisher,
        products_qs=mock_products_query_service,
        versions_qs=mock_versions_query_service,
        logger=mock_logger,
        provisioned_products_qs=mock_provisioned_products_qs,
        uow=mock_unit_of_work,
        feature_toggles_srv=mock_be_feature_toggles_srv,
        experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
        projects_qs=mocked_projects_qs,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_started.ProductLaunchStarted(provisionedProductId="pp-123", userIpAddress="127.0.0.1")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.add.assert_called_once_with(
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Provisioning,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="v1.0.0",
            versionDescription="Initial release",
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(
                    key="SomeParam",
                    value="some-test-param-value",
                    parameterType="String",
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
                provisioning_parameter.ProvisioningParameter(key="Experimental", value="False", parameterType="String"),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            additionalConfigurations=[
                additional_configuration.AdditionalConfiguration(
                    type=additional_configuration.ProvisionedProductConfigurationTypeEnum.VVPLProvisionedProductConfiguration,
                    parameters=[
                        additional_configuration.AdditionalConfigurationParameter(key="conf_a", value="a"),
                        additional_configuration.AdditionalConfigurationParameter(key="conf_b", value="b"),
                    ],
                )
            ],
            experimental=False,
            userIpAddress="127.0.0.1",
            deploymentOption="MULTI_AZ",
        )
    )
    mock_products_query_service.get_product.assert_called_once_with(project_id="proj-123", product_id="prod-123")
    mock_versions_query_service.get_product_version_distributions.assert_called_once_with(
        product_id="prod-123",
        version_id="vers-123",
        region="us-east-1",
        stage=version.VersionStage.DEV,
    )


def test_launch_product_when_user_provides_ssm_param_should_raise(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_message_bus,
    mock_unit_of_work,
    mock_versions_query_service,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    mocked_projects_qs,
):
    # ARRANGE
    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [
                {
                    "key": "SomeTechParam",
                    "value": "/fake-ami-ssm-param",
                }
            ]
        ),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        launch.handle(
            command=command,
            publisher=mock_publisher,
            products_qs=mock_products_query_service,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
            uow=mock_unit_of_work,
            feature_toggles_srv=mock_be_feature_toggles_srv,
            experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
            projects_qs=mocked_projects_qs,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Technical parameters SomeTechParam cannot be overridden.")
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


def test_launch_virtual_target_when_provided_param_is_invalid_should_raise(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_message_bus,
    mock_unit_of_work,
    mock_versions_query_service,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    mocked_projects_qs,
):
    # ARRANGE
    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [
                {
                    "key": "SomeNonExistingParam",
                    "value": "value",
                }
            ]
        ),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        launch.handle(
            command=command,
            publisher=mock_publisher,
            products_qs=mock_products_query_service,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
            uow=mock_unit_of_work,
            feature_toggles_srv=mock_be_feature_toggles_srv,
            experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
            projects_qs=mocked_projects_qs,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Product does not accept these parameters: SomeNonExistingParam.")
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@pytest.mark.parametrize(
    "stage,limit",
    [
        pytest.param("dev", 5),
        pytest.param("qa", 6),
    ],
)
def test_launch_product_when_user_exceeds_product_limit_per_stage_and_region_should_raise(
    stage,
    limit,
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_unit_of_work,
    mock_versions_query_service,
    get_provisioned_product,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    mocked_projects_qs,
):
    # ARRANGE
    provisioned_products = []
    for i in range(limit):
        provisioned_products.append(get_provisioned_product(provisioned_product_id=f"pp-{i}"))
    mock_provisioned_products_qs.get_provisioned_products_by_user_id.return_value = provisioned_products

    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list([]),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str(stage),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        launch.handle(
            command=command,
            publisher=mock_publisher,
            products_qs=mock_products_query_service,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
            uow=mock_unit_of_work,
            feature_toggles_srv=mock_be_feature_toggles_srv,
            experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
            projects_qs=mocked_projects_qs,
        )

    assertpy.assert_that(str(e.value)).is_equal_to(
        "Number of allowed provisioned products per product type is reached. You must deprovision a product of the same type before provisioning a new product."
    )
    mock_provisioned_products_qs.get_provisioned_products_by_user_id.assert_called_once_with(
        exclude_status=[
            product_status.ProductStatus.Terminated,
            product_status.ProductStatus.Deprovisioning,
        ],
        project_id="proj-123",
        stage=provisioned_product.ProvisionedProductStage(stage.upper()),
        user_id="T0011AA",
        product_id="prod-123",
    )


def test_launch_experimental_product_when_user_exceeds_project_limit_should_raise(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_unit_of_work,
    mock_versions_query_service,
    get_provisioned_product,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    mocked_projects_qs,
):
    # ARRANGE
    provisioned_products = []
    # Limit per project is currently set to 20 in app/provisioning/domain/aggregates/product_provisioning_aggregate.py
    for i in range(20):
        provisioned_products.append(get_provisioned_product(provisioned_product_id=f"pp-{i}", experimental=True))
    mock_provisioned_products_qs.get_provisioned_products_by_project_id.return_value = provisioned_products

    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [
                provisioned_product.provisioning_parameter.ProvisioningParameter(
                    key="Experimental",
                    value="True",
                )
            ]
        ),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str("qa"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        launch.handle(
            command=command,
            publisher=mock_publisher,
            products_qs=mock_products_query_service,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
            uow=mock_unit_of_work,
            feature_toggles_srv=mock_be_feature_toggles_srv,
            experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
            projects_qs=mocked_projects_qs,
        )

    assertpy.assert_that(str(e.value)).is_equal_to(
        "The maximum amount of experimental provisioned products per program has been reached. Contact the program owner for assistance."
    )
    mock_provisioned_products_qs.get_provisioned_products_by_project_id.assert_called_once_with(
        project_id="proj-123",
        exclude_status=[
            product_status.ProductStatus.ProvisioningError,
            product_status.ProductStatus.InstanceError,
            product_status.ProductStatus.Terminated,
        ],
        experimental=True,
    )


def test_launch_experimental_product_when_not_qa_stage_should_raise(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_unit_of_work,
    mock_versions_query_service,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    mocked_projects_qs,
):
    # ARRANGE
    mock_provisioned_products_qs.get_provisioned_products_by_project_id.return_value = []

    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [
                provisioned_product.provisioning_parameter.ProvisioningParameter(
                    key="Experimental",
                    value="True",
                )
            ]
        ),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        launch.handle(
            command=command,
            publisher=mock_publisher,
            products_qs=mock_products_query_service,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
            uow=mock_unit_of_work,
            feature_toggles_srv=mock_be_feature_toggles_srv,
            experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
            projects_qs=mocked_projects_qs,
        )

    assertpy.assert_that(str(e.value)).is_equal_to("Experimental products can be provisioned only in QA stage.")


@freeze_time("2023-12-05")
def test_launch_experimental_product_should_succeed(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_versions_query_service,
    get_provisioned_product,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    mocked_projects_qs,
):
    # ARRANGE
    provisioned_products = []
    for i in range(2):
        provisioned_products.append(get_provisioned_product(provisioned_product_id=f"pp-{i}", experimental=True))
    mock_provisioned_products_qs.get_provisioned_products_by_project_id.return_value = provisioned_products

    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [
                provisioned_product.provisioning_parameter.ProvisioningParameter(
                    key="Experimental",
                    value="True",
                )
            ]
        ),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str("qa"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
    )

    # ACT
    launch.handle(
        command=command,
        publisher=mock_publisher,
        products_qs=mock_products_query_service,
        versions_qs=mock_versions_query_service,
        logger=mock_logger,
        provisioned_products_qs=mock_provisioned_products_qs,
        uow=mock_unit_of_work,
        feature_toggles_srv=mock_be_feature_toggles_srv,
        experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
        projects_qs=mocked_projects_qs,
    )

    # ASSERT
    mock_provisioned_products_qs.get_provisioned_products_by_project_id.assert_called_once_with(
        project_id="proj-123",
        exclude_status=[
            product_status.ProductStatus.ProvisioningError,
            product_status.ProductStatus.InstanceError,
            product_status.ProductStatus.Terminated,
        ],
        experimental=True,
    )
    mock_message_bus.publish.assert_called_once_with(
        product_launch_started.ProductLaunchStarted(provisionedProductId="pp-123", userIpAddress="127.0.0.1")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.add.assert_called_once_with(
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Provisioning,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="v1.0.0",
            versionDescription="Initial release",
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=provisioned_product.ProvisionedProductStage.QA,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(
                    key="SomeParam", value="some-default", parameterType="String"
                ),
                provisioning_parameter.ProvisioningParameter(
                    key="SomeTechParam",
                    value="/workbench/autosar/adaptive/ami-id/v1-3-x",
                    parameterType="AWS::SSM::Parameter::Value<String>",
                ),
                provisioning_parameter.ProvisioningParameter(key="Experimental", value="True", parameterType="String"),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            additionalConfigurations=[],
            experimental=True,
            userIpAddress="127.0.0.1",
            deploymentOption=provisioned_product.DeploymentOption.MULTI_AZ,
        )
    )
    mock_products_query_service.get_product.assert_called_once_with(project_id="proj-123", product_id="prod-123")
    mock_versions_query_service.get_product_version_distributions.assert_called_once_with(
        product_id="prod-123",
        version_id="vers-123",
        region="us-east-1",
        stage=version.VersionStage.QA,
    )


def test_launch_product_when_user_has_no_role_in_project(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_message_bus,
    mock_unit_of_work,
    mock_versions_query_service,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    mocked_projects_qs,
):
    # ARRANGE
    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list(
            [
                {
                    "key": "SomeTechParam",
                    "value": "/fake-ami-ssm-param",
                }
            ]
        ),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
    )

    mocked_projects_qs.get_project_assignment.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        launch.handle(
            command=command,
            publisher=mock_publisher,
            products_qs=mock_products_query_service,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
            uow=mock_unit_of_work,
            feature_toggles_srv=mock_be_feature_toggles_srv,
            experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
            projects_qs=mocked_projects_qs,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        "User does not have a role in the project to allow product provisioning"
    )
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@freeze_time("2023-12-05")
@mock.patch("random.randrange", return_value=12345)
def test_launch_product_with_single_az_deployment_option_stores_correctly(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_versions_query_service,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    get_test_version,
    mock_product,
    publishing_qry_svc_mock,
    mocked_projects_qs,
):
    # ARRANGE
    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list([]),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        provisioned_compound_product_id=provisioned_compound_product_id_value_object.from_string("cpp-123"),
        deployment_option=deployment_option_value_object.from_str("SINGLE_AZ"),
    )
    mock_versions_query_service.get_product_version_distributions.return_value = [
        get_mocked_product_version(
            region="us-east-1",
            stage=version.VersionStage.DEV,
            sc_product_id="sc-prod-123",
            sc_provisioning_artifact_id="sc-pa-123",
            aws_account_id="001234567890",
        )
    ]
    mock_products_query_service.get_product.return_value = mock_product

    # ACT
    launch.handle(
        command=command,
        publisher=mock_publisher,
        products_qs=mock_products_query_service,
        versions_qs=mock_versions_query_service,
        logger=mock_logger,
        provisioned_products_qs=mock_provisioned_products_qs,
        uow=mock_unit_of_work,
        feature_toggles_srv=mock_be_feature_toggles_srv,
        experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
        projects_qs=mocked_projects_qs,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_started.ProductLaunchStarted(provisionedProductId="pp-123", userIpAddress="127.0.0.1")
    )
    mock_unit_of_work.commit.assert_called_once()

    # Verify the saved entity has the correct deployment_option
    saved_entity_call = mock_provisioned_product_repo.add.call_args[0][0]
    assertpy.assert_that(saved_entity_call.deploymentOption).is_equal_to("SINGLE_AZ")
    assertpy.assert_that(saved_entity_call.provisionedProductId).is_equal_to("pp-123")


@freeze_time("2023-12-05")
@mock.patch("random.randrange", return_value=12345)
def test_launch_product_with_none_deployment_option_defaults_to_multi_az(
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_versions_query_service,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    get_test_version,
    mock_product,
    publishing_qry_svc_mock,
    mocked_projects_qs,
):
    # ARRANGE
    command = launch_product_command.LaunchProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        project_id=project_id_value_object.from_str("proj-123"),
        user_id=user_id_value_object.from_str("T0011AA"),
        user_domains=user_domains_value_object.from_list(["domain"]),
        product_id=product_id_value_object.from_str("prod-123"),
        version_id=product_version_id_value_object.from_str("vers-123"),
        provisioning_parameters=provisioning_parameters_value_object.from_list([]),
        additional_configurations=additional_configurations_value_object.from_list([]),
        stage=provisioned_product_stage_value_object.from_str("dev"),
        region=region_value_object.from_str("us-east-1"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        provisioned_compound_product_id=provisioned_compound_product_id_value_object.from_string("cpp-123"),
        deployment_option=deployment_option_value_object.from_str(None),  # This should default to MULTI_AZ
    )
    mock_versions_query_service.get_product_version_distributions.return_value = [
        get_mocked_product_version(
            region="us-east-1",
            stage=version.VersionStage.DEV,
            sc_product_id="sc-prod-123",
            sc_provisioning_artifact_id="sc-pa-123",
            aws_account_id="001234567890",
        )
    ]
    mock_products_query_service.get_product.return_value = mock_product

    # ACT
    launch.handle(
        command=command,
        publisher=mock_publisher,
        products_qs=mock_products_query_service,
        versions_qs=mock_versions_query_service,
        logger=mock_logger,
        provisioned_products_qs=mock_provisioned_products_qs,
        uow=mock_unit_of_work,
        feature_toggles_srv=mock_be_feature_toggles_srv,
        experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
        projects_qs=mocked_projects_qs,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_started.ProductLaunchStarted(provisionedProductId="pp-123", userIpAddress="127.0.0.1")
    )
    mock_unit_of_work.commit.assert_called_once()

    # Verify the saved entity has the correct deployment_option (should default to MULTI_AZ)
    saved_entity_call = mock_provisioned_product_repo.add.call_args[0][0]
    assertpy.assert_that(saved_entity_call.deploymentOption).is_equal_to("MULTI_AZ")
    assertpy.assert_that(saved_entity_call.provisionedProductId).is_equal_to("pp-123")


@freeze_time("2023-12-05")
@pytest.mark.parametrize(
    "product_id,version_id,user_id,random_value,expected_name",
    [
        pytest.param(
            "prod-123",
            "vers-123",
            "T0011AA",
            12345,
            "prod-123-vers-123-T0011AA-12345",
            id="valid_name",
        ),
        pytest.param(
            "prod@123",
            "vers#123",
            "T0011AA",
            12345,
            "prod-123-vers-123-T0011AA-12345",
            id="special_chars",
        ),
        pytest.param(
            "prod 123",
            "vers 123",
            "T0011AA",
            12345,
            "prod-123-vers-123-T0011AA-12345",
            id="spaces",
        ),
        pytest.param(
            "prod_123",
            "vers.123",
            "T0011AA",
            12345,
            "prod_123-vers-123-T0011AA-12345",
            id="dots_underscores",
        ),
    ],
)
def test_launch_product_sanitizes_provisioned_product_name(
    product_id,
    version_id,
    user_id,
    random_value,
    expected_name,
    mock_logger,
    mock_publisher,
    mock_products_query_service,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_versions_query_service,
    mock_provisioned_products_qs,
    mock_be_feature_toggles_srv,
    mock_experimental_provisioned_product_per_project_limit,
    mocked_projects_qs,
):
    # ARRANGE
    with mock.patch("random.randrange", return_value=random_value):
        command = launch_product_command.LaunchProductCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
            project_id=project_id_value_object.from_str("proj-123"),
            user_id=user_id_value_object.from_str(user_id),
            user_domains=user_domains_value_object.from_list(["domain"]),
            product_id=product_id_value_object.from_str(product_id),
            version_id=product_version_id_value_object.from_str(version_id),
            provisioning_parameters=provisioning_parameters_value_object.from_list([]),
            additional_configurations=additional_configurations_value_object.from_list([]),
            stage=provisioned_product_stage_value_object.from_str("dev"),
            region=region_value_object.from_str("us-east-1"),
            user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
            deployment_option=deployment_option_value_object.from_str("MULTI_AZ"),
        )

        # ACT
        launch.handle(
            command=command,
            publisher=mock_publisher,
            products_qs=mock_products_query_service,
            versions_qs=mock_versions_query_service,
            logger=mock_logger,
            provisioned_products_qs=mock_provisioned_products_qs,
            uow=mock_unit_of_work,
            feature_toggles_srv=mock_be_feature_toggles_srv,
            experimental_provisioned_product_per_project_limit=mock_experimental_provisioned_product_per_project_limit,
            projects_qs=mocked_projects_qs,
        )

        # ASSERT
        saved_entity = mock_provisioned_product_repo.add.call_args[0][0]
        assertpy.assert_that(saved_entity.provisionedProductName).is_equal_to(expected_name)
