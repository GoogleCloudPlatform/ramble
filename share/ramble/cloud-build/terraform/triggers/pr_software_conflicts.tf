locals {
  pr_software_conflicts_env = local.image_matrix[8]
}

resource "google_cloudbuild_trigger" "pr_software_conflicts" {
  name        = "PR-Software-Conflicts-${local.pr_software_conflicts_env.base}${local.pr_software_conflicts_env.base_ver}-${replace(local.pr_software_conflicts_env.spack, ".", "-")}spack-${replace(local.pr_software_conflicts_env.python, ".", "-")}python"
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
    _BASE_IMG   = local.pr_software_conflicts_env.base
    _BASE_VER   = local.pr_software_conflicts_env.base_ver
    _PYTHON_VER = local.pr_software_conflicts_env.python
    _SPACK_REF  = local.pr_software_conflicts_env.spack
  }
}
