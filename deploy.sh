#!/usr/bin/env bash
# =============================================================================
# VEW Platform - Automated Deployment Script
#
# Deploys the Virtual Engineering Workbench to a single AWS account with
# optional spoke account onboarding. Standard public deployment.
#
# Usage: ./deploy.sh [--config <path>] [--dry-run] [--destroy]
#   --config <path>  Load inputs from a config file instead of prompting
#
# Prerequisites: aws-cli v2, cdk v2, node 18+, python 3.13+, uv, jq, yarn 4+
# =============================================================================
set -euo pipefail
export AWS_PAGER=""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
CONFIG_FILE=""
LOG_FILE="$SCRIPT_DIR/.deploy-logs/deploy-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$SCRIPT_DIR/.deploy-logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[VEW]${NC} $1" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[VEW]${NC} $1" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[VEW]${NC} $1" | tee -a "$LOG_FILE"; exit 1; }
step() { echo -e "\n${CYAN}━━━ Phase $1: $2 ━━━${NC}" | tee -a "$LOG_FILE"; }

run_cmd() {
  log "Running: $*"
  "$@" 2>&1 | tee -a "$LOG_FILE"
  local rc=${PIPESTATUS[0]}
  if [ $rc -ne 0 ]; then
    err "Command failed (exit $rc): $*"
  fi
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
DESTROY_MODE=false
DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --config)  CONFIG_FILE="$2"; shift 2 ;;
    --destroy) DESTROY_MODE=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) err "Unknown argument: $1" ;;
  esac
done

# ---------------------------------------------------------------------------
# --destroy: tear down all VEW stacks and orphaned resources
# ---------------------------------------------------------------------------
if [ "$DESTROY_MODE" = "true" ]; then
  if [ -z "$CONFIG_FILE" ]; then
    err "--destroy requires --config <path> to identify resources by prefix"
  fi
  source "$CONFIG_FILE"
  PREFIX="${ORG_PREFIX}-${APP_PREFIX}"
  warn "This will delete ALL VEW stacks and orphaned resources with prefix '$PREFIX' in $AWS_REGION"
  read -r -p "$(echo -e "${YELLOW}Type 'destroy' to confirm: ${NC}")" CONFIRM
  [[ "$CONFIRM" == "destroy" ]] || err "Destruction cancelled"

  activate_hub_credentials 2>/dev/null || true

  log "Deleting CloudFormation stacks..."
  STACKS=$(aws cloudformation list-stacks \
    --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE \
    --query "StackSummaries[?starts_with(StackName, '${PREFIX}')].StackName" \
    --output text --region "$AWS_REGION" 2>/dev/null || echo "")
  for stack in $STACKS; do
    log "Deleting stack: $stack"
    aws cloudformation delete-stack --stack-name "$stack" --region "$AWS_REGION"
    aws cloudformation wait stack-delete-complete --stack-name "$stack" --region "$AWS_REGION" || \
      warn "Stack $stack deletion may have failed — check console"
  done

  log "Cleaning orphaned CloudWatch log groups..."
  for prefix_pattern in "$PREFIX" "aws-waf-logs-${PREFIX}"; do
    aws logs describe-log-groups --log-group-name-prefix "$prefix_pattern" --region "$AWS_REGION" \
      --query 'logGroups[].logGroupName' --output text 2>/dev/null | tr '\t' '\n' | while read -r lg; do
      [ -n "$lg" ] && aws logs delete-log-group --log-group-name "$lg" --region "$AWS_REGION" \
        && log "Deleted log group: $lg"
    done
  done

  log "Cleaning orphaned ECR repositories..."
  aws ecr describe-repositories --region "$AWS_REGION" \
    --query "repositories[?starts_with(repositoryName, '${PREFIX}')].repositoryName" \
    --output text 2>/dev/null | tr '\t' '\n' | while read -r repo; do
    [ -n "$repo" ] && aws ecr delete-repository --repository-name "$repo" --force \
      --region "$AWS_REGION" && log "Deleted ECR repo: $repo"
  done

  log "Cleaning orphaned S3 buckets..."
  aws s3api list-buckets --query "Buckets[?starts_with(Name, '${PREFIX}')].Name" \
    --output text 2>/dev/null | tr '\t' '\n' | while read -r bucket; do
    [ -n "$bucket" ] && aws s3 rb "s3://$bucket" --force && log "Deleted S3 bucket: $bucket"
  done

  log "Destruction complete"
  exit 0
fi

# ---------------------------------------------------------------------------
# Phase 0: Validate prerequisites
# ---------------------------------------------------------------------------
step 0 "Validating prerequisites (CLI tools, AWS credentials, AWS Organization)"

for cmd in aws cdk node python uv jq yarn; do
  if ! command -v "$cmd" &>/dev/null; then
    err "Required command not found: $cmd"
  fi
done

AWS_CLI_VERSION=$(aws --version 2>&1 | head -1)
AWS_CLI_MAJOR=$(aws --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 | cut -d. -f1)
CDK_VERSION=$(cdk --version 2>&1 | head -1)
CDK_MAJOR=$(cdk --version 2>&1 | grep -oE '[0-9]+' | head -1)
NODE_VERSION=$(node --version)
NODE_MAJOR=$(node --version | tr -d 'v' | cut -d. -f1)
PYTHON_VERSION=$(python --version)
PYTHON_MINOR=$(python --version | grep -oE '[0-9]+\.[0-9]+' | head -1 | cut -d. -f2)
UV_VERSION=$(uv --version 2>&1 | head -1)
YARN_VERSION=$(COREPACK_ENABLE_DOWNLOAD_PROMPT=0 yarn --version 2>&1)
YARN_MAJOR=$(echo "$YARN_VERSION" | cut -d. -f1)

