resource "google_cloudbuild_trigger" "pr_unit_tests" {
  for_each = local.image_map

  name        = "PR-Unit-Tests-${each.value.base}${replace(each.value.base_ver, ".", "-")}-${replace(each.value.spack, ".", "-")}spack-${replace(each.value.python, ".", "-")}python"
  description = "Run unit tests and linting on Ramble pull requests"

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch          = "(?:main|develop)"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  ignored_files = local.docs_files

  included_files = concat(
    local.core_source_files,
    local.dependency_and_config_files,
    [
      "share/ramble/cloud-build/**"
    ]
  )

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-pr-unit-tests.yaml"

  substitutions = {
    _BASE_IMG   = each.value.base
    _BASE_VER   = each.value.base_ver
    _PYTHON_VER = each.value.python
    _SPACK_REF  = each.value.spack
  }
}
