from unittest import mock

from freezegun import freeze_time

from app.provisioning.domain.event_handlers import update_recommended_version_handler
from app.provisioning.domain.read_models import version
from app.provisioning.domain.tests.product_provisioning.conftest import TEST_OS_VERSION
from app.provisioning.domain.tests.read_models.conftest import TEST_COMPONENT_VERSION_DETAILS


@freeze_time("2023-10-25")
def test_update_recommended_version_updates_recommended_version(
    uow_mock,
    get_sample_product,
    versions_qry_svc_mock,
    get_sample_version,
    versions_repo_mock,
    product_qry_svc_mock,
):
    # ARRANGE
    product_qry_svc_mock.get_product.return_value = get_sample_product()
    versions_qry_svc_mock.get_product_version_distributions.side_effect = (
        [get_sample_version(index=2, is_recommended=False)],
        [get_sample_version(index=1, is_recommended=True)],
    )
    # ACT
    update_recommended_version_handler.handle(
        project_id="proj-123",
        product_id="prod-123",
        new_recommended_version_id="vers-2",
        product_qry_srv=product_qry_svc_mock,
        versions_qry_srv=versions_qry_svc_mock,
        uow=uow_mock,
    )

    # ASSERT
    calls = [
        mock.call(
            pk=version.VersionPrimaryKey(productId="prod-123", versionId="vers-1", awsAccountId="105249321508"),
            entity=version.Version.parse_obj(
                {
                    "projectId": "proj-123",
                    "productId": "prod-123",
                    "technologyId": "tech-123",
                    "versionId": "vers-1",
                    "versionName": "1.0.0",
                    "versionDescription": "version description",
                    "awsAccountId": "105249321508",
                    "accountId": "acct-12345",
                    "stage": version.VersionStage.DEV,
                    "region": "us-east-1",
                    "amiId": "ami-12345",
                    "scProductId": "prod-12345",
                    "scProvisioningArtifactId": "pa-12345",
                    "isRecommendedVersion": False,
                    "componentVersionDetails": TEST_COMPONENT_VERSION_DETAILS,
                    "osVersion": TEST_OS_VERSION,
                    "parameters": [
                        version.VersionParameter(
                            parameterKey=f"{param_index}",
                            defaultValue="mock-value",
                            description="mock-description",
                            isNoEcho=False,
                            parameterType="mock-param-type",
                            parameterMetadata=version.ParameterMetadata(
                                label="mock-label", optionLabels={"test": "label"}
                            ),
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
                }
            ),
        ),
        mock.call(
            pk=version.VersionPrimaryKey(productId="prod-123", versionId="vers-2", awsAccountId="105249321508"),
            entity=version.Version.parse_obj(
                {
                    "projectId": "proj-123",
                    "productId": "prod-123",
                    "technologyId": "tech-123",
                    "versionId": "vers-2",
                    "versionName": "1.0.0",
                    "versionDescription": "version description",
                    "awsAccountId": "105249321508",
                    "accountId": "acct-12345",
                    "stage": version.VersionStage.DEV,
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
                            parameterMetadata=version.ParameterMetadata(
                                label="mock-label", optionLabels={"test": "label"}
                            ),
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
                }
            ),
        ),
    ]
    versions_repo_mock.update_entity.assert_has_calls(calls=calls, any_order=True)
    uow_mock.commit.assert_called_once()
    versions_repo_mock.add.assert_not_called()
    versions_repo_mock.remove.assert_not_called()
