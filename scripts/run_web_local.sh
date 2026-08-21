#!/bin/bash
set -euo pipefail

ROOT="${AIOS_ROOT:-$HOME/LocalProjects/aios}"
cd "$ROOT"

PROJECT="${GOOGLE_CLOUD_PROJECT:-aios-jdh}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"
API_SERVICE="${AIOS_API_SERVICE:-aios-api}"

export AIOS_WEB_USERNAME="${AIOS_WEB_USERNAME:-aios}"
export AIOS_WEB_PASSWORD="${AIOS_WEB_PASSWORD:-local}"
export AIOS_WEB_SESSION_SECRET="${AIOS_WEB_SESSION_SECRET:-local-dev-session-secret-change-me}"
export AIOS_WEB_COOKIE_SECURE="false"
export AIOS_LOCAL_IMPERSONATE_SERVICE_ACCOUNT="${AIOS_LOCAL_IMPERSONATE_SERVICE_ACCOUNT:-aios-web-runtime@${PROJECT}.iam.gserviceaccount.com}"

if [ -z "${AIOS_API_URL:-}" ]; then
  export AIOS_API_URL="$(
    gcloud run services describe "$API_SERVICE"       --project="$PROJECT"       --region="$REGION"       --format='value(status.url)'
  )"
fi

if [ -z "$AIOS_API_URL" ]; then
  echo "ERROR: Could not resolve AIOS API URL."
  exit 1
fi

echo "=== AIOS LOCAL WEB ==="
echo "Web:      http://localhost:8000"
echo "Username: $AIOS_WEB_USERNAME"
echo "Password: $AIOS_WEB_PASSWORD"
echo "API:      $AIOS_API_URL"
echo
echo "Press Ctrl+C to stop."

exec uvicorn aios.web_capture.app:app   --reload   --host 0.0.0.0   --port 8000
