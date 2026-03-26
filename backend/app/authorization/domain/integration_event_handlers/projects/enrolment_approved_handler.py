from app.authorization.domain.integration_events.projects import enrolment_approved
from app.authorization.domain.read_models import project_assignment
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(event: enrolment_approved.EnrolmentApproved, uow: unit_of_work.UnitOfWork):
    with uow:
        assignment_repo = uow.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment)
        assignment_id = project_assignment.AssignmentPrimaryKey(userId=event.user_id, projectId=event.program_id)

        if assignment := assignment_repo.get(assignment_id):
            assignment.roles = event.roles
            assignment.userEmail = event.user_email
            assignment_repo.update_entity(assignment_id, assignment)
        else:
            assignment_repo.add(
                project_assignment.Assignment(
                    userId=event.user_id,
                    projectId=event.program_id,
                    roles=event.roles,
                    userEmail=event.user_email,
                    groupMemberships=event.groupMemberships,
                )
            )
        uow.commit()
