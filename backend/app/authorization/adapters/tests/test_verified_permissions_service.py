import assertpy

from app.authorization.adapters.services import verified_permissions_service

TEST_POLICY_STORE_ID = "policystore-12345"
TEST_REGION = "us-east-1"


def test_is_action_allowed_returns_true_when_allowed(mock_moto_error_calls, mock_avp, mock_avp_is_authorized_request):
    # ARRANGE
    service = verified_permissions_service.VerifiedPermissionsService(verified_permissions_client=mock_avp)

    # ACT
    result = service.is_action_allowed(
        policy_store_id=TEST_POLICY_STORE_ID,
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "DoSmth", "actionType": "VEW::Action"},
        resource={"entityId": "proj-123", "entityType": "VEW::Project"},
        entities=[],
    )

    # ASSERT
    assertpy.assert_that(result).is_true()
    mock_avp_is_authorized_request.assert_called_once_with(
        policyStoreId=TEST_POLICY_STORE_ID,
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "DoSmth", "actionType": "VEW::Action"},
        resource={"entityId": "proj-123", "entityType": "VEW::Project"},
        entities=[],
    )


def test_is_action_allowed_ignores_none_values(mock_moto_error_calls, mock_avp, mock_avp_is_authorized_request):
    # ARRANGE
    service = verified_permissions_service.VerifiedPermissionsService(verified_permissions_client=mock_avp)

    # ACT
    result = service.is_action_allowed(
        policy_store_id=TEST_POLICY_STORE_ID,
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "DoSmth", "actionType": "VEW::Action"},
        resource=None,
        entities=[],
    )

    # ASSERT
    assertpy.assert_that(result).is_true()
    mock_avp_is_authorized_request.assert_called_once_with(
        policyStoreId=TEST_POLICY_STORE_ID,
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "DoSmth", "actionType": "VEW::Action"},
        entities=[],
    )


def test_is_action_allowed_returns_false_when_denied(
    mock_is_authorized_denied_response, mock_moto_error_calls, mock_avp, mock_avp_is_authorized_request
):
    # ARRANGE
    mock_avp_is_authorized_request.return_value = mock_is_authorized_denied_response
    service = verified_permissions_service.VerifiedPermissionsService(verified_permissions_client=mock_avp)

    # ACT
    result = service.is_action_allowed(
        policy_store_id=TEST_POLICY_STORE_ID,
        principal={"entityId": "test-user", "entityType": "VEW::User"},
        action={"actionId": "DoSmth", "actionType": "VEW::Action"},
        resource={"entityId": "proj-123", "entityType": "VEW::Project"},
        entities=[],
    )

    # ASSERT
    assertpy.assert_that(result).is_false()
