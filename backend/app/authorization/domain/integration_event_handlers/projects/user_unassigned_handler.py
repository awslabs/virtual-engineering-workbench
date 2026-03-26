from app.authorization.domain.integration_events.projects import user_unassigned
from app.authorization.domain.read_models import project_assignment
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(event: user_unassigned.UserUnAssigned, uow: unit_of_work.UnitOfWork):
    with uow:
        uow.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).remove(
            project_assignment.AssignmentPrimaryKey(userId=event.userId, projectId=event.projectId)
        )
        uow.commit()
