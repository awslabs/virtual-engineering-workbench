import shutil
from pathlib import Path

DOCKER_STRIP_CMD = (
    'find /asset-output -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null;'
    ' find /asset-output -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null;'
    ' find /asset-output -name "*.pyc" -delete 2>/dev/null;'
    " true"
)


def strip_bundle(root: Path) -> None:
    for pattern in ("__pycache__", "*.dist-info"):
        for d in list(root.rglob(pattern)):
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)

    for f in root.rglob("*.pyc"):
        f.unlink(missing_ok=True)


# Lambda Python runtimes run on Amazon Linux 2023 (glibc 2.34), so manylinux_2_28 wheels are safe.
_PLATFORM_BY_ARCHITECTURE = {
    "arm64": "aarch64-manylinux_2_28",
    "x86_64": "x86_64-manylinux_2_28",
}


def uv_target_args(runtime_name: str, architecture_name: str) -> list[str]:
    """uv flags that build for the Lambda runtime instead of the host Python.

    Local bundling runs `uv pip install -t` on the deploy host (e.g. inside the deployer image).
    Without these flags uv picks wheels for whatever Python that host has, and a cp315 native
    module (pydantic-core, cryptography, ...) cannot be imported by a python3.13 Lambda.
    """
    if not runtime_name.startswith("python"):
        raise ValueError(f"Not a Python Lambda runtime: {runtime_name}")
    if architecture_name not in _PLATFORM_BY_ARCHITECTURE:
        raise ValueError(f"Unsupported Lambda architecture: {architecture_name}")
    return [
        "--python-version",
        runtime_name.removeprefix("python"),
        "--python-platform",
        _PLATFORM_BY_ARCHITECTURE[architecture_name],
    ]
