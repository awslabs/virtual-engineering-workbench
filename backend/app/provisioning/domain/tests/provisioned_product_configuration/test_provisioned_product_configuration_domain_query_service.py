import assertpy
import pytest

from app.provisioning.domain.model import additional_configuration
from app.provisioning.domain.query_services import provisioned_product_configuration_domain_query_service
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@pytest.mark.parametrize(
    "expected_status, expected_reason",
    [
        (additional_configuration.AdditionalConfigurationRunStatus.Success, "Success"),
        (additional_configuration.AdditionalConfigurationRunStatus.Failed, "Failed"),
        (
            additional_configuration.AdditionalConfigurationRunStatus.InProgress,
            "InProgress",
        ),
    ],
)
def test_get_provisioned_product_configuration_run_status_returns_correct_status(
    expected_status, expected_reason, mock_provisioned_products_qs, mock_system_command_service
):
    # Arrange
    mock_system_command_service.get_run_status.return_value = (expected_status, expected_reason)
    pp_domain_qry_srv = (
        provisioned_product_configuration_domain_query_service.ProvisionedProductConfigurationDomainQueryService(
            provisioned_products_qry_srv=mock_provisioned_products_qs, system_command_srv=mock_system_command_service
        )
    )

    # Act
    actual_status, actual_reason = pp_domain_qry_srv.get_provisioned_product_configuration_run_status(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    # Assert
    assertpy.assert_that(actual_status).is_equal_to(expected_status)
    assertpy.assert_that(actual_reason).is_equal_to(expected_reason)


def test_is_provisioned_product_ready_returns_true_when_pp_is_ready(
    mock_provisioned_products_qs, mock_system_command_service
):
    # Arrange
    pp_domain_qry_srv = (
        provisioned_product_configuration_domain_query_service.ProvisionedProductConfigurationDomainQueryService(
            provisioned_products_qry_srv=mock_provisioned_products_qs, system_command_srv=mock_system_command_service
        )
    )

    # Act
    is_pp_ready = pp_domain_qry_srv.is_provisioned_product_ready(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123")
    )

    # Assert
    assertpy.assert_that(is_pp_ready).is_true()
