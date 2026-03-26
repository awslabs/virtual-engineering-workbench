from unittest import mock

import pytest

from app.publishing.domain.command_handlers import validate_version_command_handler
from app.publishing.domain.commands import validate_version_command
from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.ports import iac_service
from app.publishing.domain.value_objects import (
    product_id_value_object,
    project_id_value_object,
    version_template_definition_value_object,
)


@pytest.fixture
def stack_service_mock():
    stack_srv_mock = mock.create_autospec(spec=iac_service.IACService)
    return stack_srv_mock


def test_handle_should_raise_exception_when_template_is_invalid(stack_service_mock):
    # ARRANGE
    stack_service_mock.validate_template.return_value = False, None, "Error Message Text"
    command = validate_version_command.ValidateVersionCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        productId=product_id_value_object.from_str("prod-11111111"),
        versionTemplateDefinition=version_template_definition_value_object.from_str("invalid-template"),
    )

    # ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        validate_version_command_handler.handle(
            command=command,
            stack_srv=stack_service_mock,
        )

    assert str(e.value) == "The template is invalid: Error Message Text"
    stack_service_mock.validate_template.assert_called_once_with(template_body="invalid-template")


def test_handle_should_not_raise_exception_when_template_is_valid(stack_service_mock):
    # ARRANGE
    stack_service_mock.validate_template.return_value = True, None, None
    command = validate_version_command.ValidateVersionCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        productId=product_id_value_object.from_str("prod-11111111"),
        versionTemplateDefinition=version_template_definition_value_object.from_str("valid-template"),
    )

    # ACT
    validate_version_command_handler.handle(
        command=command,
        stack_srv=stack_service_mock,
    )

    # ASSERT
    stack_service_mock.validate_template.assert_called_once_with(template_body="valid-template")
