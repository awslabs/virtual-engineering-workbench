#!/usr/bin/env bash
# =============================================================================
# Compile per-context Lambda requirements into pinned + hashed lockfiles.
#
# Usage: bash scripts/compile.sh [--upgrade]
#
# Each requirements.in (human-edited, ~= specifiers) produces a
# requirements.txt (fully pinned with hashes) consumed by CDK bundling.
# Dependabot's uv ecosystem pairs the two files by this naming.
# =============================================================================
set -euo pipefail

if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first."
    exit 1
fi

PYTHON_VERSION="3.13"

REQUIREMENTS_FILES=(
    app/shared/requirements.in
    app/authorization/libraries/requirements.in
    app/packaging/libraries/requirements.in
    app/projects/libraries/requirements.in
    app/provisioning/libraries/requirements.in
    app/publishing/libraries/requirements.in
    app/usecase/libraries/requirements.in
    infra/constructs/eventbridge/eb_upsert_handler/requirements.in
    infra/constructs/ssm/handler/requirements.in
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
    lockfile="${req%.in}.txt"
    echo "Compiling $req → $lockfile"
    uv pip compile "$req" \
        --python-version "$PYTHON_VERSION" \
        --generate-hashes \
        ${UPGRADE_FLAG} \
        -o "$lockfile" \
        --quiet
done

echo "Done. All lockfiles generated."
