import typing
from datetime import datetime, timezone

from app.projects.domain.commands.enrolments import reject_enrolments_command as command
from app.projects.domain.events.enrolments import enrolment_rejected
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import enrolment
from app.projects.domain.ports import enrolment_query_service, projects_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_reject_enrolments_command(
    cmd: command.RejectEnrolmentsCommand,
    uow: unit_of_work.UnitOfWork,
    enrolment_qry_srv: enrolment_query_service.EnrolmentQueryService,
    project_qry_srv: projects_query_service.ProjectsQueryService,
    message_bus: message_bus.MessageBus,
):
    project = project_qry_srv.get_project_by_id(cmd.project_id)
    if not project:
        raise domain_exception.DomainException(
            f"Failed to load project. Project for given ID {cmd.project_id} does not exist."
        )

    current_time = datetime.now(timezone.utc).isoformat()

    pending_events: typing.List[enrolment_rejected.EnrolmentRejected] = []

    with uow:
        for enrolment_id in cmd.enrolment_ids:
            enrolment_item = enrolment_qry_srv.get_enrolment_by_id(enrolment_id=enrolment_id, project_id=cmd.project_id)

            if not enrolment_item:
                raise domain_exception.DomainException("Enrolment not found.")

            if enrolment_item.status != enrolment.EnrolmentStatus.Pending:
                raise domain_exception.DomainException(
                    f"Failed to reject enrolments. Enrolment for user ID {enrolment_item.userId} is not in Pending status."
                )

            enrolment_item.status = enrolment.EnrolmentStatus.Rejected
            enrolment_item.reason = cmd.reason
            enrolment_item.resolveDate = current_time
            enrolment_item.lastUpdateDate = current_time
            enrolment_item.approver = cmd.rejecter_id.value
            uow.get_repository(enrolment.EnrolmentPrimaryKey, enrolment.Enrolment).update_entity(
                pk=enrolment.EnrolmentPrimaryKey(id=enrolment_id, projectId=cmd.project_id),
                entity=enrolment_item,
            )

            pending_events.append(
                enrolment_rejected.EnrolmentRejected(
                    programId=project.projectId,
                    programName=project.projectName,
                    userId=enrolment_item.userId,
                    userEmail=enrolment_item.userEmail,
                    enrolmentId=enrolment_item.id,
                    reason=cmd.reason,
                )  # type: ignore
            )

        uow.commit()

    for event in pending_events:
        message_bus.publish(event)
