#!/bin/bash
# Required dependency: jq
# Example usage locally: ./configure_auth.sh proserve-wb-ui proserve-wb dev us-east-1 us-east-1 fe-profile be-profile
# Example usage in CI (requires the below environment variables): ./configure_auth.sh
#   APP_NAME: proserve-workbench-ui
#   BACKEND_APP_NAME: proserve-workbench
#   ENVIRONMENT_NAME: dev
#   AWS_DEFAULT_REGION: us-east-1
#   AWS_REGION_BE_API: us-east-1
#   

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
profile_name=$6
be_profile_name=$7

fail_if_empty "$app_name" "Application name not specified"
fail_if_empty "$backend_app_name" "Backend application name not specified"
fail_if_empty "$environment_name" "Application environment not specified"
fail_if_empty "$region" "Region not specified"
fail_if_empty "$api_region" "API Region not specified"

echo_info "Using application name: $app_name"
echo_info "Generating aws-exports.js..."

default_region=$region
default_api_region=$api_region

profile=""
if [ ! -z $profile_name ]; then
  echo_info "Using profile $profile_name for frontend"
  profile="--profile $profile_name"
fi

be_profile=""
if [ ! -z $be_profile_name ]; then
  echo_info "Using profile $be_profile_name for backend"
  be_profile="--profile $be_profile_name"
fi

stack_name_suffix="$app_name-$environment_name"

# Fetch User Interface params

if [ ! -z "$FE_READ_ROLE" ]; then
  echo_info "Assuming $FE_READ_ROLE role for frontend"
  unset AWS_ACCESS_KEY_ID
  unset AWS_SECRET_ACCESS_KEY
  unset AWS_SESSION_TOKEN
  FE_TEMP_ROLE=$(aws sts assume-role --role-arn $FE_READ_ROLE --role-session-name workbench-ui-build-session); export FE_TEMP_ROLE
  export AWS_ACCESS_KEY_ID=$(echo "${FE_TEMP_ROLE}" | jq -r '.Credentials.AccessKeyId')
  export AWS_SECRET_ACCESS_KEY=$(echo "${FE_TEMP_ROLE}" | jq -r '.Credentials.SecretAccessKey')
  export AWS_SESSION_TOKEN=$(echo "${FE_TEMP_ROLE}" | jq -r '.Credentials.SessionToken')
fi

ui_stack_name="$stack_name_suffix"
ui_stack_outputs=$(aws cloudformation describe-stacks --stack-name $ui_stack_name --query 'Stacks[0].Outputs' --output json --region $default_region $profile || echo "")
user_pool_client_id=$(jq -r '.[] | select(.OutputKey=="icwebclientidoutput") | .OutputValue' <<< $ui_stack_outputs)
cdn_fqdn=$(jq -r '.[] | select(.OutputKey=="cdnfqdnoutput") | .OutputValue' <<< $ui_stack_outputs)
cdn_custom_fqdn=$(jq -r '.[] | select(.OutputKey=="cdncustomfqdnoutput") | .OutputValue' <<< $ui_stack_outputs)
user_pool_id=$(jq -r '.[] | select(.OutputKey=="userpooloutputid") | .OutputValue' <<< $ui_stack_outputs)
user_pool_fqdn=$(jq -r '.[] | select(.OutputKey=="userpooloutputdomain") | .OutputValue' <<< $ui_stack_outputs)
user_pool_custom_fqdn=$(jq -r '.[] | select(.OutputKey=="userpooloutputcustomdomain") | .OutputValue' <<< $ui_stack_outputs)
user_pool_client_logout_redirect_url=$(jq -r '.[] | select(.OutputKey=="userpooloutputlogouturl") | .OutputValue' <<< $ui_stack_outputs)

user_pool_client_redirect_url="https://$cdn_fqdn"

if [ ! -z $user_pool_custom_fqdn ]; then
 echo_info "Configure custom domain for login: $user_pool_custom_fqdn"
 user_pool_fqdn="$user_pool_custom_fqdn"
fi

if [ "$cdn_custom_fqdn" != "not available" ]; then
 echo_info "Configure custom domain: $cdn_custom_fqdn"
 user_pool_client_redirect_url="https://$cdn_custom_fqdn"
fi

if [ "$UPLOAD_ENV" != "remote" ]; then
  echo_info "Configuring for localhost..."
  user_pool_client_redirect_url="http://localhost:3000"
  user_pool_client_logout_redirect_url="http://localhost:3000"
fi

if [ ! -z "$BE_READ_ROLE" ]; then
  echo_info "Assuming $BE_READ_ROLE role for backend"
  unset AWS_ACCESS_KEY_ID
  unset AWS_SECRET_ACCESS_KEY
  unset AWS_SESSION_TOKEN
  BE_TEMP_ROLE=$(aws sts assume-role --role-arn $BE_READ_ROLE --role-session-name workbench-ui-build-session); export BE_READ_ROLE
  export AWS_ACCESS_KEY_ID=$(echo "${BE_TEMP_ROLE}" | jq -r '.Credentials.AccessKeyId')
  export AWS_SECRET_ACCESS_KEY=$(echo "${BE_TEMP_ROLE}" | jq -r '.Credentials.SecretAccessKey')
  export AWS_SESSION_TOKEN=$(echo "${BE_TEMP_ROLE}" | jq -r '.Credentials.SessionToken')
