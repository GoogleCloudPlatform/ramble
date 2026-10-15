#!/bin/bash
# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

# Script to setup BigQuery dataset and table for Ramble perf metrics.

PROJECT_ID=${1:-$GOOGLE_CLOUD_PROJECT}
DATASET_ID=${2:-ramble_metrics}
TABLE_ID=${3:-perf_test_durations}

if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 <PROJECT_ID> [DATASET_ID] [TABLE_ID]"
    exit 1
fi

echo "Setting up BigQuery for project: $PROJECT_ID"
echo "Dataset: $DATASET_ID"
echo "Table: $TABLE_ID"

if ! bq ls --project_id="$PROJECT_ID" "$DATASET_ID" &>/dev/null; then
    echo "Creating dataset $DATASET_ID..."
    bq --project_id="$PROJECT_ID" mk --dataset \
        --description "Ramble Performance Metrics" \
        --location=US \
        "$DATASET_ID"
else
    echo "Dataset $DATASET_ID already exists."
fi

SCHEMA="test_name:STRING,test_id:STRING,duration:FLOAT,outcome:STRING,timestamp:TIMESTAMP,commit_sha:STRING"

if ! bq ls --project_id="$PROJECT_ID" "$DATASET_ID" | grep -w "$TABLE_ID" &>/dev/null; then
    echo "Creating table $TABLE_ID..."
    bq --project_id="$PROJECT_ID" mk --table \
        --description "Durations of Ramble perf tests" \
        "${DATASET_ID}.${TABLE_ID}" \
        "$SCHEMA"
else
    echo "Table $TABLE_ID already exists."
fi

echo "Done."
