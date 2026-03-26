import json

import assertpy


def test_scheduled_metric_producer_handler(mock_dependencies, lambda_context, metric_producer_job_event, capsys):
    # ARRANGE
    from app.provisioning.entrypoints.scheduled_jobs_handler import handler

    handler.dependencies = mock_dependencies

    # ACT
    handler.handler(metric_producer_job_event, lambda_context)

    # ASSERT
    captured_stdout, captured_stderr = capsys.readouterr()
    log_entries = captured_stdout.split("\n")
    log_entries_dict = [json.loads(s) for s in log_entries if s]
    program_a_metric_users = next(
        m
        for m in log_entries_dict
        if "Program" in m and m["Program"] == "Program A" and "TotalProgramUsersWithProvisionedProducts" in m
    )
    program_b_metric_users = next(
        m
        for m in log_entries_dict
        if "Program" in m and m["Program"] == "Program B" and "TotalProgramUsersWithProvisionedProducts" in m
    )
    program_a_metric_provisioned_products = next(
        m
        for m in log_entries_dict
        if "Program" in m and m["Program"] == "Program A" and "TotalProgramProvisionedProducts" in m
    )
    program_b_metric_provisioned_products = next(
        m
        for m in log_entries_dict
        if "Program" in m and m["Program"] == "Program B" and "TotalProgramProvisionedProducts" in m
    )
    program_a_metric_running_products = next(
        m
        for m in log_entries_dict
        if "Program" in m and m["Program"] == "Program A" and "TotalProgramRunningProvisionedProducts" in m
    )
    program_b_metric_running_products = next(
        m
        for m in log_entries_dict
        if "Program" in m and m["Program"] == "Program B" and "TotalProgramRunningProvisionedProducts" in m
    )
    program_a_metric_current_active_users = next(
        m
        for m in log_entries_dict
        if "Program" in m and m["Program"] == "Program A" and "TotalProgramCurrentActiveUsers" in m
    )
    program_b_metric_current_active_users = next(
        m
        for m in log_entries_dict
        if "Program" in m and m["Program"] == "Program B" and "TotalProgramCurrentActiveUsers" in m
    )
    program_a_metric_provisioned_product_names = next(
        m
        for m in log_entries_dict
        if "Program" in m
        and "ProductName" in m
        and m["Program"] == "Program A"
        and m["ProductName"] == "Pied Piper"
        and "TotalProgramProvisionedProductNames" in m
    )
    program_b_metric_provisioned_product_names = next(
        m
        for m in log_entries_dict
        if "Program" in m
        and "ProductName" in m
        and m["Program"] == "Program B"
        and m["ProductName"] == "Pied Piper"
        and "TotalProgramProvisionedProductNames" in m
    )
    program_a_metric_running_provisioned_product_names = next(
        m
        for m in log_entries_dict
        if "Program" in m
        and "ProductName" in m
        and m["Program"] == "Program A"
        and m["ProductName"] == "Pied Piper"
        and "TotalProgramRunningProvisionedProductNames" in m
    )
    program_b_metric_running_provisioned_product_names = next(
        m
        for m in log_entries_dict
        if "Program" in m
        and "ProductName" in m
        and m["Program"] == "Program B"
        and m["ProductName"] == "Pied Piper"
        and "TotalProgramRunningProvisionedProductNames" in m
    )
    total_provisioned_products = next(m for m in log_entries_dict if "TotalProvisionedProducts" in m)
    total_users_with_provisioned_products = next(
        m for m in log_entries_dict if "TotalUsersWithProvisionedProducts" in m
    )
    total_running_provisioned_products = next(m for m in log_entries_dict if "TotalRunningProvisionedProducts" in m)
    total_current_active_users = next(m for m in log_entries_dict if "TotalCurrentActiveUsers" in m)

    assertpy.assert_that(program_a_metric_users).contains_entry({"TotalProgramUsersWithProvisionedProducts": [3.0]})
    assertpy.assert_that(program_b_metric_users).contains_entry({"TotalProgramUsersWithProvisionedProducts": [3.0]})

    assertpy.assert_that(program_a_metric_provisioned_products).contains_entry(
        {"TotalProgramProvisionedProducts": [3.0]}
    )
    assertpy.assert_that(program_b_metric_provisioned_products).contains_entry(
        {"TotalProgramProvisionedProducts": [3.0]}
    )

    assertpy.assert_that(program_a_metric_running_products).contains_entry(
        {"TotalProgramRunningProvisionedProducts": [2.0]}
    )
    assertpy.assert_that(program_b_metric_running_products).contains_entry(
        {"TotalProgramRunningProvisionedProducts": [2.0]}
    )

    assertpy.assert_that(program_a_metric_current_active_users).contains_entry(
        {"TotalProgramCurrentActiveUsers": [2.0]}
    )
    assertpy.assert_that(program_b_metric_current_active_users).contains_entry(
        {"TotalProgramCurrentActiveUsers": [2.0]}
    )

    assertpy.assert_that(program_a_metric_provisioned_product_names).contains_entry(
        {"TotalProgramProvisionedProductNames": [3.0]}
    )
    assertpy.assert_that(program_b_metric_provisioned_product_names).contains_entry(
        {"TotalProgramProvisionedProductNames": [3.0]}
    )

    assertpy.assert_that(program_a_metric_running_provisioned_product_names).contains_entry(
        {"TotalProgramRunningProvisionedProductNames": [2.0]}
    )
    assertpy.assert_that(program_b_metric_running_provisioned_product_names).contains_entry(
        {"TotalProgramRunningProvisionedProductNames": [2.0]}
    )

    assertpy.assert_that(total_provisioned_products).contains_entry({"TotalProvisionedProducts": [6.0]})
    assertpy.assert_that(total_users_with_provisioned_products).contains_entry(
        {"TotalUsersWithProvisionedProducts": [3.0]}
    )
    assertpy.assert_that(total_running_provisioned_products).contains_entry({"TotalRunningProvisionedProducts": [4.0]})
    assertpy.assert_that(total_current_active_users).contains_entry({"TotalCurrentActiveUsers": [2.0]})


def test_handler_when_sync_job_is_triggered_invokes_sync_command(
    mock_dependencies,
    lambda_context,
    provisioned_product_sync_job_event,
    mock_sync_provisioned_products_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.scheduled_jobs_handler import handler

    handler.dependencies = mock_dependencies

    # ACT
    handler.handler(provisioned_product_sync_job_event, lambda_context)

    # ASSERT
    mock_sync_provisioned_products_command_handler.assert_called_once()


def test_scheduled_provisioned_products_cleanup_handler(
    mock_dependencies,
    lambda_context,
    provisioned_product_cleanup_job_event,
    mock_provisioned_product_cleanup_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.scheduled_jobs_handler import handler

    handler.dependencies = mock_dependencies

    # ACT
    handler.handler(provisioned_product_cleanup_job_event, lambda_context)

    # ASSERT
    mock_provisioned_product_cleanup_command_handler.assert_called_once()


def test_provisioned_product_batch_stop_handler(
    mock_dependencies,
    lambda_context,
    provisioned_product_batch_stop_job_event,
    mock_initiate_provisioned_product_batch_stop_command_handler,
):
    # ARRANGE
    from app.provisioning.entrypoints.scheduled_jobs_handler import handler

    handler.dependencies = mock_dependencies

    # ACT
    handler.handler(provisioned_product_batch_stop_job_event, lambda_context)

    # ASSERT
    mock_initiate_provisioned_product_batch_stop_command_handler.assert_called_once()
