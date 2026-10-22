from unittest import mock

from app.packaging.entrypoints.s2s_api import bootstrapper, config


def test_bootstrapper_wires_access_commands_and_component_queries(monkeypatch):
    session = mock.Mock()
    monkeypatch.setattr(bootstrapper.boto_logger, "loggable_session", mock.Mock(return_value=session))
    monkeypatch.setattr(bootstrapper.parameters, "get_parameter", mock.Mock(return_value="{}"))

    result = bootstrapper.bootstrap(config.AppConfig(), mock.Mock())

    assert result.project_access_service is not None
    assert result.component_domain_qry_srv is not None
    assert result.component_version_domain_qry_srv is not None
    assert result.component_version_qry_srv is not None
    assert result.recipe_domain_qry_srv is not None
    assert result.recipe_version_domain_qry_srv is not None
    session.client.assert_any_call("ssm", region_name="eu-west-1")