log "aws-cli:  $AWS_CLI_VERSION"
log "cdk:      $CDK_VERSION"
log "node:     $NODE_VERSION"
log "python:   $PYTHON_VERSION"
log "uv:       $UV_VERSION"
log "yarn:     $YARN_VERSION"

[[ "$AWS_CLI_MAJOR" -ge 2 ]] 2>/dev/null || err "aws-cli v2 or higher is required (found: $AWS_CLI_VERSION)"
[[ "$CDK_MAJOR" -ge 2 ]] 2>/dev/null || err "cdk v2 or higher is required (found: $CDK_VERSION)"
[[ "$NODE_MAJOR" -ge 18 ]] 2>/dev/null || err "node 18.x or higher is required (found: $NODE_VERSION)"
[[ "$PYTHON_MINOR" -ge 13 ]] 2>/dev/null || err "python 3.13 or higher is required (found: $PYTHON_VERSION)"
[[ "$YARN_MAJOR" -ge 4 ]] 2>/dev/null || err "yarn 4.x or higher is required (found: $YARN_VERSION)"

if grep -qi microsoft /proc/version 2>/dev/null; then
  log "WSL environment detected"
  if [[ "$REPO_ROOT" == /mnt/* ]]; then
    warn "Repository is on the Windows filesystem (/mnt/...)."
    warn "Python venvs and Yarn will fail here. Copy the repo to the Linux filesystem first:"
    warn "  cp -r $REPO_ROOT /tmp/vew && cd /tmp/vew"
    err "Cannot continue from a Windows filesystem path in WSL."
  fi
fi

if command -v corepack &>/dev/null; then
  corepack enable 2>/dev/null || true
fi

if [ "$(uname -s)" != "Linux" ]; then
  if ! docker info &>/dev/null; then
    err "Docker is required on non-Linux systems for Lambda bundling and ECS image builds. Install Docker and ensure the daemon is running."
  fi
  log "docker:   $(docker --version)"
else
  if ! docker info &>/dev/null; then
    warn "Docker is not running. ECS task image builds will fail. Lambda bundling will use local mode."
  else
    log "docker:   $(docker --version)"
  fi
fi

# ---------------------------------------------------------------------------
# Phase 1: Collect deployment parameters
# ---------------------------------------------------------------------------
step 1 "Collecting deployment parameters"

prompt() {
  local var_name="$1" prompt_text="$2" default="$3" is_secret="${4:-false}"
  if [ -n "${!var_name:-}" ]; then
    if [ "$is_secret" = "true" ]; then
      log "$prompt_text: ********"
    else
      log "$prompt_text: ${!var_name}"
    fi
    return
  fi
  if [ -n "$default" ]; then
    prompt_text="$prompt_text [$default]"
  fi
  if [ "$is_secret" = "true" ]; then
    read -rsp "$prompt_text: " value
    echo
  else
    read -rp "$prompt_text: " value
  fi
  value="${value:-$default}"
  printf -v "$var_name" '%s' "$value"
}

# Load config file if provided
if [ -n "$CONFIG_FILE" ]; then
  if [ ! -f "$CONFIG_FILE" ]; then
    err "Config file not found: $CONFIG_FILE"
  fi
  log "Loading config from $CONFIG_FILE"
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
fi

if [ -z "${AWS_ACCESS_KEY_ID:-}" ]; then
  prompt AWS_PROFILE_HUB "AWS CLI profile for hub account (empty for default)" "default"
fi
prompt AWS_ACCOUNT_ID    "AWS Account ID (12 digits)"          ""
[[ "$AWS_ACCOUNT_ID" =~ ^[0-9]{12}$ ]] || err "Invalid AWS Account ID: $AWS_ACCOUNT_ID"
prompt AWS_REGION         "AWS Region"                          "us-east-1"
prompt ENVIRONMENT        "Environment (dev/qa/prod)"           "dev"
[[ "$ENVIRONMENT" =~ ^(dev|qa|prod)$ ]] || err "Invalid environment: $ENVIRONMENT"
prompt ORG_PREFIX         "Organization prefix"                 "proserve"
prompt APP_PREFIX         "Application prefix"                  "wb"
prompt ADMIN_EMAIL        "Admin user email"                    ""
[[ -n "$ADMIN_EMAIL" ]] || err "Admin email is required"
[[ "$ADMIN_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]] || err "Admin email is not valid: $ADMIN_EMAIL"
if [[ "$ADMIN_EMAIL" == *"example.com"* ]] || [[ "$ADMIN_EMAIL" == *"example.org"* ]]; then
  err "ADMIN_EMAIL is still set to a placeholder ($ADMIN_EMAIL). Update it to a real email address."
fi
prompt ADMIN_USER_ID      "Admin user ID (uppercase, not an email)"          ""
[[ -n "$ADMIN_USER_ID" ]] || err "Admin user ID is required"
[[ "$ADMIN_USER_ID" != *"@"* ]] || err "Admin user ID must not be an email address. Use a plain user ID (e.g. JDOE), not an email: $ADMIN_USER_ID"
[[ "$ADMIN_USER_ID" =~ ^[a-zA-Z0-9]+$ ]] || err "Admin user ID must be alphanumeric: $ADMIN_USER_ID"

echo ""
log "OIDC federation (leave empty to use manual Cognito users):"
prompt OIDC_CLIENT_ID     "OIDC Client ID"                     ""
prompt OIDC_CLIENT_SECRET "OIDC Client Secret"                 "" true
prompt OIDC_ISSUER_URL    "OIDC Issuer URL"                    ""

echo ""
log "TLS and DNS (leave empty for no custom domain):"
prompt CERT_ARN           "TLS Certificate ARN (deployment region)" ""
prompt CUSTOM_DOMAIN      "Custom domain (e.g. dev.workbench.company.com)" ""
prompt API_CUSTOM_DOMAIN  "API custom domain (e.g. dev.api.workbench.company.com)" ""

# us-east-1 cert needed for Cognito/CloudFront if deploying to another region
CERT_ARN_US_EAST_1=""
if [ "$AWS_REGION" != "us-east-1" ] && [ -n "$CERT_ARN" ]; then
  prompt CERT_ARN_US_EAST_1 "TLS Certificate ARN in us-east-1 (for Cognito)" ""
fi

echo ""
log "Spoke account (optional):"
prompt SPOKE_ACCOUNT_ID   "Spoke Account ID (empty to skip)"   ""
if [ -n "$SPOKE_ACCOUNT_ID" ]; then
  prompt SPOKE_VPC_ID        "Spoke VPC ID (empty to create a new VPC)"  ""
  if [ -z "$SPOKE_VPC_ID" ]; then
    warn "No Spoke VPC ID provided — a new VPC will be created in the spoke account during bootstrap."
  fi
  prompt AWS_PROFILE_SPOKE   "AWS CLI profile for spoke account"  ""
  [[ -n "$AWS_PROFILE_SPOKE" ]] || warn "AWS profile for spoke not specified. Will fallback to using AWS_SPOKE_ACCESS_KEY_ID, AWS_SPOKE_SECRET_ACCESS_KEY and AWS_SPOKE_SESSION_TOKEN environment variables."
fi

# Derived values
APP_NAME="${ORG_PREFIX}-${APP_PREFIX}-ui"
BACKEND_APP_NAME="${ORG_PREFIX}-${APP_PREFIX}"
BACKEND_DIR="$REPO_ROOT/backend"
DEPLOYMENT_QUALIFIER=$(echo -n "$AWS_ACCOUNT_ID" | md5sum | cut -c1-5)
ADMIN_USER_ID=$(echo "$ADMIN_USER_ID" | tr '[:lower:]' '[:upper:]')
SPOKE_CDK_QUALIFIER="ioc760get"
PROJECTS_TABLE="${ORG_PREFIX}-${APP_PREFIX}-projects-table-${ENVIRONMENT}"

# Save config for re-runs (excluding secrets)
CONFIG_OUT="$SCRIPT_DIR/.deploy-config-${ENVIRONMENT}"
cat > "$CONFIG_OUT" <<CONF
AWS_ACCOUNT_ID="$AWS_ACCOUNT_ID"
AWS_REGION="$AWS_REGION"
ENVIRONMENT="$ENVIRONMENT"
ORG_PREFIX="$ORG_PREFIX"
APP_PREFIX="$APP_PREFIX"
ADMIN_EMAIL="$ADMIN_EMAIL"
ADMIN_USER_ID="$ADMIN_USER_ID"
OIDC_CLIENT_ID="$OIDC_CLIENT_ID"
OIDC_ISSUER_URL="$OIDC_ISSUER_URL"
CERT_ARN="$CERT_ARN"
CERT_ARN_US_EAST_1="${CERT_ARN_US_EAST_1:-}"
CUSTOM_DOMAIN="$CUSTOM_DOMAIN"
API_CUSTOM_DOMAIN="$API_CUSTOM_DOMAIN"
SPOKE_ACCOUNT_ID="${SPOKE_ACCOUNT_ID:-}"
SPOKE_VPC_ID="${SPOKE_VPC_ID:-}"
AWS_PROFILE_HUB="${AWS_PROFILE_HUB:-default}"
AWS_PROFILE_SPOKE="${AWS_PROFILE_SPOKE:-}"
CONF
log "Config saved to $CONFIG_OUT (re-run with --config $CONFIG_OUT)"

# ---------------------------------------------------------------------------
# Activate hub account credentials
# ---------------------------------------------------------------------------
activate_hub_credentials() {
  if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    log "Using existing env var credentials (AWS_ACCESS_KEY_ID set)"
    return
  fi
  log "Activating credentials for hub account (profile: $AWS_PROFILE_HUB)"
  eval "$(aws configure export-credentials --profile "$AWS_PROFILE_HUB" --format env)"
}

activate_spoke_credentials() {
  if [ -n "${AWS_SPOKE_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SPOKE_SECRET_ACCESS_KEY:-}" ]; then
    export AWS_ACCESS_KEY_ID="$AWS_SPOKE_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$AWS_SPOKE_SECRET_ACCESS_KEY"
    export AWS_SESSION_TOKEN="${AWS_SPOKE_SESSION_TOKEN:-}"
    log "Using existing env var credentials for spoke account"
    return
  fi
  if [ -z "${AWS_PROFILE_SPOKE:-}" ]; then
    err "No spoke account credentials available. Set AWS_PROFILE_SPOKE or AWS_SPOKE_ACCESS_KEY_ID/AWS_SPOKE_SECRET_ACCESS_KEY environment variables."
  fi
  log "Activating credentials for spoke account (profile: $AWS_PROFILE_SPOKE)"
  eval "$(aws configure export-credentials --profile "$AWS_PROFILE_SPOKE" --format env)"
}

activate_hub_credentials

# Verify credentials target the expected account
CALLER_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text)
if [ "$CALLER_ACCOUNT" != "$AWS_ACCOUNT_ID" ]; then
  err "Profile '$AWS_PROFILE_HUB' targets account $CALLER_ACCOUNT, expected $AWS_ACCOUNT_ID"
fi
log "Hub account credentials verified: $AWS_ACCOUNT_ID"

# Fetch Organization ID
ORG_ID=$(aws organizations describe-organization --query 'Organization.Id' --output text 2>/dev/null || echo "")
[[ -n "$ORG_ID" ]] || err "AWS Organization ID is required. Account must be part of an AWS Organization."
log "Organization ID: $ORG_ID"

if [ "$DRY_RUN" = "true" ]; then
  echo ""
  log "=== DRY RUN SUMMARY ==="
  log "Account:       $AWS_ACCOUNT_ID (verified: $CALLER_ACCOUNT)"
  log "Region:        $AWS_REGION"
  log "Environment:   $ENVIRONMENT"
  log "Org prefix:    $ORG_PREFIX"
  log "App prefix:    $APP_PREFIX"
  log "Admin:         $ADMIN_USER_ID ($ADMIN_EMAIL)"
  log "Org ID:        $ORG_ID"
  log "OIDC:          ${OIDC_CLIENT_ID:-not configured}"
  log "Custom domain: ${CUSTOM_DOMAIN:-not configured}"
  log "Spoke account: ${SPOKE_ACCOUNT_ID:-not configured}"
  log ""
  log "All prerequisites validated. Ready to deploy."
  log "Run without --dry-run to proceed."
  exit 0
fi

# ---------------------------------------------------------------------------
# Phase 2: Patch source configuration files
# ---------------------------------------------------------------------------
step 2 "Patching source configuration files (config.py, cdk.json)"

BACKEND_CONFIG="$REPO_ROOT/backend/infra/config.py"
FE_CDK_JSON="$REPO_ROOT/frontend/infrastructure/cdk.json"
FE_PUBLIC_STACK="$REPO_ROOT/frontend/infrastructure/lib/public-access-deployment-stack.ts"

# --- backend/infra/config.py ---
log "Patching $BACKEND_CONFIG"
sed -i.bak \
  -e "s/^ORGANIZATION_PREFIX = \".*\"/ORGANIZATION_PREFIX = \"${ORG_PREFIX}\"/" \
  -e "s/^APPLICATION_PREFIX = \".*\"/APPLICATION_PREFIX = \"${APP_PREFIX}\"/" \
  -e "s/\"cognito-region\": \"[^\"]*\"/\"cognito-region\": \"${AWS_REGION}\"/" \
  -e "s/\"enabled-workbench-regions\": \[\"[^\"]*\"\]/\"enabled-workbench-regions\": [\"${AWS_REGION}\"]/" \
  -e "s/login-[a-z0-9]*\.auth\.[a-z0-9-]*/login-${DEPLOYMENT_QUALIFIER}.auth.${AWS_REGION}/g" \
  "$BACKEND_CONFIG"
rm -f "${BACKEND_CONFIG}.bak"

# --- backend/infra/constants.py ---
BACKEND_CONSTANTS="$REPO_ROOT/backend/infra/constants.py"
MACHINE_ARCH=$(uname -m)
case "$MACHINE_ARCH" in
  arm64|aarch64)
    LAMBDA_ARCH_KEY="ARM_ARCH_KEY"
    ;;
  x86_64|amd64)
    LAMBDA_ARCH_KEY="X86_ARCH_KEY"
    ;;
  *)
    err "Unsupported architecture: $MACHINE_ARCH"
    ;;
