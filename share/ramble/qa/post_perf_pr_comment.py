#!/usr/bin/env python3
# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None

# This is used to dedupe comments
MARKER = "<!-- ramble-perf-test-metrics -->"

def get_bq_averages(project_id, dataset_id, table_id):
    if not bigquery:
        print("google-cloud-bigquery not found, skipping BQ query.")
        return {}

    if not project_id or not dataset_id or not table_id:
        print("Missing BigQuery configuration, skipping BQ query.")
        return {}
        
    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT test_name, AVG(duration) as avg_duration
        FROM (
            SELECT test_name, duration,
                   ROW_NUMBER() OVER(PARTITION BY test_name ORDER BY timestamp DESC) as rn
            FROM `{project_id}.{dataset_id}.{table_id}`
            WHERE duration IS NOT NULL
        )
        WHERE rn <= 5
        GROUP BY test_name
    """
    try:
        query_job = client.query(query)
        results = query_job.result()
        return {row.test_name: row.avg_duration for row in results}
    except Exception as e:
        print(f"Error querying BigQuery: {e}")
        return {}

def make_github_request(url, token, method="GET", data=None):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    if data is not None:
        data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"GitHub API Error: {e.code} - {error_msg}")
        raise



def format_markdown(metrics, averages):
    lines = [
        "## Ramble Performance Test Metrics",
        "",
        "| Test Name | Outcome | Duration (s) | Last 5 Avg (s) |",
        "|---|---|---|---|"
    ]
    
    for m in metrics:
        name = m.get("test_name", "Unknown")
        duration = m.get("duration", "N/A")
        outcome = m.get("outcome", "N/A")
        
        avg_dur = averages.get(name)
        avg_str = f"{avg_dur:.4f}" if avg_dur is not None else "N/A"
        
        if isinstance(duration, float):
            duration = f"{duration:.4f}"
            
        lines.append(f"| {name} | {outcome} | {duration} | {avg_str} |")
        
    lines.append("")
    lines.append(MARKER)
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Post Ramble perf metrics to a GitHub PR")
    parser.add_argument("--metrics-file", required=True, help="Path to metrics JSON file")
    parser.add_argument("--project-id", help="GCP Project ID")
    parser.add_argument("--dataset-id", help="BigQuery Dataset ID")
    parser.add_argument("--table-id", help="BigQuery Table ID")
    parser.add_argument("--pr-number", required=True, help="GitHub Pull Request number")
    parser.add_argument("--repo", default="GoogleCloudPlatform/ramble", help="GitHub repository (owner/repo)")
    parser.add_argument("--dry-run", action="store_true", help="Print only")
    
    args = parser.parse_args()

    token = os.environ.get("GITHUB_PR_TOKEN")
    if not token and not args.dry_run:
        print("GITHUB_PR_TOKEN environment variable is not set. Cannot post to GitHub.")
        sys.exit(1)
        
    if not os.path.exists(args.metrics_file):
        print(f"Metrics file {args.metrics_file} not found.")
        sys.exit(0)
        
    with open(args.metrics_file, "r") as f:
        metrics = json.load(f)

    if not metrics:
        print("No metrics to post.")
        sys.exit(0)

    averages = get_bq_averages(args.project_id, args.dataset_id, args.table_id)
    
    body = format_markdown(metrics, averages)
    
    if args.dry_run:
        print("[DRY RUN] Would post the following comment:")
        print(body)
        sys.exit(0)
        
    # Avoid posting multiple comments
    url_comments = f"https://api.github.com/repos/{args.repo}/issues/{args.pr_number}/comments"
    comments = make_github_request(url_comments, token)
    
    existing_comment = None
    for c in comments:
        if MARKER in c.get("body", ""):
            existing_comment = c
            break
            
    if existing_comment:
        print(f"Found existing comment (ID: {existing_comment['id']}). Updating...")
        update_url = f"https://api.github.com/repos/{args.repo}/issues/comments/{existing_comment['id']}"
        res = make_github_request(update_url, token, method="PATCH", data={"body": body})
        print("Comment updated successfully.")
    else:
        print("Creating new comment...")
        res = make_github_request(url_comments, token, method="POST", data={"body": body})
        print("Comment created successfully.")

if __name__ == "__main__":
    main()
