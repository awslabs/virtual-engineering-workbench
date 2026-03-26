#!/bin/bash

# workaround for missing feature
# https://github.com/yarnpkg/yarn/issues/6669
# run the following command to generate an ignore file:
# 	yarn audit --json --level high | grep auditAdvisory > yarn-audit-known-issues

set -u

echo Scanning NPM packages

set +e
output=$(yarn npm audit --json --severity high)
result=$?

mkdir -p code_scanning_reports
echo "$output" >> code_scanning_reports/yarn-audit.json

set -e

if [ $result -eq 0 ]; then
	echo No vulnerabilities found.
	exit 0
fi

if [ -f yarn-audit-known-issues ] && echo "$output" | grep auditAdvisory | diff -q yarn-audit-known-issues - > /dev/null 2>&1; then
	echo
	echo Ignorning known vulnerabilities
        jq --slurp '.[].data.advisory | {findings, title, severity, patched_versions}' yarn-audit-known-issues
	exit 0
fi

audit_summary=$(jq '. | select(.type=="auditSummary") | .data.vulnerabilities' <<< $output)
findings_critical=$(jq '.critical' <<< $audit_summary)
findings_high=$(jq '.high' <<< $audit_summary)

echo
echo Audit summary:
echo 
echo "$audit_summary"

if [[ $findings_critical -ne 0 ]] || [[ $findings_high -ne 0 ]]; then
	echo "Critical or high vulnerabilities found!"
	exit "$result"
fi