esac
log "Detected architecture: $MACHINE_ARCH → Lambda $LAMBDA_ARCH_KEY"

sed -i.bak "s/^LAMBDA_ARCHITECTURE = .*_ARCH_KEY/LAMBDA_ARCHITECTURE = ${LAMBDA_ARCH_KEY}/" "$BACKEND_CONSTANTS"
rm -f "${BACKEND_CONSTANTS}.bak"

# Disable local bundling on non-Linux (macOS) — forces Docker bundling for native deps
if [ "$(uname -s)" != "Linux" ]; then
  log "Non-Linux OS detected — disabling local bundling (Docker required)"
  sed -i.bak 's/^LOCAL_BUNDLING = True/LOCAL_BUNDLING = False/' "$BACKEND_CONSTANTS"
  rm -f "${BACKEND_CONSTANTS}.bak"
fi

# --- frontend/infrastructure/cdk.json ---
log "Patching $FE_CDK_JSON"

OIDC_NAME="${ORG_PREFIX}-${APP_PREFIX}-ui-dev/oidc"
if [ -z "$OIDC_CLIENT_ID" ]; then
  ALLOW_CUSTOM_LOGIN="true"
  OIDC_FILTER='| del(.context.config.dev.OIDCSecretName)'
else
  ALLOW_CUSTOM_LOGIN="false"
  OIDC_FILTER='| .context.config.dev.OIDCSecretName = $oidc'
