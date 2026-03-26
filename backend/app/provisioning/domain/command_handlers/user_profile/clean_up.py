import logging

from app.provisioning.domain.aggregates import user_profile_aggragate
from app.provisioning.domain.commands.user_profile import cleanup_user_profile_command
from app.provisioning.domain.model import user_profile
from app.provisioning.domain.ports import maintenance_windows_query_service, projects_query_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.ddd import aggregate


def handle(
    command: cleanup_user_profile_command.CleanUpUserProfileCommand,
    publisher: aggregate.AggregatePublisher,
    uow: unit_of_work.UnitOfWork,
    maintenance_windows_qry_srv: maintenance_windows_query_service.MaintenanceWindowsQueryService,
    projects_qry_srv: projects_query_service.ProjectsQueryService,
    logger: logging.Logger,
):
    with uow:
        user_profile_entity = uow.get_repository(user_profile.UserProfilePrimaryKey, user_profile.UserProfile).get(
            pk=user_profile.UserProfilePrimaryKey(
                userId=command.user_id.value,
            ),
        )
    maintenance_windows = maintenance_windows_qry_srv.get_maintenance_windows_by_user_id(user_id=command.user_id.value)

    user_profile_agg = user_profile_aggragate.UserProfileAggregate(
        logger=logger, user_profile_entity=user_profile_entity, maintenance_windows=maintenance_windows
    )

    user_profile_agg.cleanup(command=command, projects_qry_srv=projects_qry_srv)

    publisher.publish(user_profile_agg)
