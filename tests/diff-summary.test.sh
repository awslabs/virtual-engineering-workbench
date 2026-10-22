#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUMMARY="$REPO_ROOT/scripts/diff-summary.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SUMMARY" ]] || fail "diff-summary.py must exist"

# Two apps, as a VEW diff produces: cdk reports a total per app, never per run.
cat >"$WORK/two-apps.txt" <<'DIFF'
Stack FrontendStack (myorg-vew-ui-dev) (aws://111122223333/eu-north-1)
Resources
[~] AWS::Lambda::Function Handler Handler1234
 └─ [~] Content (requires replacement)
[-] AWS::Lambda::Version Handler/CurrentVersion HandlerVersion99 orphan

✨  Number of stacks with differences: 1

Stack BackendStack (myorg-vew-api-dev) (aws://111122223333/eu-north-1)
IAM Statement Changes
Resources
[+] AWS::SNS::Topic Events Events4321
[~] AWS::CloudWatch::Alarm AlarmFailed AlarmFailed777 may be replaced
[-] AWS::ApiGateway::Deployment Api/Deployment ApiDeployment55 destroy

Stack UnchangedStack (myorg-vew-dns-dev) (aws://111122223333/eu-north-1)
There were no differences

✨  Number of stacks with differences: 1
DIFF

out="$("$SUMMARY" "$WORK/two-apps.txt")" || fail "a well-formed diff must summarise"

grep -q '2 stack(s) with differences, 1 unchanged' <<<"$out" || \
  fail "expected totals across both apps and the unchanged stack; got:
$out"
grep -q '2 replacement(s)' <<<"$out" || fail "expected both replacements counted; got:
$out"
grep -q '1 orphaned (retained), 1 destroyed' <<<"$out" || \
  fail "expected orphan and destroy counted apart; got:
$out"
grep -q 'No resource holding data is replaced or removed' <<<"$out" || \
  fail "expected an all-clear when nothing stateful changes; got:
$out"

# A replaced table and a removed bucket both lose data and must be named.
cat >"$WORK/at-risk.txt" <<'DIFF'
Stack DataStack (myorg-vew-data-dev) (aws://111122223333/eu-north-1)
Resources
[~] AWS::DynamoDB::Table Projects ProjectsTable11 may be replaced
[-] AWS::S3::Bucket Artifacts ArtifactsBucket22 destroy

✨  Number of stacks with differences: 1
DIFF

out="$("$SUMMARY" "$WORK/at-risk.txt")" || fail "an at-risk diff must still summarise"
grep -q 'DATA AT RISK' <<<"$out" || fail "expected a data-at-risk warning; got:
$out"
grep -q 'replaced AWS::DynamoDB::Table' <<<"$out" || fail "expected the replaced table named; got:
$out"
grep -q 'removed AWS::S3::Bucket' <<<"$out" || fail "expected the removed bucket named; got:
$out"

# cdk's own totals are the checksum. Disagreement means the parse is wrong,
# and a wrong summary is worse than none.
sed 's/Number of stacks with differences: 1/Number of stacks with differences: 7/' \
  "$WORK/two-apps.txt" >"$WORK/mismatch.txt"
if "$SUMMARY" "$WORK/mismatch.txt" >/dev/null 2>&1; then
  fail "expected a refusal when cdk's totals disagree with the parse"
fi

# Output format moved: no stack headers to anchor on.
sed 's/^Stack /Stakk /' "$WORK/two-apps.txt" >"$WORK/no-headers.txt"
if "$SUMMARY" "$WORK/no-headers.txt" >/dev/null 2>&1; then
  fail "expected a refusal when no stack headers are found"
fi

# Output format moved: no totals to check against.
grep -v 'Number of stacks with differences' "$WORK/two-apps.txt" >"$WORK/no-count.txt"
if "$SUMMARY" "$WORK/no-count.txt" >/dev/null 2>&1; then
  fail "expected a refusal when cdk reports no totals"
fi

: >"$WORK/empty.txt"
if "$SUMMARY" "$WORK/empty.txt" >/dev/null 2>&1; then
  fail "expected a refusal on empty input"
fi

# A refusal explains itself on stderr and leaves stdout clean, so a caller
# teeing the summary into a report never captures a half-truth.
stdout="$("$SUMMARY" "$WORK/empty.txt" 2>/dev/null || true)"
[[ -z "$stdout" ]] || fail "a refusal must print nothing to stdout; got '$stdout'"

echo "PASS: diff-summary"
