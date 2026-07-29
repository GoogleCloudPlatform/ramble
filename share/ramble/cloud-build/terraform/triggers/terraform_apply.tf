resource "google_cloudbuild_trigger" "terraform_apply" {
  location    = var.region
  name        = "ramble-terraform-apply"
  description = "Automatically apply Cloud Build Triggers Terraform configuration when pushed to develop branch"

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = "^develop$"
    }
  }

  included_files = [
    "share/ramble/cloud-build/terraform/triggers/**",
    "share/ramble/cloud-build/ramble-terraform-apply.yaml"
  ]

  filename = "share/ramble/cloud-build/ramble-terraform-apply.yaml"
}