fi

jq --arg app_name "$APP_NAME" \
   --arg qualifier "$DEPLOYMENT_QUALIFIER" \
   --arg oidc "$OIDC_NAME" \
   --argjson allow_login "$ALLOW_CUSTOM_LOGIN" \
   ".context[\"app-name\"] = \$app_name | .context[\"deployment-qualifier\"] = \$qualifier | .context.config.dev.AllowCustomUserLogin = \$allow_login $OIDC_FILTER" \
   "$FE_CDK_JSON" > "${FE_CDK_JSON}.tmp" && mv "${FE_CDK_JSON}.tmp" "$FE_CDK_JSON"

# --- frontend/infrastructure/lib/public-access-deployment-stack.ts ---
if [ -f "$FE_PUBLIC_STACK" ]; then
  log "Patching $FE_PUBLIC_STACK"
  MONITORING_PREFIX="${ORG_PREFIX}-${APP_PREFIX}-monitoring"
  sed -i.bak \
    -e "s/[a-z0-9-]*-monitoring/${MONITORING_PREFIX}/g" \
    "$FE_PUBLIC_STACK"
  rm -f "${FE_PUBLIC_STACK}.bak"
fi

log "Configuration files patched"

# ---------------------------------------------------------------------------
# Phase 3: CDK bootstrap (default qualifier)
# ---------------------------------------------------------------------------
step 3 "CDK bootstrapping account $AWS_ACCOUNT_ID in $AWS_REGION"

