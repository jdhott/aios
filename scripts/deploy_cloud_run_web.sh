#!/bin/bash
set -euo pipefail

ROOT="${AIOS_ROOT:-$HOME/LocalProjects/aios}"
cd "$ROOT"

PROJECT="${GOOGLE_CLOUD_PROJECT:-aios-jdh}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"
REPOSITORY="${AIOS_ARTIFACT_REPOSITORY:-aios}"
WEB_SERVICE="${AIOS_WEB_SERVICE:-aios-web}"
WEB_RUNTIME_SA="${AIOS_WEB_RUNTIME_SERVICE_ACCOUNT_EMAIL:-aios-web-runtime@${PROJECT}.iam.gserviceaccount.com}"
WEB_USERNAME="${AIOS_WEB_USERNAME:-aios}"
PASSWORD_SECRET="${AIOS_WEB_PASSWORD_SECRET:-aios-web-password}"

API_URL="$(
  gcloud run services describe aios-api \
    --project "$PROJECT" \
    --region "$REGION" \
    --format='value(status.url)'
)"

if [ -z "$API_URL" ]; then
  echo "ERROR: Could not resolve aios-api URL."
  exit 1
fi

IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPOSITORY}/aios-web:$(git rev-parse --short HEAD)-$(date +%H%M%S)"

echo "=== AIOS WEB CAPTURE V1 DEPLOY ==="
echo "Project: $PROJECT"
echo "Region:  $REGION"
echo "Service: $WEB_SERVICE"
echo "API:     $API_URL"
echo "Image:   $IMAGE"

gcloud builds submit \
  --project "$PROJECT" \
  --config cloudbuild.web.yaml \
  --substitutions "_IMAGE=${IMAGE}" \
  .

gcloud run deploy "$WEB_SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --image "$IMAGE" \
  --service-account "$WEB_RUNTIME_SA" \
  --allow-unauthenticated \
  --set-env-vars "AIOS_WEB_USERNAME=${WEB_USERNAME},AIOS_API_URL=${API_URL}" \
  --set-secrets "AIOS_WEB_PASSWORD=${PASSWORD_SECRET}:latest" \
  --port 8080 \
  --memory 256Mi \
  --cpu 1 \
  --min 0 \
  --max 2

WEB_URL="$(
  gcloud run services describe "$WEB_SERVICE" \
    --project "$PROJECT" \
    --region "$REGION" \
    --format='value(status.url)'
)"

echo
echo "Web Capture deployed:"
echo "  $WEB_URL"
echo
echo "The Cloud Run service is internet-reachable but the app itself requires"
echo "HTTP Basic authentication using username '$WEB_USERNAME' and the password"
echo "stored in Secret Manager."
