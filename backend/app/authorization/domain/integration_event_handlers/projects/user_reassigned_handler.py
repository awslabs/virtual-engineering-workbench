from app.authorization.domain.integration_events.projects import user_reassigned
from app.authorization.domain.read_models import project_assignment
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(event: user_reassigned.UserReAssigned, uow: unit_of_work.UnitOfWork):
    with uow:
        assignment_repo = uow.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment)
        asignment_id = project_assignment.AssignmentPrimaryKey(userId=event.userId, projectId=event.projectId)

        if assignment := assignment_repo.get(asignment_id):
            assignment.roles = event.roles
            assignment.groupMemberships = event.groupMemberships
            assignment_repo.update_entity(asignment_id, assignment)
        else:
            assignment_repo.add(
                project_assignment.Assignment(
                    userId=event.userId,
                    projectId=event.projectId,
                    roles=event.roles,
                    groupMemberships=event.groupMemberships,
                )
            )
        uow.commit()
