import logging
from unittest import mock

import pytest

from app.provisioning.domain.model import maintenance_window, user_profile
from app.provisioning.domain.ports import (
    maintenance_windows_query_service,
    projects_query_service,
)
from app.shared.adapters.feature_toggling import (
    frontend_feature,
    frontend_feature_toggles,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.api import parameter_service
from app.shared.ddd import aggregate


@pytest.fixture()
def mock_logger():
    return mock.create_autospec(spec=logging.Logger)


@pytest.fixture()
def mock_message_bus():
    return mock.create_autospec(spec=message_bus.MessageBus)


@pytest.fixture()
def mock_user_profile_repo(get_test_user_profile):
    user_profile_repo = mock.create_autospec(spec=unit_of_work.GenericRepository)
    user_profile_repo.get.return_value = get_test_user_profile()
    return user_profile_repo


@pytest.fixture()
def mock_maintenance_window_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository)


@pytest.fixture()
def mock_unit_of_work(mock_user_profile_repo, mock_maintenance_window_repo):
    repo_dict = {
        user_profile.UserProfile: mock_user_profile_repo,
        maintenance_window.MaintenanceWindow: mock_maintenance_window_repo,
    }

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk_param, entity_param: repo_dict.get(entity_param)
    return uow_mock


@pytest.fixture()
def mock_publisher(mock_message_bus, mock_unit_of_work):
    return aggregate.AggregatePublisher(
        mb=mock_message_bus,
        uow=mock_unit_of_work,
    )


@pytest.fixture()
def get_test_user_profile():
    def _inner(
        user_id: str = "T0011AA",
        preferred_region: str = "us-east-1",
    ):
        return user_profile.UserProfile(
            userId=user_id,
            preferredRegion=preferred_region,
            preferredNetwork="x",
            preferredMaintenanceWindows=[
                maintenance_window.MaintenanceWindow(
                    day=maintenance_window.WeekDay.MONDAY,
                    startTime="00:00",
                    endTime="04:00",
                    userId=user_id,
                )
            ],
            createDate="2024-01-18T00:00:00+00:00",
            lastUpdateDate="2024-01-18T00:00:00+00:00",
        )

    return _inner


@pytest.fixture()
def get_test_maintenance_window():
    def _inner(
        user_id: str = "T0011AA",
    ):
        return maintenance_window.MaintenanceWindow(
            day=maintenance_window.WeekDay.MONDAY,
            startTime="00:00",
            endTime="04:00",
            userId=user_id,
        )

    return _inner


@pytest.fixture()
def mock_maintenance_windows_qs(get_test_maintenance_window):
    mw_qs = mock.create_autospec(spec=maintenance_windows_query_service.MaintenanceWindowsQueryService)
    mw_qs.get_maintenance_windows_by_user_id.return_value = [get_test_maintenance_window()]
    mw_qs.get_maintenance_windows_by_time.return_value = [get_test_maintenance_window()]
    return mw_qs


@pytest.fixture
def mock_parameter_srv():
    parameter_srv = mock.create_autospec(spec=parameter_service.ParameterService)
    parameter_srv.get_parameter_value.return_value = "3.12"
    parameter_srv.get_list_parameter_value.return_value = ["us-east-1", "eu-west-3"]
    return parameter_srv


@pytest.fixture
def mock_feature_toggles():
    ft = mock.create_autospec(spec=frontend_feature_toggles.FrontendFeatureToggles)
    ft.get_enabled_features_for_user.return_value = [
        frontend_feature.FrontendFeature(
            version="v0.0.0",
            feature="EnabledFeature",
            enabled=True,
        )
    ]
    return ft


@pytest.fixture
def mock_projects_qs():
    projects_qs = mock.create_autospec(spec=projects_query_service.ProjectsQueryService)
    projects_qs.get_user_assignments_count.return_value = 0
    return projects_qs
