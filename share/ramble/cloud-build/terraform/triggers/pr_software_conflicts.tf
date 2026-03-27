resource "google_cloudbuild_trigger" "pr_software_conflicts" {
  name        = "PR-Software-Conflicts-rockylinux8-v0-22-1spack-3-12-1python"
  description = "Check for conflicts in application definitions on Ramble pull requests"

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch          = "(?:main|develop)"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-pr-software-conflicts.yaml"

  included_files = [
    "var/ramble/repos/**",
    "lib/ramble/ramble/**",
    "share/ramble/cloud-build/**"
  ]

  substitutions = {
    _BASE_IMG   = "rockylinux"
    _BASE_VER   = "8"
    _PYTHON_VER = "3.12.1"
    _SPACK_REF  = "v0.22.1"
  }
}
