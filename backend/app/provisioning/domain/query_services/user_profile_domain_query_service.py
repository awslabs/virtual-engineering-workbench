from app.provisioning.domain.model import user_profile
from app.provisioning.domain.ports import maintenance_windows_query_service
from app.provisioning.domain.value_objects import start_hour_value_object, user_id_value_object, week_day_value_object
from app.shared.adapters.feature_toggling import frontend_feature, frontend_feature_toggles
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.api import parameter_service


class UserProfileDomainQueryService:
    def __init__(
        self,
        uow: unit_of_work.UnitOfWork,
        parameter_srv: parameter_service.ParameterService,
        maintenance_windows_qry_srv: maintenance_windows_query_service.MaintenanceWindowsQueryService,
        feature_toggles: frontend_feature_toggles.FrontendFeatureToggles,
        enabled_regions_param_name: str,
        application_version_param_name: str,
    ):
        self._uow = uow
        self._parameter_srv = parameter_srv
        self._feature_toggles = feature_toggles
        self._maintenance_windows_qry_srv = maintenance_windows_qry_srv
        self._enabled_regions_param_name = enabled_regions_param_name
        self._application_version_param_name = application_version_param_name

    def get_user_configuration(
        self, user_id: user_id_value_object.UserIdValueObject
    ) -> tuple[user_profile.UserProfile | None, list[str], list[frontend_feature.FrontendFeature], str]:
        with self._uow:
            profile = self._uow.get_repository(user_profile.UserProfilePrimaryKey, user_profile.UserProfile).get(
                pk=user_profile.UserProfilePrimaryKey(
                    userId=user_id.value,
                ),
            )

        enabled_regions = self._parameter_srv.get_list_parameter_value(parameter_name=self._enabled_regions_param_name)

        enabled_features = self._feature_toggles.get_enabled_features_for_user(user_id=user_id.value)

        application_version = self._parameter_srv.get_parameter_value(
            parameter_name=self._application_version_param_name
        )

        return (profile, enabled_regions, enabled_features, application_version)

    def get_users_within_maintenance_window(
        self,
        day: week_day_value_object.WeekDayValueObject,
        start_hour: start_hour_value_object.StartHourValueObject,
    ) -> list[str]:
        maintenance_windows = self._maintenance_windows_qry_srv.get_maintenance_windows_by_time(
            day=day.value, start_hour=start_hour.value
        )
        return list({maintenance_window.userId for maintenance_window in maintenance_windows})
