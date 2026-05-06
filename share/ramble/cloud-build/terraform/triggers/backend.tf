terraform {
  backend "gcs" {
    bucket = "ramble-terraform-state"
    prefix = "terraform/state/image-triggers"
  }
}
