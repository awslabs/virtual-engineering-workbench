import assertpy


def test_describe_log_groups_should_return_all_log_groups(mock_aws_logs_service, mock_logs_client):
    # ARRANGE
    mock_logs_client.create_log_group(logGroupName="/aws/lambda/test-function-1")
    mock_logs_client.create_log_group(logGroupName="/aws/lambda/test-function-2")
    mock_logs_client.create_log_group(logGroupName="/aws/ecs/other-service")

    # ACT
    log_groups = mock_aws_logs_service.describe_log_groups()

    # ASSERT
    assertpy.assert_that(log_groups).is_length(3)
    log_group_names = [lg["logGroupName"] for lg in log_groups]
    assertpy.assert_that(log_group_names).contains(
        "/aws/lambda/test-function-1", "/aws/lambda/test-function-2", "/aws/ecs/other-service"
    )


def test_put_retention_policy_should_set_retention(mock_aws_logs_service, mock_logs_client):
    # ARRANGE
    log_group_name = "/aws/lambda/test-function"
    retention_days = 7
    mock_logs_client.create_log_group(logGroupName=log_group_name)

    # ACT
    mock_aws_logs_service.put_retention_policy(log_group_name=log_group_name, retention_days=retention_days)

    # ASSERT
    response = mock_logs_client.describe_log_groups(logGroupNamePrefix=log_group_name)
    assertpy.assert_that(response["logGroups"][0]["retentionInDays"]).is_equal_to(retention_days)
