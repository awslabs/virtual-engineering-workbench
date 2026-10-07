#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

if ! source "$REPO_ROOT/scripts/deploy-regions.sh"; then
  fail "deployment region helpers must be available"
fi

actual=$(normalize_workbench_regions " us-east-1,eu-north-1, us-east-1 ")
[[ "$actual" == "us-east-1,eu-north-1" ]] || \
  fail "expected trimmed, deduplicated regions; got '$actual'"

if normalize_workbench_regions "us-east-1,not-a-region" >/dev/null 2>&1; then
  fail "expected malformed regions to be rejected"
fi

for invalid_regions in "" "," "us-east-1," ",us-east-1" "us-east-1,,eu-west-1" "us-east-1, ,eu-west-1"; do
  if normalize_workbench_regions "$invalid_regions" >/dev/null 2>&1; then
    fail "expected empty region entries to be rejected: '$invalid_regions'"
  fi
done

actual=$(workbench_regions_python_list "us-east-1,eu-north-1")
[[ "$actual" == '["us-east-1", "eu-north-1"]' ]] || \
  fail "expected a Python list literal; got '$actual'"

actual=$(workbench_regions_lines "us-east-1,eu-north-1")
[[ "$actual" == $'us-east-1\neu-north-1' ]] || \
  fail "expected one region per line; got '$actual'"

declare -F required_bootstrap_regions >/dev/null || \
  fail "deployment region helpers must determine required bootstrap regions"

actual=$(required_bootstrap_regions "eu-west-1" "eu-north-1,eu-west-1" "false")
[[ "$actual" == "eu-west-1,eu-north-1,us-east-1" ]] || \
  fail "public deployments must bootstrap primary, workbench, and CloudFront regions; got '$actual'"

actual=$(required_bootstrap_regions "eu-west-1" "eu-north-1" "true")
[[ "$actual" == "eu-west-1,eu-north-1" ]] || \
  fail "private deployments must bootstrap primary and workbench regions; got '$actual'"

test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT
mkdir -p "$test_root/scripts" "$test_root/bin"
cp "$REPO_ROOT/deploy.sh" "$test_root/deploy.sh"
cp "$REPO_ROOT/scripts/deploy-regions.sh" "$test_root/scripts/deploy-regions.sh"

declare -F patch_workbench_regions_config >/dev/null || \
  fail "deployment region helpers must patch the backend configuration"

region_config="$test_root/backend-config.py"
printf '%s\n' '    "enabled-workbench-regions": ["us-east-1"],' > "$region_config"
patch_workbench_regions_config "$region_config" "us-east-1,eu-north-1"
actual=$(sed -n '/enabled-workbench-regions/p' "$region_config")
[[ "$actual" == '    "enabled-workbench-regions": ["us-east-1", "eu-north-1"],' ]] || \
  fail "backend config must receive the complete region list; got '$actual'"

cat > "$test_root/config.env" <<'EOF'
AWS_ACCOUNT_ID="123456789012"
AWS_REGION="us-east-1"
ENABLED_WORKBENCH_REGIONS=" us-east-1,eu-north-1,us-east-1 "
ENVIRONMENT="dev"
ORG_PREFIX="test"
APP_PREFIX="wb"
ADMIN_EMAIL="admin@test.invalid"
ADMIN_USER_ID="ADMIN"
AWS_PROFILE_HUB="default"
OIDC_CLIENT_ID=""
OIDC_CLIENT_SECRET=""
OIDC_ISSUER_URL=""
OIDC_USER_ID_CLAIM="sub"
OIDC_LOGOUT_URL=""
CERT_ARN=""
CERT_ARN_US_EAST_1=""
CUSTOM_DOMAIN=""
API_CUSTOM_DOMAIN=""
PRIVATE_DEPLOYMENT="false"
PRIVATE_DNS_AUTOMATE="true"
PRIVATE_DNS_ZONE=""
SPOKE_ACCOUNT_ID=""
SPOKE_VPC_ID=""
EOF

cat > "$test_root/bin/aws" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "--version" ]; then
  echo "aws-cli/2.20.0 Python/3.13.0"
elif [ "${1:-} ${2:-}" = "sts get-caller-identity" ]; then
  echo "123456789012"
elif [ "${1:-} ${2:-}" = "organizations describe-organization" ]; then
  echo "o-test123456"
else
  echo "unexpected aws invocation: $*" >&2
  exit 1
fi
EOF

cat > "$test_root/bin/cdk" <<'EOF'
#!/usr/bin/env bash
echo "2.1000.0"
EOF
cat > "$test_root/bin/node" <<'EOF'
#!/usr/bin/env bash
echo "v20.0.0"
EOF
cat > "$test_root/bin/python" <<'EOF'
#!/usr/bin/env bash
echo "Python 3.13.0"
EOF
cat > "$test_root/bin/uv" <<'EOF'
#!/usr/bin/env bash
echo "uv 0.8.0"
EOF
cat > "$test_root/bin/jq" <<'EOF'
#!/usr/bin/env bash
echo "jq-1.7"
EOF
cat > "$test_root/bin/yarn" <<'EOF'
#!/usr/bin/env bash
echo "4.14.0"
EOF
cat > "$test_root/bin/docker" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "info" ]; then
  exit 0
fi
echo "Docker version 27.0.0"
EOF
chmod +x "$test_root/bin/"*

dry_run_output=$(
  cd "$test_root"
  PATH="$test_root/bin:$PATH" \
    AWS_ACCESS_KEY_ID=test \
    AWS_SECRET_ACCESS_KEY=test \
    bash ./deploy.sh --config ./config.env --dry-run
)

[[ "$dry_run_output" == *"Workbench regions: us-east-1,eu-north-1"* ]] || \
  fail "dry-run summary must show normalized workbench regions"

saved_regions=$(sed -n 's/^ENABLED_WORKBENCH_REGIONS="\(.*\)"$/\1/p' "$test_root/.deploy-config-dev")
[[ "$saved_regions" == "us-east-1,eu-north-1" ]] || \
  fail "saved config must contain normalized workbench regions; got '$saved_regions'"

sed '/^ENABLED_WORKBENCH_REGIONS=/d' "$test_root/config.env" > "$test_root/default-regions.env"
default_output=$(
  cd "$test_root"
  PATH="$test_root/bin:$PATH" \
    AWS_ACCESS_KEY_ID=test \
    AWS_SECRET_ACCESS_KEY=test \
    bash ./deploy.sh --config ./default-regions.env --dry-run --yes
)
[[ "$default_output" == *"Workbench regions: us-east-1"* ]] || \
  fail "an omitted region list must default to the primary AWS region"

echo "PASS: deployment region helpers"
