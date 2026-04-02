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
