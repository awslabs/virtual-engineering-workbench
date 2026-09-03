from pathlib import Path

import yaml


COMPONENT_PATH = Path(__file__).with_name("component.yaml")


def load_component() -> dict:
    return yaml.safe_load(COMPONENT_PATH.read_text(encoding="utf-8"))


def commands_for(phase_name: str) -> str:
    phase = next(phase for phase in load_component()["phases"] if phase["name"] == phase_name)
    return "\n".join(
        command
        for step in phase["steps"]
        for command in step["inputs"]["commands"]
    )


def test_component_uses_the_image_builder_schema() -> None:
    component = load_component()

    assert component["schemaVersion"] == 1.0
    assert [phase["name"] for phase in component["phases"]] == ["build", "validate"]


def test_component_supports_ubuntu_22_and_24_on_x86_64() -> None:
    build = commands_for("build")

    assert 'test "$ID" = "ubuntu"' in build
    assert '"22.04"|"24.04"' in build
    assert 'test "$(uname -m)" = "x86_64"' in build


def test_component_installs_a_verified_aws_cli_v2_release() -> None:
    build = commands_for("build")

    assert "awscli-exe-linux-x86_64-2.36.38.zip" in build
    assert "1056bc30b892f4a80e65b05eac856fbf175d0c5aeda051d782450d2218db6657" in build
    assert "sha256sum -c -" in build
    assert "./aws/install --bin-dir /usr/local/bin --install-dir /usr/local/aws-cli" in build


def test_component_validates_the_installed_version() -> None:
    validate = commands_for("validate")

    assert "/usr/local/bin/aws --version" in validate
    assert "aws-cli/2.36.38" in validate