run_cmd cdk bootstrap "aws://${AWS_ACCOUNT_ID}/${AWS_REGION}" \
  --trust "$AWS_ACCOUNT_ID" \
  --cloudformation-execution-policies "arn:aws:iam::aws:policy/AdministratorAccess"

if [ "$AWS_REGION" != "us-east-1" ]; then
  log "Bootstrapping us-east-1 for Cognito/CloudFront resources"
  run_cmd cdk bootstrap "aws://${AWS_ACCOUNT_ID}/us-east-1" \
    --trust "$AWS_ACCOUNT_ID" \
    --cloudformation-execution-policies "arn:aws:iam::aws:policy/AdministratorAccess"
fi

# ---------------------------------------------------------------------------
# Phase 4: Create prerequisite resources (SSM parameters, VPC, service roles)
# ---------------------------------------------------------------------------
step 4 "Creating prerequisite resources (SSM, VPC, service-linked roles)"

put_ssm() {
  local name="$1" value="$2"
  log "SSM: $name"
  aws ssm put-parameter \
    --name "$name" \
    --value "$value" \
    --type String \
    --overwrite \
    --region "$AWS_REGION" 2>&1 | tee -a "$LOG_FILE" || true
}

put_ssm "/${ORG_PREFIX}-${APP_PREFIX}-ui-${ENVIRONMENT}/tools-account-id" "$AWS_ACCOUNT_ID"
put_ssm "/${ORG_PREFIX}-${APP_PREFIX}-ui-${ENVIRONMENT}/dns-records" '{"records":[]}'
put_ssm "/${ORG_PREFIX}-${APP_PREFIX}-backend-${ENVIRONMENT}/image-service-account-id" "$AWS_ACCOUNT_ID"

# Ensure Image Builder service-linked role exists (required by packaging stacks)
aws iam create-service-linked-role --aws-service-name imagebuilder.amazonaws.com 2>/dev/null || true

# --- VPC ---
VPC_NAME="vpc-${ORG_PREFIX}-${APP_PREFIX}-${ENVIRONMENT}"

