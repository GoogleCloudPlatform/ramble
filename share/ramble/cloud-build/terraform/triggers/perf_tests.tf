locals {
  perf_test_env = local.image_matrix[10]
}

resource "google_cloudbuild_trigger" "perf_test_pr" {
  name        = "PerfTest-PR-${local.perf_test_env.base}${local.perf_test_env.base_ver}-${replace(local.perf_test_env.spack, ".", "-")}spack-${replace(local.perf_test_env.python, ".", "-")}python"
  description = "Ramble perf tests for PR builds"

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch          = "(?:main|develop)"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-perf-tests.yaml"

  substitutions = {
    _SPACK_REF    = local.perf_test_env.spack
    _PYTHON_VER   = local.perf_test_env.python
    _BASE_IMG     = local.perf_test_env.base
    _BASE_VER     = local.perf_test_env.base_ver
    _DATASET_ID   = "ramble_metrics"
    _PROJECT_ID   = var.project_id
    _TABLE_ID     = "perf_test_durations"
    _UPLOAD_TO_BQ = "false"
  }
}

resource "google_cloudbuild_trigger" "perf_test_push" {
  name        = "PerfTest-Push-${local.perf_test_env.base}${local.perf_test_env.base_ver}-${replace(local.perf_test_env.spack, ".", "-")}spack-${replace(local.perf_test_env.python, ".", "-")}python"
  description = "Continuous monitoring of Ramble performance for develop push"

  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = "^develop$"
    }
  }

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-perf-tests.yaml"

  substitutions = {
    _SPACK_REF    = local.perf_test_env.spack
    _PYTHON_VER   = local.perf_test_env.python
    _BASE_IMG     = local.perf_test_env.base
    _BASE_VER     = local.perf_test_env.base_ver
    _DATASET_ID   = "ramble_metrics"
    _PROJECT_ID   = var.project_id
    _TABLE_ID     = "perf_test_durations"
    _UPLOAD_TO_BQ = "true"
  }
}
