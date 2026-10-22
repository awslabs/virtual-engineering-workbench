"""Local bundling must build for the Lambda runtime, not for the deploy host's Python.

The deployer image (root Dockerfile) bundles Lambdas locally with `uv pip install -t`. If its
base Python differs from the Lambda runtime, native wheels (pydantic-core, cryptography) are
built for the wrong interpreter and every Lambda fails at import.
"""

from unittest import mock

import pytest
from aws_cdk import aws_lambda

from infra import constants
from infra.constructs import backend_app_function, shared_layer
from infra.constructs.bundling import uv_target_args


@pytest.mark.parametrize(
    "architecture,platform",
    [
        (aws_lambda.Architecture.ARM_64, "aarch64-manylinux_2_28"),
        (aws_lambda.Architecture.X86_64, "x86_64-manylinux_2_28"),
    ],
)
def test_uv_target_args_follow_runtime_and_architecture(architecture, platform):
    assert uv_target_args(aws_lambda.Runtime.PYTHON_3_13.name, architecture.name) == [
        "--python-version",
        "3.13",
        "--python-platform",
        platform,
    ]


def test_uv_target_args_reject_non_python_runtimes():
    with pytest.raises(ValueError):
        uv_target_args(aws_lambda.Runtime.NODEJS_22_X.name, "arm64")


def _uv_call(run):
    return next(c.args[0] for c in run.call_args_list if c.args[0][:3] == ["uv", "pip", "install"])


def test_function_local_bundler_pins_runtime_python(tmp_path, monkeypatch):
    lambda_root = tmp_path / "app" / "fn"
    lambda_root.mkdir(parents=True)
    (lambda_root / "requirements.txt").write_text("pydantic\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(constants, "LOCAL_BUNDLING", True)
    bundler = backend_app_function.LocalBundler(
        app_root="app",
        lambda_root="app/fn",
        runtime=aws_lambda.Runtime.PYTHON_3_13,
        architecture=aws_lambda.Architecture.ARM_64,
    )

    with mock.patch.object(backend_app_function.subprocess, "run") as run:
        assert bundler.try_bundle(str(tmp_path / "out"), mock.Mock()) is True

    assert _uv_call(run)[-4:] == ["--python-version", "3.13", "--python-platform", "aarch64-manylinux_2_28"]


def test_shared_layer_local_bundler_pins_runtime_python(tmp_path, monkeypatch):
    (tmp_path / "shared").mkdir()
    (tmp_path / "shared" / "requirements.txt").write_text("pydantic\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(constants, "LOCAL_BUNDLING", True)
    bundler = shared_layer.MyLocalBundler(
        entry="shared",
        runtime=aws_lambda.Runtime.PYTHON_3_13,
        architecture=aws_lambda.Architecture.X86_64,
    )

    with mock.patch.object(shared_layer.subprocess, "run") as run:
        assert bundler.try_bundle(str(tmp_path / "out"), mock.Mock()) is True

    assert _uv_call(run)[-4:] == ["--python-version", "3.13", "--python-platform", "x86_64-manylinux_2_28"]
