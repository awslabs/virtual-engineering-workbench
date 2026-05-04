import assertpy
import pytest

from app.publishing.domain.exceptions import domain_exception
from app.publishing.domain.value_objects import version_template_definition_value_object


def test_from_str_should_return_value_object_for_valid_template():
    # ARRANGE & ACT
    result = version_template_definition_value_object.from_str("AWSTemplateFormatVersion: '2010-09-09'")

    # ASSERT
    assertpy.assert_that(result.value).is_equal_to("AWSTemplateFormatVersion: '2010-09-09'")


def test_from_str_should_raise_when_empty():
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as e:
        version_template_definition_value_object.from_str("")

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Version template definition cannot be empty.")


def test_from_str_should_raise_when_none():
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as e:
        version_template_definition_value_object.from_str(None)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Version template definition cannot be empty.")


@pytest.mark.parametrize(
    "payload",
    [
        "{{ config.__class__.__init__.__globals__['os'].popen('id').read() }}",
        "{% import 'os' %}{% print os.popen('id').read() %}",
        "{# malicious comment with code #}",
        "Description: {{ self._TemplateReference__context }}",
        "normal text {{ bad }} more text",
        "start {%block%} end",
    ],
)
def test_from_str_should_reject_jinja2_control_sequences(payload):
    # ARRANGE & ACT
    with pytest.raises(domain_exception.DomainException) as e:
        version_template_definition_value_object.from_str(payload)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        "Version template definition must not contain Jinja2 control sequences ({{, {%, {#)."
    )
