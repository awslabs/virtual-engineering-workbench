#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/license-manager-readiness.sh
source "$REPO_ROOT/scripts/license-manager-readiness.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

ENABLED=true
SHARE_ARN="arn:aws:ram:us-east-1:123456789012:resource-share/lm-123"
RAM_SHARE_ARN="$SHARE_ARN"
MANAGEMENT_ACCOUNT="123456789012"
SHARE_STATUS="ACTIVE"
SHARE_OWNER="123456789012"
EXPECTED_RESOURCE_OWNER="SELF"

aws() {
  case "${1:-} ${2:-}" in
    "license-manager get-service-settings")
      jq -n --argjson enabled "$ENABLED" --arg share "$SHARE_ARN" '
        {OrganizationConfiguration: {EnableIntegration: $enabled}}
        + if $share == "" then {} else {LicenseManagerResourceShareArn: $share} end
      '
      ;;
    "organizations describe-organization")
      jq -n --arg account "$MANAGEMENT_ACCOUNT" '{Organization: {MasterAccountId: $account}}'
      ;;
    "ram get-resource-shares")
      [[ " $* " == *" --resource-owner $EXPECTED_RESOURCE_OWNER "* ]] || {
        echo "wrong RAM resource owner in: $*" >&2
        return 1
      }
      jq -n \
        --arg arn "$RAM_SHARE_ARN" \
        --arg owner "$SHARE_OWNER" \
        --arg status "$SHARE_STATUS" \
        '{resourceShares: [{resourceShareArn: $arn, owningAccountId: $owner, status: $status}]}'
      ;;
    *)
      echo "unexpected aws invocation: $*" >&2
      return 1
      ;;
  esac
}

actual=$(license_manager_readiness "us-east-1" "123456789012")
[[ "$actual" == "active" ]] || fail "expected active; got '$actual'"

ENABLED=false
actual=$(license_manager_readiness "us-east-1" "123456789012")
[[ "$actual" == "disabled" ]] || fail "expected disabled; got '$actual'"

ENABLED=true
SHARE_ARN=""
actual=$(license_manager_readiness "us-east-1" "123456789012")
[[ "$actual" == "pending-not-active" ]] || fail "expected pending without a share; got '$actual'"

SHARE_ARN="arn:aws:ram:us-east-1:123456789012:resource-share/lm-123"
SHARE_STATUS="PENDING"
actual=$(license_manager_readiness "us-east-1" "123456789012")
[[ "$actual" == "pending-not-active" ]] || fail "expected pending for a non-active share; got '$actual'"

SHARE_STATUS="ACTIVE"
RAM_SHARE_ARN="arn:aws:ram:us-east-1:123456789012:resource-share/unrelated"
actual=$(license_manager_readiness "us-east-1" "123456789012")
[[ "$actual" == "pending-not-active" ]] || fail "expected pending for the wrong share ARN; got '$actual'"

RAM_SHARE_ARN="$SHARE_ARN"
SHARE_OWNER="999999999999"
actual=$(license_manager_readiness "us-east-1" "123456789012")
[[ "$actual" == "pending-not-active" ]] || fail "expected pending for a wrongly owned share; got '$actual'"

SHARE_OWNER="999999999999"
MANAGEMENT_ACCOUNT="999999999999"
EXPECTED_RESOURCE_OWNER="OTHER-ACCOUNTS"
actual=$(license_manager_readiness "us-east-1" "123456789012")
[[ "$actual" == $'member-not-distributor\t999999999999' ]] || \
  fail "expected member-not-distributor; got '$actual'"

echo "PASS: License Manager readiness reporting"