EXISTING_VPC=$(aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=$VPC_NAME" \
  --query 'Vpcs[0].VpcId' --output text \
  --region "$AWS_REGION" 2>/dev/null || echo "None")

if [ "$EXISTING_VPC" = "None" ] || [ -z "$EXISTING_VPC" ]; then
  warn "VPC '$VPC_NAME' not found in $AWS_REGION"
  warn "A development VPC will be created. This is intended for dev/testing only — not for production use."
  read -r -p "$(echo -e "${YELLOW}Proceed with VPC creation? [y/N]: ${NC}")" VPC_CONFIRM
  if [[ ! "$VPC_CONFIRM" =~ ^[Yy]$ ]]; then
    err "VPC creation declined. Create a VPC named '$VPC_NAME' manually and re-run."
  fi
  log "Deploying VPC via CDK"
  if [ ! -d "$BACKEND_DIR/.venv" ]; then
    uv venv "$BACKEND_DIR/.venv" --python 3.13
  fi
  source "$BACKEND_DIR/.venv/bin/activate"
  UV_PROJECT_ENVIRONMENT="$BACKEND_DIR/.venv" uv sync --project "$BACKEND_DIR" --group dev --group test 2>&1 | tail -1 | tee -a "$LOG_FILE"
  (
    cd "$BACKEND_DIR"
    cp cdk-vpc.json cdk.json
    run_cmd cdk deploy --all --require-approval never --force \
      -c "environment=$ENVIRONMENT" \
      -c "account=$AWS_ACCOUNT_ID" \
      -c "region=$AWS_REGION"
    rm -f cdk.json
  )
  deactivate
  log "VPC created"
else
  log "VPC '$VPC_NAME' already exists ($EXISTING_VPC)"
fi

# ---------------------------------------------------------------------------
# Phase 5: Configure identity federation (OIDC secret)
# ---------------------------------------------------------------------------
step 5 "Configuring identity federation"

OIDC_SECRET_NAME="${ORG_PREFIX}-${APP_PREFIX}-ui-${ENVIRONMENT}/oidc"

if [ -n "$OIDC_CLIENT_ID" ] && [ -n "$OIDC_CLIENT_SECRET" ] && [ -n "$OIDC_ISSUER_URL" ]; then
  log "Creating OIDC secret: $OIDC_SECRET_NAME"
  OIDC_JSON=$(jq -n \
    --arg cid "$OIDC_CLIENT_ID" \
    --arg cs "$OIDC_CLIENT_SECRET" \
    --arg iss "$OIDC_ISSUER_URL" \
    '{ClientID: $cid, ClientSecret: $cs, Issuer: $iss}')

  if aws secretsmanager describe-secret --secret-id "$OIDC_SECRET_NAME" --region "$AWS_REGION" &>/dev/null; then
    aws secretsmanager put-secret-value \
      --secret-id "$OIDC_SECRET_NAME" \
      --secret-string "$OIDC_JSON" \
      --region "$AWS_REGION" 2>&1 | tee -a "$LOG_FILE"
  else
    aws secretsmanager create-secret \
      --name "$OIDC_SECRET_NAME" \
      --secret-string "$OIDC_JSON" \
      --region "$AWS_REGION" 2>&1 | tee -a "$LOG_FILE"
  fi
  log "OIDC secret created"
else
  warn "No OIDC credentials provided — Cognito will use manual user creation"
fi

# ---------------------------------------------------------------------------
# Phase 6: Deploy frontend infrastructure (Cognito, CloudFront, WAF, S3)
# ---------------------------------------------------------------------------
step 6 "Deploying frontend CDK stacks (Cognito, CloudFront, WAF, S3)"

FRONTEND_DIR="$REPO_ROOT/frontend/infrastructure"

log "Installing frontend infrastructure dependencies"
run_cmd yarn --cwd "$FRONTEND_DIR" install --frozen-lockfile

FE_CDK_CONTEXT=(
  -c "environment=$ENVIRONMENT"
  -c "account=$AWS_ACCOUNT_ID"
  -c "region=$AWS_REGION"
  -c "app-name=$APP_NAME"
  -c "deployment-qualifier=$DEPLOYMENT_QUALIFIER"
)

if [ -n "$CERT_ARN" ]; then
  FE_CDK_CONTEXT+=(-c "cert-arn=$CERT_ARN")
fi
if [ -n "$CUSTOM_DOMAIN" ]; then
  FE_CDK_CONTEXT+=(-c "use-custom-domain=$CUSTOM_DOMAIN")
fi
if [ -n "$CERT_ARN_US_EAST_1" ]; then
  FE_CDK_CONTEXT+=(-c "cert-arn-login=$CERT_ARN_US_EAST_1")
fi

log "Deploying frontend CDK stacks"
(
  cd "$FRONTEND_DIR"
  run_cmd cdk deploy --all --require-approval never --force \
    "${FE_CDK_CONTEXT[@]}"
)

# ---------------------------------------------------------------------------
# Phase 7: Deploy backend infrastructure (Lambda, API Gateway, DynamoDB, EventBridge)
# ---------------------------------------------------------------------------
step 7 "Deploying backend CDK stacks (Lambda, API Gateway, DynamoDB, EventBridge)"

log "Installing backend Python dependencies"
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  uv venv "$BACKEND_DIR/.venv" --python 3.13
fi
source "$BACKEND_DIR/.venv/bin/activate"
UV_PROJECT_ENVIRONMENT="$BACKEND_DIR/.venv" uv sync --project "$BACKEND_DIR" --group dev --group test 2>&1 | tail -1 | tee -a "$LOG_FILE"

BE_CDK_CONTEXT=(
  -c "environment=$ENVIRONMENT"
  -c "account=$AWS_ACCOUNT_ID"
  -c "region=$AWS_REGION"
  -c "image-service-account=$AWS_ACCOUNT_ID"
  -c "image-service-region=$AWS_REGION"
  -c "catalog-service-account=$AWS_ACCOUNT_ID"
  -c "catalog-service-region=$AWS_REGION"
  -c "organization-id=$ORG_ID"
)

if [ -n "$API_CUSTOM_DOMAIN" ]; then
  BE_CDK_CONTEXT+=(-c "use-custom-domain=$API_CUSTOM_DOMAIN")
fi
if [ -n "$CERT_ARN" ]; then
  BE_CDK_CONTEXT+=(-c "cert-arn=$CERT_ARN")
fi

FE_STACK_NAME="${APP_NAME}-${ENVIRONMENT}"
FE_OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name "$FE_STACK_NAME" \
  --query 'Stacks[0].Outputs' \
  --output json --region "$AWS_REGION" 2>/dev/null || echo "[]")

