locals {
  perf_test_img = local.image_map["rocky8-py3-13-5-spack-v1-0-0"]
}

resource "google_cloudbuild_trigger" "perf_test_pr" {
  location    = var.region
  name        = "PerfTest-PR-${local.perf_test_img.base}${local.perf_test_img.base_ver}-${replace(local.perf_test_img.spack, ".", "-")}spack-${replace(local.perf_test_img.python, ".", "-")}python"
  description = "Ramble perf tests for PR builds"

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
      "share/ramble/**"
    ]
  )

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-perf-tests.yaml"

  substitutions = merge(local.default_substitutions, {
    _SPACK_REF    = local.perf_test_img.spack
    _PYTHON_VER   = local.perf_test_img.python
    _BASE_IMG     = local.perf_test_img.base
    _BASE_VER     = local.perf_test_img.base_ver
    _DATASET_ID   = "ramble_metrics"
    _PROJECT_ID   = var.project_id
    _TABLE_ID     = "perf_test_durations"
    _UPLOAD_TO_BQ = "false"
  })
}

resource "google_cloudbuild_trigger" "perf_test_push" {
  location    = var.region
  name        = "PerfTest-Push-${local.perf_test_img.base}${local.perf_test_img.base_ver}-${replace(local.perf_test_img.spack, ".", "-")}spack-${replace(local.perf_test_img.python, ".", "-")}python"
  description = "Continuous monitoring of Ramble performance for develop push"

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = "^develop$"
    }
  }

  filename = "share/ramble/cloud-build/ramble-perf-tests.yaml"

  substitutions = merge(local.default_substitutions, {
    _SPACK_REF    = local.perf_test_img.spack
    _PYTHON_VER   = local.perf_test_img.python
    _BASE_IMG     = local.perf_test_img.base
    _BASE_VER     = local.perf_test_img.base_ver
    _DATASET_ID   = "ramble_metrics"
    _PROJECT_ID   = var.project_id
    _TABLE_ID     = "perf_test_durations"
    _UPLOAD_TO_BQ = "true"
  })
}
