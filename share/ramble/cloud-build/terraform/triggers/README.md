# Ramble Cloud Build Image Triggers

This directory contains Terraform configuration to deploy and manage Google Cloud Build Triggers used by the Ramble repository.

## How to deploy

The deployment states are stored in a GCS bucket, to allow for running Terraform from different locations. The bucket was created with:

```bash
gcloud storage buckets create gs://ramble-terraform-state --project=ramble-eng --location=us-central1
```

With the bucket created, the triggers can be deployed with:

```bash
terraform init
# Optional to check the changes to be made
terraform plan
terraform apply --auto-approve
```

## Slack Notification Setup

Build failure notifications for `codecov_push` are sent to Slack via the [Cloud Build Slack Notifier](https://cloud.google.com/build/docs/configuring-notifications/configure-slack) defined in `slack_notifier.tf`. The Slack Incoming Webhook URL (from the `ramble-ci-notifier` Slack app) is stored in GCP Secret Manager under `ramble-slack-webhook`.

To rotate the Slack webhook URL:

1. Generate a new **Incoming Webhook URL** for the `ramble-ci-notifier` app in your [Slack App settings](https://api.slack.com/apps).
2. Add a new version to the `ramble-slack-webhook` secret in Secret Manager:

```bash
printf "<webhook-url>" | \
  gcloud secrets versions add ramble-slack-webhook \
    --project=ramble-eng \
    --data-file=-
```

3. Re-run `terraform apply` so the notifier configuration and Cloud Run revision pick up the latest secret version.

