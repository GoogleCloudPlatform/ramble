locals {
  terraform_apply_roles = toset([
    "roles/cloudbuild.editor",
    "roles/cloudbuild.workerPoolOwner",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/logging.logWriter",
    "roles/pubsub.admin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/secretmanager.admin",
    "roles/storage.admin",
  ])
}

resource "google_service_account" "terraform_apply" {
  account_id   = "cloud-build-terraform-apply"
  display_name = "Cloud Build Terraform Apply Service Account"
}

resource "google_project_iam_member" "terraform_apply_roles" {
  for_each = local.terraform_apply_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.terraform_apply.email}"
}

resource "google_cloudbuild_trigger" "terraform_apply" {
  location    = var.region
  name        = "ramble-terraform-apply"
  description = "Automatically apply Cloud Build Triggers Terraform configuration when pushed to develop branch"

  service_account = google_service_account.terraform_apply.id

  repository_event_config {
    repository = "projects/${var.project_id}/locations/${var.region}/connections/Ramble-USC1/repositories/${var.github_owner}-${var.github_repo}"
    push {
      branch = "^develop$"
    }
  }

  included_files = [
    "share/ramble/cloud-build/terraform/triggers/**",
    "share/ramble/cloud-build/ramble-terraform-apply.yaml"
  ]

  filename = "share/ramble/cloud-build/ramble-terraform-apply.yaml"

  depends_on = [
    google_project_iam_member.terraform_apply_roles,
  ]
}
