#!/bin/bash

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
  [ -z "$1" ] && echo_fail "$2" && exit 1
  return 0
}

app_name=${1:-$APP_NAME}
environment_name=${2:-$ENVIRONMENT_NAME}
default_region=${3:-$AWS_DEFAULT_REGION}

# Optional: a caller may export profile="--profile <name>". Split it into
# separate arguments so it can be passed through safely.
# shellcheck disable=SC2154 # set by the caller, if at all
read -r -a profile_args <<< "${profile:-}"

fail_if_empty "$app_name" "Application name not specified"
fail_if_empty "$environment_name" "Environment name not specified"
fail_if_empty "$default_region" "Region name not specified"


echo_info "Using application name: $app_name"
echo_info "Using environment name: $environment_name"
echo_info "Using region name: $default_region"


export UPLOAD_ENV="remote"

ui_stack_name="$app_name-$environment_name"

ui_stack_outputs=$(aws cloudformation describe-stacks --stack-name "$ui_stack_name" --query 'Stacks[0].Outputs' --output json --region "$default_region")

distribution_id=$(jq -r '.[] | select(.OutputKey=="cdndistributionidoutput") | .OutputValue' <<< "$ui_stack_outputs")
s3_bucket_name=$(jq -r '.[] | select(.OutputKey=="icfrontends3output") | .OutputValue' <<< "$ui_stack_outputs")
CWD=$(pwd)

cd "$CWD/web/dist"

# Redeploy main web app
aws s3 rm "s3://$s3_bucket_name/static/" "${profile_args[@]}" --recursive
aws s3 cp ./ "s3://$s3_bucket_name/" "${profile_args[@]}" --recursive

if [ -n "$distribution_id" ]; then
 echo_info "Invalidating CloudFront distribution $distribution_id..."
 aws cloudfront create-invalidation --distribution-id "$distribution_id" "${profile_args[@]}" --paths "/*"
fi
