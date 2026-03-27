resource "google_cloudbuild_trigger" "pr_doc_build_tests" {
  name        = "PR-Doc-Build-Tests"
  description = "A presubmit check for building Ramble documentation"

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch          = "(?:main|develop)"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-pr-docs.yaml"

  substitutions = {
    _BASE_IMG   = "rockylinux"
    _BASE_VER   = "8"
    _PYTHON_VER = "3.13.5"
    _SPACK_REF  = "v1.0.0"
  }
}
