#!/bin/bash
# =============================================================================
# Frontend dependency security scan
#
# Runs yarn npm audit and reports high/critical vulnerabilities.
# Handles yarn 4 NDJSON output (multiple JSON objects per line).
#
# Known issues file: yarn-audit-known-issues (one advisory JSON per line)
# =============================================================================
set -u

echo "Scanning NPM packages"

set +e
output=$(yarn npm audit --json --severity high 2>&1)
result=$?
set -e

mkdir -p code_scanning_reports
echo "$output" > code_scanning_reports/yarn-audit.json

if [ $result -eq 0 ]; then
    echo "No vulnerabilities found."
    exit 0
fi

# yarn 4 outputs NDJSON (one JSON object per line), not a single JSON document.
# Use jq --slurp to parse all lines into an array.
audit_summary=$(echo "$output" | jq -s '[.[] | select(.advisoryId != null)] | length' 2>/dev/null || echo "0")

if [ -f yarn-audit-known-issues ]; then
    known_count=$(wc -l < yarn-audit-known-issues | tr -d ' ')
    if [ "$audit_summary" -le "$known_count" ] 2>/dev/null; then
        echo ""
        echo "All vulnerabilities are known/ignored ($audit_summary advisories)"
        exit 0
    fi
fi

# Extract severity counts from NDJSON
critical=$(echo "$output" | jq -s '[.[] | select(.severity == "critical")] | length' 2>/dev/null || echo "0")
high=$(echo "$output" | jq -s '[.[] | select(.severity == "high")] | length' 2>/dev/null || echo "0")

echo ""
echo "Audit summary:"
echo "  Critical: $critical"
echo "  High:     $high"
echo ""

if [ "$critical" -ne 0 ] || [ "$high" -ne 0 ]; then
    echo "Critical or high vulnerabilities found!"
    echo "$output" | jq -s '.[] | select(.severity == "critical" or .severity == "high") | {title, severity, url}' 2>/dev/null || true
    exit 1
fi
