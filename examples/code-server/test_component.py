from pathlib import Path

import yaml


COMPONENT_PATH = Path(__file__).with_name("component.yaml")


def load_component() -> dict:
    return yaml.safe_load(COMPONENT_PATH.read_text())


def commands_for(component: dict, phase_name: str) -> str:
    phase = next(phase for phase in component["phases"] if phase["name"] == phase_name)
    return "\n".join(
        command
        for step in phase["steps"]
        for command in step["inputs"]["commands"]
    )


def test_component_uses_the_image_builder_schema() -> None:
    component = load_component()

    assert component["schemaVersion"] == 1.0
    assert [phase["name"] for phase in component["phases"]] == ["build", "validate"]


def test_every_execute_bash_command_is_a_string() -> None:
    component = load_component()

    commands = [
        command
        for phase in component["phases"]
        for step in phase["steps"]
        if step["action"] == "ExecuteBash"
        for command in step["inputs"]["commands"]
    ]

    assert all(isinstance(command, str) for command in commands)


def test_component_installs_a_pinned_code_server_release() -> None:
    build_commands = commands_for(load_component(), "build")

    assert "--version=4.133.0" in build_commands
    assert "systemctl enable code-server.service" in build_commands


def test_installer_has_a_home_directory_in_the_awstoe_environment() -> None:
    build_commands = commands_for(load_component(), "build")

    assert "HOME=/root sh /tmp/install-code-server.sh" in build_commands


def test_component_keeps_the_unauthenticated_server_on_loopback() -> None:
    build_commands = commands_for(load_component(), "build")

    assert "bind-addr: 127.0.0.1:8080" in build_commands
    assert "auth: none" in build_commands
    assert "User=ubuntu" in build_commands