CORS_ORIGIN=$(echo "$FE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="cdncustomfqdnoutput") | .OutputValue // empty')
if [ -z "$CORS_ORIGIN" ] || [ "$CORS_ORIGIN" = "not available" ]; then
  CORS_ORIGIN=$(echo "$FE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="cdnfqdnoutput") | .OutputValue // empty')
fi
if [ -n "$CORS_ORIGIN" ]; then
  CORS_ORIGIN="https://${CORS_ORIGIN}"
  log "Setting CORS origin to $CORS_ORIGIN"
  sed -i.bak "s|\"rest-api-cors-origins\": \"[^\"]*\"|\"rest-api-cors-origins\": \"${CORS_ORIGIN}\"|" "$BACKEND_CONFIG"
  rm -f "${BACKEND_CONFIG}.bak"
else
  warn "Could not determine CloudFront URL — CORS origin will remain as wildcard (*)"
fi

log "Deploying backend CDK stacks"
(
  cd "$BACKEND_DIR"
  cp cdk-backend.json cdk.json
  rm -f cdk.context.json
  rm -rf cdk.out
  EXISTING_STACKS=$(aws cloudformation list-stacks \
    --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE \
    --query "StackSummaries[?starts_with(StackName, '${ORG_PREFIX}-${APP_PREFIX}')].StackName" \
    --output text --region "$AWS_REGION" 2>/dev/null || echo "")
  if [ -z "$EXISTING_STACKS" ]; then
    CDK_CONCURRENCY=1
    log "First deployment detected — using --concurrency 1 to avoid race conditions"
  else
    CDK_CONCURRENCY=10
  fi

  run_cmd cdk deploy --all --require-approval never --force \
    --concurrency $CDK_CONCURRENCY \
    "${BE_CDK_CONTEXT[@]}"
  rm -f cdk.json
)

deactivate

# ---------------------------------------------------------------------------
# Phase 8: Build and deploy frontend web application
# ---------------------------------------------------------------------------
step 8 "Building frontend web application and uploading to S3"

WEB_DIR="$REPO_ROOT/frontend/web"

log "Generating frontend configuration (aws-exports.js)"
(
  cd "$WEB_DIR"
  APP_NAME="$APP_NAME" \
  BACKEND_APP_NAME="$BACKEND_APP_NAME" \
  ENVIRONMENT_NAME="$ENVIRONMENT" \
  AWS_DEFAULT_REGION="$AWS_REGION" \
  AWS_REGION_BE_API="$AWS_REGION" \
  UPLOAD_ENV="remote" \
  bash configure_auth.sh
)

log "Installing web app dependencies"
run_cmd yarn --cwd "$WEB_DIR" install --frozen-lockfile
log "Building web app"
REACT_APP_ENVIRONMENT="$ENVIRONMENT" run_cmd yarn --cwd "$WEB_DIR" build

# Upload to S3 and invalidate CloudFront
S3_BUCKET=$(echo "$FE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="icfrontends3output") | .OutputValue')
CF_DIST_ID=$(echo "$FE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="cdndistributionidoutput") | .OutputValue')

if [ -z "$S3_BUCKET" ] || [ "$S3_BUCKET" = "null" ]; then
  S3_BUCKET=$(echo "$FE_OUTPUTS" | jq -r '.[] | select(.OutputKey | test("s3bucketname"; "i")) | .OutputValue' | head -1)
fi

if [ -n "$S3_BUCKET" ] && [ "$S3_BUCKET" != "null" ]; then
  log "Uploading web app to s3://$S3_BUCKET"
  run_cmd aws s3 sync "$WEB_DIR/dist" "s3://$S3_BUCKET" --delete --region "$AWS_REGION"

  if [ -n "$CF_DIST_ID" ] && [ "$CF_DIST_ID" != "null" ]; then
    log "Invalidating CloudFront distribution $CF_DIST_ID"
    aws cloudfront create-invalidation \
      --distribution-id "$CF_DIST_ID" \
      --paths "/*" \
      --region us-east-1 2>&1 | tee -a "$LOG_FILE"
  fi
else
  warn "Could not determine S3 bucket from stack outputs. Upload frontend manually."
  warn "Stack outputs: $(echo "$FE_OUTPUTS" | jq -r '.[].OutputKey')"
fi

# ---------------------------------------------------------------------------
# Phase 9: Seed DynamoDB (admin user + default program)
# ---------------------------------------------------------------------------
step 9 "Seeding DynamoDB (admin user + default program)"

PROGRAM_ID="prog-73488"
NOW=$(date -u +"%Y-%m-%dT%H:%M:%S.000000+00:00")

log "Creating program: $PROGRAM_ID"
aws dynamodb put-item \
  --table-name "$PROJECTS_TABLE" \
  --region "$AWS_REGION" \
  --item "{
    \"PK\": {\"S\": \"PROJECT#${PROGRAM_ID}\"},
    \"SK\": {\"S\": \"PROJECT#${PROGRAM_ID}\"},
    \"createDate\": {\"S\": \"${NOW}\"},
    \"entity\": {\"S\": \"PROJECT\"},
    \"isActive\": {\"BOOL\": true},
    \"lastUpdateDate\": {\"S\": \"${NOW}\"},
    \"projectDescription\": {\"S\": \"Default program\"},
    \"projectId\": {\"S\": \"${PROGRAM_ID}\"},
    \"projectName\": {\"S\": \"$(echo "${ENVIRONMENT}" | awk '{print toupper(substr($0,1,1)) substr($0,2)}') Program\"}
  }" 2>&1 | tee -a "$LOG_FILE"

log "Creating admin user: $ADMIN_USER_ID ($ADMIN_EMAIL)"
aws dynamodb put-item \
  --table-name "$PROJECTS_TABLE" \
  --region "$AWS_REGION" \
  --item "{
    \"PK\": {\"S\": \"USER#${ADMIN_USER_ID}\"},
    \"SK\": {\"S\": \"PROJECT#${PROGRAM_ID}\"},
    \"activeDirectoryGroups\": {\"L\": []},
    \"activeDirectoryGroupStatus\": {\"S\": \"PENDING\"},
    \"projectId\": {\"S\": \"${PROGRAM_ID}\"},
    \"roles\": {\"L\": [{\"S\": \"ADMIN\"}]},
    \"userEmail\": {\"S\": \"${ADMIN_EMAIL}\"},
    \"userId\": {\"S\": \"${ADMIN_USER_ID}\"}
  }" 2>&1 | tee -a "$LOG_FILE"

log "DynamoDB seeding complete (projects)"

# Seed authorization table with admin assignment
AUTH_TABLE="${ORG_PREFIX}-${APP_PREFIX}-authorization-table-${ENVIRONMENT}"

log "Creating admin authorization assignment: $ADMIN_USER_ID → $PROGRAM_ID (ADMIN)"
aws dynamodb put-item \
  --table-name "$AUTH_TABLE" \
  --region "$AWS_REGION" \
  --item "{
    \"PK\": {\"S\": \"USER#${ADMIN_USER_ID}\"},
    \"SK\": {\"S\": \"PROJECT#${PROGRAM_ID}\"},
    \"userId\": {\"S\": \"${ADMIN_USER_ID}\"},
    \"projectId\": {\"S\": \"${PROGRAM_ID}\"},
    \"roles\": {\"L\": [{\"S\": \"ADMIN\"}]},
    \"userEmail\": {\"S\": \"${ADMIN_EMAIL}\"},
    \"activeDirectoryGroups\": {\"L\": []},
    \"groupMemberships\": {\"L\": [{\"S\": \"VEW_USERS\"}]}
  }" 2>&1 | tee -a "$LOG_FILE"

log "DynamoDB seeding complete"

# ---------------------------------------------------------------------------
# Phase 10: Spoke account onboarding (optional)
# ---------------------------------------------------------------------------
if [ -n "${SPOKE_ACCOUNT_ID:-}" ]; then
  step 10 "Onboarding spoke account $SPOKE_ACCOUNT_ID (CloudFormation bootstrap)"

  SPOKE_TEMPLATE="$REPO_ROOT/backend/setup/prerequisites/vew-spoke-account-bootstrap.yml"
  SPOKE_STACK_NAME="VEW-Spoke-Bootstrap"

  if [ ! -f "$SPOKE_TEMPLATE" ]; then
    err "Spoke bootstrap template not found: $SPOKE_TEMPLATE"
  fi

  # Switch to spoke account credentials
  activate_spoke_credentials

  # Verify spoke credentials target the correct account
  SPOKE_CALLER_ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null || echo "")
  if [ "$SPOKE_CALLER_ACCOUNT" != "$SPOKE_ACCOUNT_ID" ]; then
    err "Spoke account credential targets account $SPOKE_CALLER_ACCOUNT, expected $SPOKE_ACCOUNT_ID"
  fi
  log "Spoke credentials verified: account $SPOKE_ACCOUNT_ID"

  if [ -n "$SPOKE_VPC_ID" ]; then
    aws ec2 describe-vpcs --vpc-ids "$SPOKE_VPC_ID" --region "$AWS_REGION" &>/dev/null \
      || err "VPC '$SPOKE_VPC_ID' not found in spoke account $SPOKE_ACCOUNT_ID ($AWS_REGION)"
    log "Spoke VPC verified: $SPOKE_VPC_ID"
  fi

  log "Deploying spoke bootstrap stack via CloudFormation into account $SPOKE_ACCOUNT_ID"
  aws cloudformation deploy \
    --template-file "$SPOKE_TEMPLATE" \
    --stack-name "$SPOKE_STACK_NAME" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$AWS_REGION" \
    --parameter-overrides \
      "Qualifier=$SPOKE_CDK_QUALIFIER" \
      "ToolkitStackName=VEWCDKToolkit" \
      "WebApplicationAccountId=$AWS_ACCOUNT_ID" \
      "WebApplicationEnvironment=$ENVIRONMENT" \
      "WebApplicationRolePrefix=${ORG_PREFIX}-${APP_PREFIX}-projects" \
      "VPCIdParameterValue=$SPOKE_VPC_ID" \
    2>&1 | tee -a "$LOG_FILE"

  # Switch back to hub account credentials
  activate_hub_credentials
  log "Spoke account bootstrap complete"
