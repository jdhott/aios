#!/bin/bash
set -euo pipefail
PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"
JOB="${AIOS_CLOUD_RUN_JOB:-aios-processor}"

if [ -z "$PROJECT" ]; then
  echo "ERROR: GOOGLE_CLOUD_PROJECT is required."
  exit 1
fi

gcloud run jobs execute "$JOB"   --project "$PROJECT"   --region "$REGION"   --wait
