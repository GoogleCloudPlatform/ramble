resource "google_cloudbuild_trigger" "pr_style" {
  name        = "PR-Style-rockylinux8-v0-22-1spack-3-12-1python"
  description = "Run linting on Ramble pull requests"

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch          = "(?:main|develop)"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-pr-style.yaml"

  substitutions = {
    _BASE_IMG   = "rockylinux"
    _BASE_VER   = "8"
    _PYTHON_VER = "3.12.1"
    _SPACK_REF  = "v0.22.1"
  }
}
