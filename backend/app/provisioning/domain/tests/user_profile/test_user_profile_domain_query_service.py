import assertpy

from app.provisioning.domain.query_services import user_profile_domain_query_service
from app.provisioning.domain.value_objects import start_hour_value_object, user_id_value_object, week_day_value_object
from app.shared.adapters.feature_toggling import frontend_feature


def test_get_user_configuration_returns_all_information(
    mock_unit_of_work,
    mock_maintenance_windows_qs,
    mock_parameter_srv,
    mock_feature_toggles,
    get_test_user_profile,
):
    # ARRANGE
    user_profile_domain_qry_srv = user_profile_domain_query_service.UserProfileDomainQueryService(
        uow=mock_unit_of_work,
        parameter_srv=mock_parameter_srv,
        maintenance_windows_qry_srv=mock_maintenance_windows_qs,
        feature_toggles=mock_feature_toggles,
        enabled_regions_param_name="enabled-regions-param",
        application_version_param_name="3.12",
    )
    test_user_profile = get_test_user_profile()

    # ACT
    (
        profile,
        enabled_regions,
        features,
        application_version,
    ) = user_profile_domain_qry_srv.get_user_configuration(user_id=user_id_value_object.from_str("T0011AA"))

    # ASSERT
    assertpy.assert_that(profile).is_equal_to(test_user_profile)
    assertpy.assert_that(enabled_regions).contains_only("us-east-1", "eu-west-3")
    assertpy.assert_that(features).contains_only(
        frontend_feature.FrontendFeature(
            version="v0.0.0",
            feature="EnabledFeature",
            enabled=True,
        )
    )
    assertpy.assert_that(application_version).is_equal_to("3.12")


def test_get_users_within_maintenance_window_return_users_ids_within_maintenance_window(
    mock_unit_of_work,
    mock_maintenance_windows_qs,
    mock_parameter_srv,
    mock_feature_toggles,
    get_test_maintenance_window,
):
    # ARRANGE
    user_profile_domain_qry_srv = user_profile_domain_query_service.UserProfileDomainQueryService(
        uow=mock_unit_of_work,
        parameter_srv=mock_parameter_srv,
        maintenance_windows_qry_srv=mock_maintenance_windows_qs,
        feature_toggles=mock_feature_toggles,
        enabled_regions_param_name="enabled-regions-param",
        application_version_param_name="app-version-param",
    )
    mock_maintenance_windows_qs.get_maintenance_windows_by_time.return_value = [
        get_test_maintenance_window("T0011AA"),
        get_test_maintenance_window("T0011AB"),
        get_test_maintenance_window("T0011AC"),
    ]

    # ACT
    user_ids = user_profile_domain_qry_srv.get_users_within_maintenance_window(
        day=week_day_value_object.from_str("MONDAY"), start_hour=start_hour_value_object.from_str("2")
    )

    # ASSERT
    assertpy.assert_that(user_ids).is_length(3)
