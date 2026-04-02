#!/usr/bin/env bash
# =============================================================================
# Compile per-context Lambda requirements into pinned + hashed lockfiles.
#
# Usage: bash scripts/compile.sh [--upgrade]
#
# Each requirements.txt (human-edited, ~= specifiers) produces a
# requirements.lock (fully pinned with hashes) consumed by CDK bundling.
# =============================================================================
set -euo pipefail

if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first."
    exit 1
fi

PYTHON_VERSION="3.13"

REQUIREMENTS_FILES=(
    app/shared/requirements.txt
    app/authorization/libraries/requirements.txt
    app/packaging/libraries/requirements.txt
    app/projects/libraries/requirements.txt
    app/provisioning/libraries/requirements.txt
    app/publishing/libraries/requirements.txt
    app/usecase/libraries/requirements.txt
    infra/constructs/eventbridge/eb_upsert_handler/requirements.txt
    infra/constructs/ssm/handler/requirements.txt
)

UPGRADE_FLAG=""
for arg in "$@"; do
    case "$arg" in
        --upgrade) UPGRADE_FLAG="--upgrade" ;;
    esac
done

for req in "${REQUIREMENTS_FILES[@]}"; do
    if [[ ! -s "$req" ]]; then
        echo "Skipping empty: $req"
        continue
    fi
    lockfile="${req%.txt}.lock"
    echo "Compiling $req → $lockfile"
    uv pip compile "$req" \
        --python-version "$PYTHON_VERSION" \
        --generate-hashes \
        ${UPGRADE_FLAG} \
        -o "$lockfile" \
        --quiet
done

echo "Done. All lockfiles generated."
