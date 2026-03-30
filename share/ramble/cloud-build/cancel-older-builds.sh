#!/bin/bash

# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# This script is used by various cloudbuild triggers, to cancel in-flight, but out-dated builds.

if [ -z "$PR_NUMBER" ]; then
  # Only attempt cancellation for PR builds
  echo "Skipping build cancellation."
  exit 0
fi

target_tag="${TRIGGER_NAME}-${PR_NUMBER}"

echo "Current Build ID: $BUILD_ID"
echo "Filtering for tag: ${target_tag} in project: ${PROJECT_ID}"

current_create_time=$(gcloud builds describe "${BUILD_ID}" --project="${PROJECT_ID}" --format="value(create_time)")

if [ -z "${current_create_time}" ]; then
  echo "Warning: Could not retrieve creation time for build ${BUILD_ID}. Skipping cancellation of older builds."
  exit 0
fi

builds_to_cancel=$(gcloud builds list \
  --project="${PROJECT_ID}" \
  --filter="tags='${target_tag}' AND (status=WORKING OR status=QUEUED) AND id!=${BUILD_ID} AND create_time < '${current_create_time}'" \
  --format="value(id)")

if [ -z "${builds_to_cancel}" ]; then
  echo "No older builds found to cancel."
  exit 0
fi

for build in ${builds_to_cancel}; do
  echo "Cancelling obsolete build: ${build}"
  gcloud builds cancel "${build}" --project="${PROJECT_ID}" || echo "Failed to cancel ${build}"
done
