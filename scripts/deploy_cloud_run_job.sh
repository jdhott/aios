#!/bin/bash
set -euo pipefail

ROOT="${AIOS_ROOT:-$HOME/LocalProjects/aios}"
cd "$ROOT"

PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"
JOB="${AIOS_CLOUD_RUN_JOB:-aios-processor}"
REPOSITORY="${AIOS_ARTIFACT_REPOSITORY:-aios}"
IMAGE_NAME="${AIOS_JOB_IMAGE_NAME:-aios-processor}"
RUNTIME_SERVICE_ACCOUNT="${AIOS_JOB_RUNTIME_SERVICE_ACCOUNT_EMAIL:-aios-job-runtime@${PROJECT}.iam.gserviceaccount.com}"

if [ -z "$PROJECT" ]; then
  echo "ERROR: GOOGLE_CLOUD_PROJECT is required."
  exit 1
fi

required_local_vars=(
  TASKS_DATABASE_ID
  BRAIN_DUMP_PAGE_ID
  NOTION_PROJECTS_DATABASE_ID
  AIOS_DASHBOARD_BLOCK_ID
  ARCHIVE_TOGGLE_BLOCK_ID
)

for name in "${required_local_vars[@]}"; do
  if [ -z "${!name:-}" ]; then
    echo "ERROR: $name must be exported before deployment."
    exit 1
  fi
done

IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPOSITORY}/${IMAGE_NAME}:$(git rev-parse --short HEAD)"

echo "=== AIOS CLOUD RUN JOB V1 DEPLOY ==="
echo "Project: $PROJECT"
echo "Region:  $REGION"
echo "Job:     $JOB"
echo "Image:   $IMAGE"
echo "Runtime: $RUNTIME_SERVICE_ACCOUNT"
echo "Schedule: manual only"

gcloud builds submit   --project "$PROJECT"   --config cloudbuild.job.yaml   --substitutions "_IMAGE=${IMAGE}"   .

gcloud run jobs deploy "$JOB"   --project "$PROJECT"   --region "$REGION"   --image "$IMAGE"   --service-account "$RUNTIME_SERVICE_ACCOUNT"   --set-env-vars "AIOS_JOB_ENV=cloudrun,AIOS_DATASTORE=supabase,AIOS_INBOX_SOURCE=supabase,TASKS_DATABASE_ID=${TASKS_DATABASE_ID},BRAIN_DUMP_PAGE_ID=${BRAIN_DUMP_PAGE_ID},NOTION_PROJECTS_DATABASE_ID=${NOTION_PROJECTS_DATABASE_ID},AIOS_DASHBOARD_BLOCK_ID=${AIOS_DASHBOARD_BLOCK_ID},ARCHIVE_TOGGLE_BLOCK_ID=${ARCHIVE_TOGGLE_BLOCK_ID}"   --set-secrets "SUPABASE_URL=aios-supabase-url:latest,SUPABASE_SECRET_KEY=aios-supabase-secret-key:latest,OPENAI_API_KEY=aios-openai-api-key:latest,NOTION_TOKEN=aios-notion-token:latest"   --tasks 1   --max-retries 0   --task-timeout 20m

echo "Deployment complete."
echo "No scheduler has been created."
