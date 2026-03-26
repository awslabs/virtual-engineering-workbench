from datetime import datetime, timezone

from app.packaging.domain.commands.component import update_component_command
from app.packaging.domain.model.component import component
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: update_component_command.UpdateComponentCommand,
    uow: unit_of_work.UnitOfWork,
):
    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        component_repo = uow.get_repository(component.ComponentPrimaryKey, component.Component)
        component_primary_key = component.ComponentPrimaryKey(componentId=command.componentId.value)
        component_entity = component_repo.get(component_primary_key)

        if not component_entity:
            raise ValueError(f"Component {command.componentId.value} not found")

        component_entity.componentDescription = command.componentDescription.value
        component_entity.lastUpdateDate = current_time
        component_entity.lastUpdatedBy = command.lastUpdatedBy.value

        component_repo.update_entity(
            component.ComponentPrimaryKey(
                componentId=component_entity.componentId,
            ),
            component_entity,
        )
        uow.commit()
