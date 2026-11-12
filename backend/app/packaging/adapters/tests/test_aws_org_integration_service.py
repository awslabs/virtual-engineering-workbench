import assertpy

from app.packaging.adapters.tests.conftest import GlobalVariables


def test_is_license_manager_org_integration_active_should_return_true_when_lm_share_present(
    mock_moto_calls, get_org_integration_srv
):
    # ACT
    result = get_org_integration_srv.is_license_manager_org_integration_active()

    # ASSERT
    assertpy.assert_that(result).is_true()
    mock_moto_calls["DescribeOrganization"].assert_called_once()
    mock_moto_calls["GetResourceShares"].assert_called_once_with(resourceOwner="OTHER-ACCOUNTS")


def test_is_license_manager_org_integration_active_should_use_self_scope_when_caller_is_the_management_account(
    mock_moto_calls,
    mock_get_caller_identity_response,
    get_org_integration_srv,
):
    # ARRANGE - caller is the organization's management account
    mock_get_caller_identity_response["Account"] = GlobalVariables.TEST_ORG_MANAGEMENT_ACCOUNT_ID.value
    mock_moto_calls["GetCallerIdentity"].return_value = mock_get_caller_identity_response

    # ACT
    result = get_org_integration_srv.is_license_manager_org_integration_active()

    # ASSERT
    assertpy.assert_that(result).is_true()
    mock_moto_calls["GetResourceShares"].assert_called_once_with(resourceOwner="SELF")


def test_is_license_manager_org_integration_active_should_return_false_when_no_share(
    mock_moto_calls, get_org_integration_srv
):
    # ARRANGE
    mock_moto_calls["GetResourceShares"].return_value = {"resourceShares": []}

    # ACT
    result = get_org_integration_srv.is_license_manager_org_integration_active()

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_is_license_manager_org_integration_active_should_return_false_when_share_name_does_not_match(
    mock_moto_calls, get_org_integration_srv
):
    # ARRANGE — share is active but not the License Manager one
    mock_moto_calls["GetResourceShares"].return_value = {
        "resourceShares": [
            {
                "resourceShareArn": "arn:aws:ram:us-east-1:555555555555:resource-share/unrelated",
                "name": "someOtherShare",
                "owningAccountId": GlobalVariables.TEST_ORG_MANAGEMENT_ACCOUNT_ID.value,
                "status": "ACTIVE",
            }
        ]
    }

    # ACT
    result = get_org_integration_srv.is_license_manager_org_integration_active()

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_is_license_manager_org_integration_active_should_return_false_when_share_not_owned_by_the_management_account(
    mock_moto_calls, get_org_integration_srv
):
    # ARRANGE — LM share name but wrong owner
    mock_moto_calls["GetResourceShares"].return_value = {
        "resourceShares": [
            {
                "resourceShareArn": "arn:aws:ram:us-east-1:999999999999:resource-share/x",
                "name": "licenseManagerResourceShare-x",
                "owningAccountId": "999999999999",
                "status": "ACTIVE",
            }
        ]
    }

    # ACT
    result = get_org_integration_srv.is_license_manager_org_integration_active()

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_is_license_manager_org_integration_active_should_return_false_when_share_not_active(
    mock_moto_calls, get_org_integration_srv
):
    # ARRANGE — right owner and name but not ACTIVE
    mock_moto_calls["GetResourceShares"].return_value = {
        "resourceShares": [
            {
                "resourceShareArn": GlobalVariables.TEST_LM_RESOURCE_SHARE_ARN.value,
                "name": "licenseManagerResourceShare-1",
                "owningAccountId": GlobalVariables.TEST_ORG_MANAGEMENT_ACCOUNT_ID.value,
                "status": "PENDING",
            }
        ]
    }

    # ACT
    result = get_org_integration_srv.is_license_manager_org_integration_active()

    # ASSERT
    assertpy.assert_that(result).is_false()


def test_is_license_manager_org_integration_active_follows_the_resource_share_pages(
    mock_moto_calls, get_org_integration_srv
):
    """get_resource_shares is paginated. Reading only the first page meant the License
    Manager share could sit on a later page, the integration looked inactive, and an
    import that should have been allowed was blocked."""
    # ARRANGE — the matching share is on the second page only
    mock_moto_calls["GetResourceShares"].side_effect = [
        {
            "resourceShares": [
                {
                    "resourceShareArn": "arn:aws:ram:us-east-1:555555555555:resource-share/unrelated",
                    "name": "SomeOtherShare",
                    "owningAccountId": GlobalVariables.TEST_ORG_MANAGEMENT_ACCOUNT_ID.value,
                    "status": "ACTIVE",
                }
            ],
            "nextToken": "page-2",
        },
        {
            "resourceShares": [
                {
                    "resourceShareArn": GlobalVariables.TEST_LM_RESOURCE_SHARE_ARN.value,
                    "name": "licenseManagerResourceShareForOrg",
                    "owningAccountId": GlobalVariables.TEST_ORG_MANAGEMENT_ACCOUNT_ID.value,
                    "status": "ACTIVE",
                }
            ]
        },
    ]

    # ACT
    result = get_org_integration_srv.is_license_manager_org_integration_active()

    # ASSERT
    assertpy.assert_that(result).is_true()
    assertpy.assert_that(mock_moto_calls["GetResourceShares"].call_count).is_equal_to(2)
    second_call = mock_moto_calls["GetResourceShares"].call_args_list[1]
    assertpy.assert_that(second_call.kwargs.get("nextToken")).is_equal_to("page-2")
