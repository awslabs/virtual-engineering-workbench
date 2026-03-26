import typing
from datetime import datetime, timezone

from app.projects.domain.commands.enrolments import approve_enrolments_command as command
from app.projects.domain.events.enrolments import enrolment_approved
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import enrolment, project_assignment, user
from app.projects.domain.ports import enrolment_query_service, projects_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

DEFAULT_USER_ROLES = [project_assignment.Role.PLATFORM_USER]


def handle_approve_enrolments_command(
    cmd: command.ApproveEnrolmentsCommand,
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

    pending_events: typing.List[enrolment_approved.EnrolmentApproved] = []

    with uow:
        for enrolment_id in cmd.enrolment_ids:
            enrolment_item = enrolment_qry_srv.get_enrolment_by_id(enrolment_id=enrolment_id, project_id=cmd.project_id)

            if not enrolment_item:
                raise domain_exception.DomainException("Enrolment not found.")

            if enrolment_item.status != enrolment.EnrolmentStatus.Pending:
                raise domain_exception.DomainException(
                    f"Failed to approve enrolments. Enrolment for user ID {enrolment_item.userId} is not pending"
                )

            assigned_roles = DEFAULT_USER_ROLES
            if not (
                assignment := project_qry_srv.get_user_assignment(
                    project_id=cmd.project_id, user_id=enrolment_item.userId.upper()
                )
            ):
                new_assignment = project_assignment.Assignment(
                    userId=enrolment_item.userId.upper(),
                    projectId=cmd.project_id,
                    roles=DEFAULT_USER_ROLES,
                    userEmail=enrolment_item.userEmail,
                    activeDirectoryGroups=[],
                    activeDirectoryGroupStatus=user.UserADStatus.PENDING,
                )
                uow.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).add(
                    new_assignment
                )
            else:
                missing_roles = set(DEFAULT_USER_ROLES) - set(assignment.roles)
                if missing_roles:
                    assignment.roles.extend(list(missing_roles))
                    assignment.activeDirectoryGroupStatus = user.UserADStatus.PENDING

                    uow.get_repository(
                        project_assignment.AssignmentPrimaryKey, project_assignment.Assignment
                    ).update_entity(
                        pk=project_assignment.AssignmentPrimaryKey(
                            userId=assignment.userId, projectId=assignment.projectId
                        ),
                        entity=assignment,
                    )

                assigned_roles = assignment.roles

            enrolment_item.status = enrolment.EnrolmentStatus.Approved
            enrolment_item.approver = cmd.approver_id.value
            enrolment_item.resolveDate = current_time
            enrolment_item.lastUpdateDate = current_time

            uow.get_repository(enrolment.EnrolmentPrimaryKey, enrolment.Enrolment).update_entity(
                pk=enrolment.EnrolmentPrimaryKey(id=enrolment_item.id, projectId=enrolment_item.projectId),
                entity=enrolment_item,
            )

            pending_events.append(
                enrolment_approved.EnrolmentApproved(
                    programId=project.projectId,
                    programName=project.projectName,
                    userId=enrolment_item.userId,
                    userEmail=enrolment_item.userEmail,
                    enrolmentId=enrolment_item.id,
                    roles=assigned_roles,
                )
            )

        uow.commit()

    for event in pending_events:
        message_bus.publish(event)
