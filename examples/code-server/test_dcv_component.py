from pathlib import Path

import yaml


COMPONENT_PATH = Path(__file__).with_name("dcv-ubuntu-2404-component.yaml")


def load_component() -> dict:
    return yaml.safe_load(COMPONENT_PATH.read_text(encoding="utf-8"))


def commands_for(phase_name: str) -> str:
    phase = next(phase for phase in load_component()["phases"] if phase["name"] == phase_name)
    return "\n".join(
        command
        for step in phase["steps"]
        for command in step["inputs"]["commands"]
    )


def test_component_uses_awstoe_schema() -> None:
    component = load_component()

    assert component["schemaVersion"] == 1.0
    assert [phase["name"] for phase in component["phases"]] == ["build", "validate"]


def test_component_rejects_unsupported_images() -> None:
    build = commands_for("build")

    assert 'test "$ID" = "ubuntu"' in build
    assert 'test "$VERSION_ID" = "24.04"' in build
    assert 'test "$(uname -m)" = "x86_64"' in build


def test_component_verifies_pinned_dcv_archive() -> None:
    build = commands_for("build")

    assert "2025.0/Servers/nice-dcv-2025.0-20103-ubuntu2404-x86_64.tgz" in build
    assert "a39374d39f2d849bd13ee101970bb9eea15a8c5ec743799b7cbb7f562ece9e17" in build
    assert "sha256sum -c -" in build


def test_component_installs_minimal_gnome_desktop_and_web_viewer() -> None:
    build = commands_for("build")

    assert "gdm3" in build
    assert "gnome-session" in build
    assert "xserver-xorg-video-dummy" in build
    assert "nice-dcv-server_2025.0.20103-1_amd64.ubuntu2404.deb" in build
    assert "nice-dcv-web-viewer_2025.0.20103-1_amd64.ubuntu2404.deb" in build
    assert "WaylandEnable=false" in build
    assert 'Driver "dummy"' in build


def test_component_does_not_install_or_validate_aws_cli() -> None:
    component_commands = commands_for("build") + commands_for("validate")

    assert "awscli" not in component_commands.lower()
    assert "/usr/local/bin/aws" not in component_commands


def test_component_requires_pam_and_owner_only_console_session() -> None:
    build = commands_for("build")

    assert 'authentication="system"' in build
    assert 'authentication="none"' not in build
    assert "create-session=true" in build
    assert 'owner="ubuntu"' in build
    assert "systemctl enable gdm3.service dcvserver.service" in build


def test_component_validates_listener_and_console_session() -> None:
    validate = commands_for("validate")

    assert "dpkg-query" in validate
    assert "systemctl is-enabled" in validate
    assert "ss -lnt" in validate
    assert "8443" in validate
    assert "dcv list-sessions" in validate
    assert "journalctl -u dcvserver.service" in validate
