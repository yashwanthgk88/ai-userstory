#!/usr/bin/env bash
# SecureReq AI CLI - Security analysis gate for CI/CD pipelines
# Usage: ./securereq-cli.sh <project_id> [risk_threshold]
#
# Environment variables:
#   SECUREREQ_API_URL  - API base URL (default: https://ai-userstory-production.up.railway.app/api)
#   SECUREREQ_API_KEY  - API key (required)
#
# Exit codes:
#   0 - All analyses passed (risk scores below threshold)
#   1 - One or more analyses exceeded risk threshold (security gate failed)
#   2 - API error or misconfiguration

set -euo pipefail

PROJECT_ID="${1:?Usage: securereq-cli.sh <project_id> [risk_threshold]}"
RISK_THRESHOLD="${2:-70}"
API_URL="${SECUREREQ_API_URL:-https://ai-userstory-production.up.railway.app/api}"
API_KEY="${SECUREREQ_API_KEY:?SECUREREQ_API_KEY environment variable is required}"

echo "=== SecureReq AI Security Gate ==="
echo "Project: ${PROJECT_ID}"
echo "Risk Threshold: ${RISK_THRESHOLD}"
echo "API: ${API_URL}"
echo ""

# Trigger bulk analysis
echo "Triggering security analysis..."
RESPONSE=$(curl -sf -X POST \
  "${API_URL}/projects/${PROJECT_ID}/analyze" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  2>&1) || {
    echo "ERROR: API request failed"
    echo "${RESPONSE}"
    exit 2
  }

TOTAL=$(echo "${RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])")
echo "Analyzed ${TOTAL} stories"
echo ""

# Check results
FAILED=0
echo "${RESPONSE}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
failed = 0
for r in data['results']:
    status = r['status']
    title = r['story_title']
    risk = r.get('risk_score', 0)
    icon = '✓' if status == 'success' and risk < ${RISK_THRESHOLD} else '✗'
    if status == 'error':
        print(f'  {icon} {title}: ERROR - {r.get(\"error\", \"unknown\")}')
        failed += 1
    elif risk >= ${RISK_THRESHOLD}:
        print(f'  {icon} {title}: RISK {risk} (threshold: ${RISK_THRESHOLD})')
        failed += 1
    else:
        print(f'  {icon} {title}: RISK {risk} - OK')
print()
if failed > 0:
    print(f'FAILED: {failed} story(ies) exceeded risk threshold or had errors')
    sys.exit(1)
else:
    print(f'PASSED: All {len(data[\"results\"])} stories below risk threshold')
    sys.exit(0)
" || FAILED=$?

exit ${FAILED}
