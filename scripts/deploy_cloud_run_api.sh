#!/bin/bash
set -euo pipefail

ROOT="${AIOS_ROOT:-$HOME/LocalProjects/aios}"
cd "$ROOT"

SERVICE="${AIOS_CLOUD_RUN_SERVICE:-aios-api}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"
PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
REPOSITORY="${AIOS_ARTIFACT_REPOSITORY:-aios}"
IMAGE_NAME="${AIOS_API_IMAGE_NAME:-aios-api}"

RUNTIME_SERVICE_ACCOUNT="${AIOS_RUNTIME_SERVICE_ACCOUNT_EMAIL:-aios-api-runtime@${PROJECT}.iam.gserviceaccount.com}"

SUPABASE_URL_SECRET="${SUPABASE_URL_SECRET:-aios-supabase-url}"
SUPABASE_SECRET_KEY_SECRET="${SUPABASE_SECRET_KEY_SECRET:-aios-supabase-secret-key}"

if [ -z "$PROJECT" ]; then
  echo "ERROR: GOOGLE_CLOUD_PROJECT is required."
  exit 1
fi

IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPOSITORY}/${IMAGE_NAME}:$(git rev-parse --short HEAD)"

echo "=== AIOS CLOUD RUN API DEPLOY ==="
echo "Project: $PROJECT"
echo "Region:  $REGION"
echo "Service: $SERVICE"
echo "Image:   $IMAGE"
echo "Auth:    Cloud Run IAM (private)"

command -v gcloud >/dev/null 2>&1 || {
  echo "ERROR: gcloud CLI is not installed."
  exit 1
}

gcloud artifacts repositories describe   "$REPOSITORY"   --project "$PROJECT"   --location "$REGION" >/dev/null 2>&1 || {
    echo "ERROR: Artifact Registry repository '$REPOSITORY' not found in $REGION."
    exit 1
  }

gcloud builds submit   --project "$PROJECT"   --config cloudbuild.api.yaml   --substitutions "_IMAGE=${IMAGE}"   .

gcloud run deploy "$SERVICE"   --project "$PROJECT"   --region "$REGION"   --image "$IMAGE"   --no-allow-unauthenticated   --set-env-vars "AIOS_API_ENV=cloudrun,AIOS_PROCESSOR_TRIGGER_ENABLED=true,GOOGLE_CLOUD_PROJECT=${PROJECT},AIOS_CLOUD_RUN_REGION=${REGION},AIOS_CLOUD_RUN_JOB=aios-processor"   --set-secrets "SUPABASE_URL=${SUPABASE_URL_SECRET}:latest,SUPABASE_SECRET_KEY=${SUPABASE_SECRET_KEY_SECRET}:latest,OPENAI_API_KEY=aios-openai-api-key:latest"   --port 8080

echo "Deployment complete."
echo "Service is private. Test with:"
echo "  SERVICE_URL=$(gcloud run services describe $SERVICE --project $PROJECT --region $REGION --format='value(status.url)')"
echo "  curl -H \"Authorization: Bearer $(gcloud auth print-identity-token)\" \"$SERVICE_URL/health\""
