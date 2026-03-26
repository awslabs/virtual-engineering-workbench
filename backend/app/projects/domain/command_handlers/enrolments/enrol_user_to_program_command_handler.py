from datetime import datetime, timezone

from app.projects.domain.commands.enrolments import enrol_user_to_program_command as command
from app.projects.domain.events.enrolments import program_access_requested
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import enrolment
from app.projects.domain.ports import enrolment_query_service, projects_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_enrol_user_to_program_command(
    cmd: command.EnrolUserToProgramCommand,
    uow: unit_of_work.UnitOfWork,
    projects_qry_srv: projects_query_service.ProjectsQueryService,
    enrolment_qry_srv: enrolment_query_service.EnrolmentQueryService,
    msg_bus: message_bus.MessageBus,
):
    project = projects_qry_srv.get_project_by_id(cmd.project_id.value)
    if not project:
        raise domain_exception.DomainException(
            f"Failed to load project. Project for given ID {cmd.project_id.value} does not exist."
        )
    current_time = datetime.now(timezone.utc).isoformat()

    existing_enrolments, _ = enrolment_qry_srv.list_enrolments_by_user(
        user_id=cmd.user_id.value, page_size=50, next_token=None, status=enrolment.EnrolmentStatus.Pending
    )

    existing_enrolment = next((e for e in existing_enrolments if e.projectId == cmd.project_id.value), None)

    if existing_enrolment:
        return existing_enrolment.id

    pending_enrolment = enrolment.Enrolment(
        userId=cmd.user_id.value,
        userEmail=cmd.user_email.value,
        projectId=cmd.project_id.value,
        status=enrolment.EnrolmentStatus.Pending,
        createDate=current_time,
        lastUpdateDate=current_time,
        sourceSystem=cmd.source_system.value,
    )

    if cmd.enrolment_id:
        pending_enrolment.id = cmd.enrolment_id.value

    with uow:
        uow.get_repository(enrolment.EnrolmentPrimaryKey, enrolment.Enrolment).add(pending_enrolment)
        uow.commit()

    msg_bus.publish(
        program_access_requested.ProgramAccessRequested(
            programId=project.projectId,
            programName=project.projectName,
            userId=cmd.user_id.value,
            userEmail=cmd.user_email.value,
            referenceId=pending_enrolment.id,
            sourceSystem=cmd.source_system.value,
        )  # type: ignore
    )

    return pending_enrolment.id
