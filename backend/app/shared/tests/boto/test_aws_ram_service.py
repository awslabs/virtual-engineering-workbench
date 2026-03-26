import assertpy

from app.shared.adapters.boto import aws_resource_access_management_service


def test_get_resource_shares_returns_resource_share_arns(mock_ram_share, mock_ram_client_provider):
    # ARRANGE
    ram_svc = aws_resource_access_management_service.AWSResourceAccessManagementService(
        ram_provider=mock_ram_client_provider
    )

    # ACT
    resp = ram_svc.get_resource_shares(tag_name="test-key")

    # ASSERT
    assertpy.assert_that(resp).is_length(1)


def test_associate_resource_share_associates_principal(
    mock_ram_client_provider, mock_moto_error_calls, mock_associate_resource_share_request
):
    # ARRANGE
    ram_svc = aws_resource_access_management_service.AWSResourceAccessManagementService(
        ram_provider=mock_ram_client_provider
    )

    # ACT
    ram_svc.associate_resource_share(
        resource_share_arn="test-arn",
        principals=["001234567890"],
    )

    # ASSERT
    mock_associate_resource_share_request.assert_called_once_with(
        principals=["001234567890"],
        resourceShareArn="test-arn",
    )
