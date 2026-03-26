from assertpy import assert_that

from app.shared.logging import helpers

AUTH_HEADER = "Bearer a.b.c"


def test_clear_auth_headers_should_mask_credentials():
    # ARRANGE
    payload = {
        "resource": "/projects",
        "httpMethod": "GET",
        "headers": {"Authorization": AUTH_HEADER},
        "multiValueHeaders": {"Authorization": [AUTH_HEADER]},
    }

    # ACT
    response = helpers.clear_auth_headers(payload)

    # ASSERT
    assert_that(response["headers"]["Authorization"]).is_equal_to("***")
    assert_that(response["multiValueHeaders"]["Authorization"][0]).is_equal_to("***")


def test_clear_auth_headers_should_work_when_no_header_present():
    # ARRANGE
    payload = {
        "resource": "/projects",
        "httpMethod": "GET",
    }

    # ACT
    response = helpers.clear_auth_headers(payload)

    # ASSERT
    assert_that(response).is_equal_to(
        {
            "resource": "/projects",
            "httpMethod": "GET",
        }
    )


def test_clear_auth_headers_should_mask_user_info():
    # ARRANGE
    payload = {
        "resource": "/notifications",
        "httpMethod": "GET",
        "requestContext": {"authorizer": {"userEmail": "user@example.com", "userName": "testuser", "userRoles": "[]"}},
    }

    # ACT
    response = helpers.clear_auth_headers(payload)

    # ASSERT
    assert_that(response["requestContext"]["authorizer"]["userEmail"]).is_equal_to("***")
    assert_that(response["requestContext"]["authorizer"]["userName"]).is_equal_to("***")
    assert_that(response["requestContext"]["authorizer"]["userRoles"]).is_equal_to("[]")
