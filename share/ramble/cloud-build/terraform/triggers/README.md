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
