#!/bin/bash

set -x
set -e

echo_info() {
  GREEN='\033[0;32m'
  NC='\033[0m'
  echo -e "${GREEN}$1${NC}"
}

echo_fail() {
  GREEN='\033[0;31m'
  NC='\033[0m'
  echo -e "${GREEN}$1${NC}"
}

fail_if_empty () {
  [ -z $1 ] && echo_fail "$2" && exit 1
  return 0
}

app_name=${1:-$APP_NAME}
backend_app_name=${2:-$BACKEND_APP_NAME}
environment_name=${3:-$ENVIRONMENT_NAME}
region=${4:-$AWS_DEFAULT_REGION}
api_region=${5:-$AWS_REGION_BE_API}

fail_if_empty "$app_name" "Application name not specified"
fail_if_empty "$backend_app_name" "Backend application name not specified"
fail_if_empty "$environment_name" "Environment name not specified"
fail_if_empty "$region" "Region name not specified"
fail_if_empty "$api_region" "API Region not specified"

echo_info "Using application name: $app_name"
echo_info "Using environment name: $environment_name"
echo_info "Using region name: $region_name"
echo_info "Using API region name: $api_region"

CWD=$(pwd)

export UPLOAD_ENV="remote"
export APP_NAME=$app_name
export BACKEND_APP_NAME=$backend_app_name
export ENVIRONMENT_NAME=$environment_name
export AWS_DEFAULT_REGION=$region
export AWS_REGION_BE_API=$api_region

cd $CWD/web && . configure_auth.sh

yarn build
