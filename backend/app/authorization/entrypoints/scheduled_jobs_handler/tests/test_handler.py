from unittest import mock


@mock.patch("app.authorization.domain.command_handlers.sync_assignments_command_handler.handle", autospec=True)
def test_handler_when_sync_job_is_triggered_invokes_sync_command(
    mocked_command_handler,
    lambda_context,
    assignment_sync_job_event,
):
    # ARRANGE
    from app.authorization.entrypoints.scheduled_jobs_handler import handler

    # ACT
    handler.handler(assignment_sync_job_event, lambda_context)

    # ASSERT
    mocked_command_handler.assert_called_once()
