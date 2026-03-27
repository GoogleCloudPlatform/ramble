locals {
  pr_style_env = local.image_matrix[8]
}

resource "google_cloudbuild_trigger" "pr_style" {
  name        = "PR-Style-${local.pr_style_env.base}${local.pr_style_env.base_ver}-${replace(local.pr_style_env.spack, ".", "-")}spack-${replace(local.pr_style_env.python, ".", "-")}python"
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
    _BASE_IMG   = local.pr_style_env.base
    _BASE_VER   = local.pr_style_env.base_ver
    _PYTHON_VER = local.pr_style_env.python
    _SPACK_REF  = local.pr_style_env.spack
  }
}
