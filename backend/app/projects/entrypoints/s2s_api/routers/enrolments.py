from uuid import uuid4

from aws_lambda_powertools import Tracer
from aws_lambda_powertools.event_handler.api_gateway import Router

from app.projects.domain.commands.enrolments import approve_enrolments_command, enrol_user_to_program_command
from app.projects.domain.value_objects import (
    enrolment_id_value_object,
    project_id_value_object,
    source_system_value_object,
    user_email_value_object,
    user_id_value_object,
)
from app.projects.entrypoints.s2s_api import bootstrapper
from app.projects.entrypoints.s2s_api.model import api_model

tracer = Tracer()


def init(dependencies: bootstrapper.Dependencies) -> Router:
    router = Router()

    @tracer.capture_method
    @router.post("/projects/<project_id>/enrolments")
    def enrol_user_to_project(request: api_model.EnrolUserRequest, project_id: str) -> api_model.EnrolUserResponse:
        """Enrol a user to a given project/program"""

        enrolment_id = str(uuid4())

        cmd = enrol_user_to_program_command.EnrolUserToProgramCommand(
            project_id=project_id_value_object.from_str(project_id),
            user_id=user_id_value_object.from_str(request.userId.upper()),
            user_email=user_email_value_object.from_str(request.userEmail),
            source_system=source_system_value_object.from_str("RTC"),
            enrolment_id=enrolment_id_value_object.from_str(enrolment_id),
        )

        enrolment_id = dependencies.command_bus.handle(cmd)

        cmd = approve_enrolments_command.ApproveEnrolmentsCommand(
            project_id=project_id,
            approver_id=user_id_value_object.from_str(request.approverId.upper()),
            enrolment_ids=[enrolment_id],
        )

        dependencies.command_bus.handle(cmd)

        return api_model.EnrolUserResponse()

    @tracer.capture_method
    @router.post("/projects/<project_id>/enrolments/pending")
    def enrol_pending_user_to_project(
        request: api_model.EnrolPendingUserRequest, project_id: str
    ) -> api_model.EnrolPendingUserResponse:
        """Enrol a user to a given project/program in state pending. There will no automatic approval"""

        enrolment_id = str(uuid4())

        cmd = enrol_user_to_program_command.EnrolUserToProgramCommand(
            project_id=project_id_value_object.from_str(project_id),
            user_id=user_id_value_object.from_str(request.userId.upper()),
            user_email=user_email_value_object.from_str(request.userEmail),
            source_system=source_system_value_object.from_str(request.source),
            enrolment_id=enrolment_id_value_object.from_str(enrolment_id),
        )

        dependencies.command_bus.handle(cmd)

        return api_model.EnrolPendingUserResponse()

    return router
