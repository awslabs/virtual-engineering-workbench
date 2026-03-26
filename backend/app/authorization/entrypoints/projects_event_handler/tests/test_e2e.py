import assertpy


def test_enrolment_approved_creates_user_assignment_entity(
    enrolment_approved_event, generate_event, backend_app_dynamodb_table, lambda_context
):
    # ARRANGE
    event = generate_event(detail_type="EnrolmentApproved", detail=enrolment_approved_event)
    from app.authorization.entrypoints.projects_event_handler import handler

    # ACT
    handler.handler(event=event, context=lambda_context)

    # ASSERT

    saved_entity = backend_app_dynamodb_table.get_item(Key={"PK": "USER#test-user-id", "SK": "PROJECT#proj-123"})

    assertpy.assert_that(saved_entity).is_not_none()
    assertpy.assert_that(saved_entity.get("Item")).is_equal_to(
        {
            "PK": "USER#test-user-id",
            "SK": "PROJECT#proj-123",
            "activeDirectoryGroups": None,
            "projectId": "proj-123",
            "roles": ["PLATFORM_USER"],
            "userEmail": "user@example.doesnotexist",
            "userId": "test-user-id",
            "sequenceNo": 0,
            "groupMemberships": ["VEW_USERS"],
        }
    )


def test_user_assigned_creates_user_assignment_entity(
    user_assigned_event, generate_event, backend_app_dynamodb_table, lambda_context
):
    # ARRANGE
    event = generate_event(detail_type="UserAssigned", detail=user_assigned_event)
    from app.authorization.entrypoints.projects_event_handler import handler

    # ACT
    handler.handler(event=event, context=lambda_context)

    # ASSERT

    saved_entity = backend_app_dynamodb_table.get_item(Key={"PK": "USER#test-user-id", "SK": "PROJECT#proj-123"})

    assertpy.assert_that(saved_entity).is_not_none()
    assertpy.assert_that(saved_entity.get("Item")).is_equal_to(
        {
            "PK": "USER#test-user-id",
            "SK": "PROJECT#proj-123",
            "activeDirectoryGroups": None,
            "projectId": "proj-123",
            "roles": ["PLATFORM_USER"],
            "userEmail": None,
            "userId": "test-user-id",
            "sequenceNo": 0,
            "groupMemberships": ["VEW_USERS"],
        }
    )


def test_user_reassigned_creates_user_assignment_entity(
    user_reassigned_event, generate_event, backend_app_dynamodb_table, lambda_context
):
    # ARRANGE
    event = generate_event(detail_type="UserReAssigned", detail=user_reassigned_event)
    from app.authorization.entrypoints.projects_event_handler import handler

    # ACT
    handler.handler(event=event, context=lambda_context)

    # ASSERT

    saved_entity = backend_app_dynamodb_table.get_item(Key={"PK": "USER#test-user-id", "SK": "PROJECT#proj-123"})

    assertpy.assert_that(saved_entity).is_not_none()
    assertpy.assert_that(saved_entity.get("Item")).is_equal_to(
        {
            "PK": "USER#test-user-id",
            "SK": "PROJECT#proj-123",
            "activeDirectoryGroups": None,
            "projectId": "proj-123",
            "roles": ["PLATFORM_USER"],
            "userEmail": None,
            "userId": "test-user-id",
            "sequenceNo": 0,
            "groupMemberships": ["VEW_USERS"],
        }
    )


def test_user_unassigned_removes_assignment(
    user_unassigned_event, generate_event, backend_app_dynamodb_table, lambda_context
):
    # ARRANGE
    backend_app_dynamodb_table.put_item(
        Item={
            "PK": "USER#test-user-id",
            "SK": "PROJECT#proj-123",
            "activeDirectoryGroups": None,
            "projectId": "proj-123",
            "roles": ["PLATFORM_USER"],
            "userEmail": None,
            "userId": "test-user-id",
        }
    )

    event = generate_event(detail_type="UserUnAssigned", detail=user_unassigned_event)
    from app.authorization.entrypoints.projects_event_handler import handler

    # ACT
    handler.handler(event=event, context=lambda_context)

    # ASSERT

    saved_entity = backend_app_dynamodb_table.get_item(Key={"PK": "USER#test-user-id", "SK": "PROJECT#proj-123"})

    assertpy.assert_that(saved_entity.get("Item", None)).is_none()
