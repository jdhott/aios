#!/bin/bash
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:-aios-jdh}"
REGION="${AIOS_CLOUD_RUN_REGION:-northamerica-northeast1}"

for job in \
  aios-compat-quarter-hour \
  aios-compat-2100
do
  if gcloud scheduler jobs describe "$job" \
      --project "$PROJECT" \
      --location "$REGION" >/dev/null 2>&1
  then
    echo "Pausing $job"
    gcloud scheduler jobs pause "$job" \
      --project "$PROJECT" \
      --location "$REGION"
  fi
done

echo "Scheduled compatibility trigger paused."