else
  log "No spoke account configured — skipping"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} VEW deployment complete${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Environment:  $ENVIRONMENT"
echo "  Account:      $AWS_ACCOUNT_ID"
echo "  Region:       $AWS_REGION"
echo ""

CDN_FQDN=$(echo "$FE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="cdnfqdnoutput") | .OutputValue' 2>/dev/null || echo "")
CDN_CUSTOM=$(echo "$FE_OUTPUTS" | jq -r '.[] | select(.OutputKey=="cdncustomfqdnoutput") | .OutputValue' 2>/dev/null || echo "")

if [ -n "$CDN_CUSTOM" ] && [ "$CDN_CUSTOM" != "not available" ] && [ "$CDN_CUSTOM" != "null" ]; then
  echo "  URL:          https://$CDN_CUSTOM"
elif [ -n "$CDN_FQDN" ] && [ "$CDN_FQDN" != "null" ]; then
  echo "  URL:          https://$CDN_FQDN"
fi

echo "  Admin user:   $ADMIN_USER_ID ($ADMIN_EMAIL)"
echo ""
echo "  Log file:     $LOG_FILE"
echo "  Config file:  $CONFIG_OUT"
echo ""

if [ -n "$CUSTOM_DOMAIN" ]; then
  echo -e "${YELLOW}  DNS records still need to be created:${NC}"
  echo "    $CUSTOM_DOMAIN -> CNAME to CloudFront distribution"
  if [ -n "$API_CUSTOM_DOMAIN" ]; then
    echo "    $API_CUSTOM_DOMAIN -> CNAME to API ALB"
  fi
  echo ""
fi

if [ -z "$OIDC_CLIENT_ID" ]; then
  echo -e "${YELLOW}  No OIDC configured. Create a Cognito user manually by running the following command:${NC}"
  POOL_ID=$(aws ssm get-parameter \
    --name "/${ORG_PREFIX}-${APP_PREFIX}-ui-${ENVIRONMENT}/user-pool-id" \
    --query 'Parameter.Value' --output text \
    --region "$AWS_REGION" 2>/dev/null || echo "unknown")
  echo "    aws cognito-idp admin-create-user \\"
  echo "      --user-pool-id $POOL_ID \\"
  echo "      --username $ADMIN_EMAIL \\"
  echo "      --user-attributes Name=email,Value=$ADMIN_EMAIL Name=email_verified,Value=true Name=custom:user_tid,Value=$ADMIN_USER_ID \\"
  echo "      --region $AWS_REGION"
  echo ""
fi

log "Done."
