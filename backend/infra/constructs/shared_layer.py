import subprocess
from pathlib import Path

import aws_cdk
import constructs
from aws_cdk import aws_lambda
from jsii import implements, member

from infra import constants
from infra.constructs.bundling import DOCKER_STRIP_CMD, strip_bundle


def _validate_path(path: str) -> None:
    if ".." in Path(path).parts:
        raise ValueError(f"Path traversal detected: {path}")


def _resolve_requirements(entry: str) -> str:
    """Return the lockfile path if it exists, otherwise the requirements.txt path."""
    lockfile = f"{entry}/requirements.lock"
    return lockfile if Path(lockfile).is_file() else f"{entry}/requirements.txt"


@implements(aws_cdk.ILocalBundling)
class MyLocalBundler:
    def __init__(self, entry: str) -> None:
        _validate_path(entry)
        self._entry = entry

    @member(jsii_name="tryBundle")
    def try_bundle(self, output_dir: str, options: aws_cdk.BundlingOptions) -> bool:
        if not constants.LOCAL_BUNDLING:
            return False

        python_dir = Path(output_dir) / "python"
        entry_dir = python_dir / self._entry
        reqfile = _resolve_requirements(self._entry)

        try:
            subprocess.run(
                ["uv", "pip", "install", "-r", reqfile, "-t", str(python_dir), "--no-compile"],
                check=True,
                shell=False,
                capture_output=True,
                timeout=300,
            )

            entry_dir.mkdir(parents=True, exist_ok=True)

            subprocess.run(
                ["rsync", "-r", f"{self._entry}/", str(entry_dir)],
                check=True,
                shell=False,
                capture_output=True,
                timeout=60,
            )

            strip_bundle(Path(output_dir))
        except subprocess.CalledProcessError as e:
            print(f"Bundle command failed: {e.stderr if e.stderr else ''}")
            return False
        except subprocess.TimeoutExpired:
            print("Bundle command timed out")
            return False

        return True


class SharedLayer(constructs.Construct):
    def __init__(
        self,
        scope: constructs.Construct,
        construct_id: str,
        entry: str,
        layer_version_name: str,
        runtime: aws_lambda.Runtime = aws_lambda.Runtime.PYTHON_3_13,
    ) -> None:
        super().__init__(scope, construct_id)

        _validate_path(entry)

        hash_path = entry
        if not hash_path.startswith("./"):
            hash_path = f"./{hash_path}"

        asset_hash = aws_cdk.FileSystem.fingerprint(
            hash_path,
            exclude=[
                "**/__pycache__",
                "**/__pycache__/**",
                "**/*.pyc",
            ],
        )

        current_dir = "."
        reqfile = _resolve_requirements(entry)
        code = aws_lambda.Code.from_asset(
            path=current_dir,
            bundling=aws_cdk.BundlingOptions(
                image=runtime.bundling_image,
                user="root",
                command=[
                    "bash",
                    "-c",
                    "curl -LsSf https://astral.sh/uv/0.11.3/install.sh | sh"
                    f" && /root/.local/bin/uv pip install --no-compile -r {reqfile} -t /asset-output/python/"
                    f" && mkdir -p /asset-output/python/{entry}"
                    f" && rsync -r {entry}/ /asset-output/python/{entry}"
                    f" && {DOCKER_STRIP_CMD}",
                ],
                local=MyLocalBundler(
                    entry=entry,
                ),
            ),
            asset_hash=asset_hash,
            asset_hash_type=aws_cdk.AssetHashType.CUSTOM,
        )

        self._layer = aws_lambda.LayerVersion(
            self,
            "SharedLayer",
            code=code,
            compatible_runtimes=[runtime],
            layer_version_name=layer_version_name,
            compatible_architectures=[constants.LAMBDA_ARCHITECTURE],
        )

    @property
    def layer(self):
        return self._layer
