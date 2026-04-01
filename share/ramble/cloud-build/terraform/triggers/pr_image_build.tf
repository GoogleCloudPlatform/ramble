resource "google_cloudbuild_trigger" "pr_image_build_tests" {
  name        = "PR-Image-Build-Tests"
  description = "A presubmit check for building images used by other cloud build triggers"

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch          = "(?:main|develop)"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-pr-image-builds.yaml"

  included_files = [
    "share/ramble/cloud-build/**",
    "requirements.txt",
    "requirements-dev.txt"
  ]
}
