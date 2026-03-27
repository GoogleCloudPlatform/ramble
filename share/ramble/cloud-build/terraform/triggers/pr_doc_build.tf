locals {
  pr_doc_env = local.image_matrix[10]
}

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
    _BASE_IMG   = local.pr_doc_env.base
    _BASE_VER   = local.pr_doc_env.base_ver
    _PYTHON_VER = local.pr_doc_env.python
    _SPACK_REF  = local.pr_doc_env.spack
  }
}