fi

# Fetch endpoints for project api
projects_api_stack_name="${backend_app_name}-projects-$environment_name"
projects_api_stack_outputs=$(aws cloudformation describe-stacks --stack-name $projects_api_stack_name --query 'Stacks[0].Outputs' --output json --region $default_api_region $profile || echo "")
projects_api_invoke_url=$(jq -r '.[] | select(.OutputKey | startswith("ProjectsAppOpenApiApiUrlOutput")) | .OutputValue' <<< $projects_api_stack_outputs)

# Fetch endpoints for publishing api
publishing_api_stack_name="${backend_app_name}-publishing-$environment_name"
publishing_api_stack_outputs=$(aws cloudformation describe-stacks --stack-name $publishing_api_stack_name --query 'Stacks[0].Outputs' --output json --region $default_api_region $profile || echo "")
publishing_api_invoke_url=$(jq -r '.[] | select(.OutputKey | startswith("PublishingAppOpenApiApiUrlOutput")) | .OutputValue' <<< $publishing_api_stack_outputs)

# Fetch endpoints for packaging api
packaging_api_stack_name="${backend_app_name}-packaging-$environment_name"
packaging_api_stack_outputs=$(aws cloudformation describe-stacks --stack-name $packaging_api_stack_name --query 'Stacks[0].Outputs' --output json --region $default_api_region $profile || echo "")
packaging_api_invoke_url=$(jq -r '.[] | select(.OutputKey | startswith("PackagingAppOpenApiApiUrlOutput")) | .OutputValue' <<< $packaging_api_stack_outputs)

# Fetch endpoints for provisioning api
provisioning_api_stack_name="${backend_app_name}-provisioning-$environment_name"
provisioning_api_stack_outputs=$(aws cloudformation describe-stacks --stack-name $provisioning_api_stack_name --query 'Stacks[0].Outputs' --output json --region $default_api_region $profile || echo "")
provisioning_api_invoke_url=$(jq -r '.[] | select(.OutputKey | startswith("ProvisioningAppOpenApiApiUrlOutput")) | .OutputValue' <<< $provisioning_api_stack_outputs)

#Fetch custom domain name
integration_stack_outputs=$(aws cloudformation describe-stacks --stack-name ApiIntegrationStack --query 'Stacks[0].Outputs' --output json --region $default_api_region $profile || echo "")
projects_api_custom_invoke_url=$(jq -r '.[] | select(.OutputKey == "projectsCustomDomainForApI") | .OutputValue' <<< $integration_stack_outputs)
publishing_api_custom_invoke_url=$(jq -r '.[] | select(.OutputKey == "publishingCustomDomainForApI") | .OutputValue' <<< $integration_stack_outputs)
packaging_api_custom_invoke_url=$(jq -r '.[] | select(.OutputKey == "packagingCustomDomainForApI") | .OutputValue' <<< $integration_stack_outputs)
provisioning_api_custom_invoke_url=$(jq -r '.[] | select(.OutputKey == "provisioningCustomDomainForApI") | .OutputValue' <<< $integration_stack_outputs)


if [ ! -z $projects_api_custom_invoke_url ]; then
 echo_info "Configure custom domain for projects API: $projects_api_custom_invoke_url"
 projects_api_invoke_url="https://$projects_api_custom_invoke_url"
fi

if [ ! -z $publishing_api_custom_invoke_url ]; then
 echo_info "Configure custom domain for publishing API: $publishing_api_custom_invoke_url"
 publishing_api_invoke_url="https://$publishing_api_custom_invoke_url"
fi

if [ ! -z $packaging_api_custom_invoke_url ]; then
 echo_info "Configure custom domain for packaging API: $packaging_api_custom_invoke_url"
 packaging_api_invoke_url="https://$packaging_api_custom_invoke_url"
fi

if [ ! -z $provisioning_api_custom_invoke_url ]; then
 echo_info "Configure custom domain for provisioning API: $provisioning_api_custom_invoke_url"
 provisioning_api_invoke_url="https://$provisioning_api_custom_invoke_url"
fi

# Output src/aws-exports.js

cat << EOF > src/aws-exports.js
const awsmobile = {
  Auth: {
    Cognito: {
      userPoolId: '$user_pool_id',
      userPoolClientId: '$user_pool_client_id',
      loginWith: {
        oauth: {
          domain: '$user_pool_fqdn',
          scopes: ['email', 'profile', 'openid'],
          redirectSignIn: ['$user_pool_client_redirect_url'],
          redirectSignOut: ['$user_pool_client_logout_redirect_url'],
          responseType: 'code'
        }
      }
    },
    cookieStorage: {
      expires: 2
    }
  },
  API: {
    REST: {
      ProjectsAPI: {
        endpoint: '${projects_api_invoke_url%/}',
        region: '$api_region'
      },
      PublishingAPI: {
        endpoint: '${publishing_api_invoke_url%/}',
        region: '$api_region'
      },
      PackagingAPI: {
        endpoint: '${packaging_api_invoke_url%/}',
        region: '$api_region'
      },
      ProvisioningAPI: {
        endpoint: '${provisioning_api_invoke_url%/}',
        region: '$api_region'
      }
    }
  }
};
export default awsmobile;
EOF
