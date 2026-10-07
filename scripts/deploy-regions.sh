#!/usr/bin/env bash

normalize_workbench_regions() {
  local raw_regions="$1"
  local candidate
  local region
  local normalized=""
  local remaining="${raw_regions},"

  while [[ -n "$remaining" ]]; do
    candidate="${remaining%%,*}"
    remaining="${remaining#*,}"
    region="${candidate#"${candidate%%[![:space:]]*}"}"
    region="${region%"${region##*[![:space:]]}"}"

    if [[ ! "$region" =~ ^[a-z]{2}(-[a-z0-9]+)+-[0-9]+$ ]]; then
      echo "Invalid AWS region in ENABLED_WORKBENCH_REGIONS: ${region:-<empty>}" >&2
      return 1
    fi

    case ",$normalized," in
      *",$region,"*) ;;
      *) normalized="${normalized:+$normalized,}$region" ;;
    esac
  done

  printf '%s\n' "$normalized"
}

workbench_regions_python_list() {
  local normalized_regions
  local region
  local separator=""
  local -a regions

  normalized_regions=$(normalize_workbench_regions "$1") || return 1
  IFS=',' read -r -a regions <<< "$normalized_regions"

  printf '['
  for region in "${regions[@]}"; do
    printf '%s"%s"' "$separator" "$region"
    separator=", "
  done
  printf ']\n'
}

workbench_regions_lines() {
  local normalized_regions
  normalized_regions=$(normalize_workbench_regions "$1") || return 1
  printf '%s\n' "$normalized_regions" | tr ',' '\n'
}

required_bootstrap_regions() {
  local primary_region="$1"
  local workbench_regions="$2"
  local private_deployment="$3"
  local regions="$primary_region,$workbench_regions"

  if [ "$private_deployment" != "true" ]; then
    regions="$regions,us-east-1"
  fi

  normalize_workbench_regions "$regions"
}

patch_workbench_regions_config() {
  local config_path="$1"
  local python_regions

  python_regions=$(workbench_regions_python_list "$2") || return 1
  sed -i.bak \
    -e "s/\"enabled-workbench-regions\": \[[^]]*\]/\"enabled-workbench-regions\": ${python_regions}/" \
    "$config_path"
  rm -f "${config_path}.bak"
}
