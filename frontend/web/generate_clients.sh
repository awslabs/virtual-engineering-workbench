#!/usr/bin/env sh
# Generate TypeScript API clients from local backend OpenAPI schemas.
#
# Usage:
#   ./generate_clients.sh [api_name]
#
# If api_name is provided, only that client is regenerated.
# If omitted, all clients are regenerated.
#
# Examples:
#   ./generate_clients.sh                              # regenerate all
#   ./generate_clients.sh proserve-wb-provisioning-api # regenerate one
#
# Required dependency: openapi-generator-cli (via npx)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="${SCRIPT_DIR}/../../backend"

echo_info() {
  printf '\033[0;32m%s\033[0m\n' "$1"
}

echo_fail() {
  printf '\033[0;31m%s\033[0m\n' "$1"
}

# Client definitions: "api_name|backend_schema_relative_path"
CLIENTS="proserve-wb-projects-api|app/projects/entrypoints/api/schema/proserve-workbench-projects-api-schema.yaml
proserve-wb-packaging-api|app/packaging/entrypoints/api/schema/proserve-workbench-packaging-api-schema.yaml
proserve-wb-publishing-api|app/publishing/entrypoints/api/schema/proserve-workbench-publishing-api-schema.yaml
proserve-wb-provisioning-api|app/provisioning/entrypoints/api/schema/proserve-workbench-provisioning-api-schema.yaml"

get_schema_path() {
  echo "$CLIENTS" | while IFS='|' read -r name path; do
    if [ "$name" = "$1" ]; then
      echo "$path"
    fi
  done
}

generate_client() {
  api_name=$1
  schema_rel_path=$(get_schema_path "$api_name")

  if [ -z "$schema_rel_path" ]; then
    echo_fail "Unknown API client: $api_name"
    echo_fail "Available clients:"
    echo "$CLIENTS" | while IFS='|' read -r name path; do
      echo_fail "  $name"
    done
    exit 1
  fi

  schema_path="${BACKEND_DIR}/${schema_rel_path}"
  spec_output_path="src/services/api-src/${api_name}.json"
  sdk_output_path="src/services/API/${api_name}"

  if [ ! -f "$schema_path" ]; then
    echo_fail "Schema not found: $schema_path"
    exit 1
  fi

  mkdir -p "$(dirname "$spec_output_path")"

  echo_info "[$api_name] Copying schema to: $spec_output_path"
  cp "$schema_path" "$spec_output_path"

  echo_info "[$api_name] Generating SDK: $sdk_output_path"
  npx openapi-generator-cli generate \
    -i "$schema_path" \
    -g typescript-fetch \
    -o "$sdk_output_path" \
    --additional-properties=supportsES6=true

  echo_info "[$api_name] Done"
}

cd "$SCRIPT_DIR"

if [ -n "$1" ]; then
  generate_client "$1"
else
  echo_info "Regenerating all API clients from local backend schemas..."
  echo "$CLIENTS" | while IFS='|' read -r name path; do
    generate_client "$name"
  done
  echo_info "All clients regenerated."
fi
