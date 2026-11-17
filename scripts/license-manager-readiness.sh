#!/usr/bin/env bash

# Reports one of: active, disabled, pending-not-active,
# member-not-distributor<TAB>management-account-id, or unknown.
# This function is read-only.
license_manager_readiness() {
  local region=$1 account_id=$2
  local settings organization enabled share_arn management_account resource_owner shares active_count

  if ! settings=$(aws license-manager get-service-settings --region "$region" --output json 2>/dev/null); then
    echo "unknown"
    return 0
  fi

  enabled=$(jq -r '.OrganizationConfiguration.EnableIntegration // false' <<<"$settings") || {
    echo "unknown"
    return 0
  }
  share_arn=$(jq -r '.LicenseManagerResourceShareArn // empty' <<<"$settings") || {
    echo "unknown"
    return 0
  }

  if ! organization=$(aws organizations describe-organization --output json 2>/dev/null); then
    if [ "$enabled" = "true" ]; then
      echo "unknown"
    else
      echo "disabled"
    fi
    return 0
  fi
  management_account=$(jq -r '.Organization.ManagementAccountId // .Organization.MasterAccountId // empty' \
    <<<"$organization") || {
    echo "unknown"
    return 0
  }

  if [ -z "$management_account" ]; then
    echo "unknown"
  elif [ "$enabled" != "true" ]; then
    echo "disabled"
  elif [ -z "$share_arn" ]; then
    echo "pending-not-active"
  else
    if [ "$account_id" = "$management_account" ]; then
      resource_owner="SELF"
    else
      resource_owner="OTHER-ACCOUNTS"
    fi

    if ! shares=$(aws ram get-resource-shares \
      --resource-owner "$resource_owner" \
      --resource-share-arns "$share_arn" \
      --region "$region" \
      --output json 2>/dev/null); then
      echo "unknown"
      return 0
    fi

    active_count=$(jq --arg arn "$share_arn" --arg owner "$management_account" \
      '[.resourceShares[]? | select(.resourceShareArn == $arn and .status == "ACTIVE" and .owningAccountId == $owner)] | length' \
      <<<"$shares") || {
      echo "unknown"
      return 0
    }
    if [ "$active_count" -gt 0 ] && [ "$account_id" != "$management_account" ]; then
      printf 'member-not-distributor\t%s\n' "$management_account"
    elif [ "$active_count" -gt 0 ]; then
      echo "active"
    else
      echo "pending-not-active"
    fi
  fi
}
