#!/usr/bin/env python3
# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import argparse
import datetime
import json
import os
import sys

try:
    # This is a dependency for Ramble, so it should be installed in the CI pipeline already
    from google.cloud import bigquery
except ImportError:
    bigquery = None


def upload_metrics(metrics_file, project_id, dataset_id, table_id, commit_sha=None, dry_run=False):
    if not os.path.exists(metrics_file):
        print(f"Metrics file {metrics_file} not found.")
        return

    with open(metrics_file, "r") as f:
        metrics = json.load(f)

    if not metrics:
        print("No metrics to upload.")
        return

    rows = []
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    for m in metrics:
        row = {
            "test_name": m.get("test_name"),
            "test_id": m.get("test_id"),
            "duration": m.get("duration"),
            "outcome": m.get("outcome"),
            "timestamp": timestamp,
            "commit_sha": commit_sha
        }
        rows.append(row)

    if dry_run:
        print(f"[DRY RUN] Would upload {len(rows)} rows to {project_id}.{dataset_id}.{table_id}:")
        for row in rows:
            print(json.dumps(row, indent=2))
        return

    if bigquery is None:
        print("google-cloud-bigquery not installed. Cannot upload.")
        sys.exit(1)

    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    
    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        print(f"Encountered errors while inserting rows: {errors}")
        sys.exit(1)
    
    print(f"Successfully uploaded {len(rows)} rows to {table_ref}.")


def main():
    parser = argparse.ArgumentParser(description="Upload Ramble perf metrics to BigQuery")
    parser.add_argument("--metrics-file", required=True, help="Path to metrics JSON file")
    parser.add_argument("--project-id", required=True, help="GCP Project ID")
    parser.add_argument("--dataset-id", required=True, help="BigQuery Dataset ID")
    parser.add_argument("--table-id", required=True, help="BigQuery Table ID")
    parser.add_argument("--commit-sha", help="Git commit SHA")
    parser.add_argument("--dry-run", action="store_true", help="Print metrics instead of uploading")

    args = parser.parse_args()

    upload_metrics(
        args.metrics_file,
        args.project_id,
        args.dataset_id,
        args.table_id,
        args.commit_sha,
        args.dry_run
    )


if __name__ == "__main__":
    main()
