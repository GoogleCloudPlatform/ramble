resource "google_cloudbuild_trigger" "perf_test_pr" {
  name        = "PerfTest-PR-rockylinux8-v1-0-0spack-3-13-5python"
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
    _SPACK_REF    = "v1.0.0"
    _PYTHON_VER   = "3.13.5"
    _BASE_IMG     = "rockylinux"
    _BASE_VER     = "8"
    _DATASET_ID   = "ramble_metrics"
    _PROJECT_ID   = var.project_id
    _TABLE_ID     = "perf_test_durations"
    _UPLOAD_TO_BQ = "false"
  }
}

resource "google_cloudbuild_trigger" "perf_test_push" {
  name        = "PerfTest-Push-rockylinux8-v1-0-0spack-3-13-5python"
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
    _SPACK_REF    = "v1.0.0"
    _PYTHON_VER   = "3.13.5"
    _BASE_IMG     = "rockylinux"
    _BASE_VER     = "8"
    _DATASET_ID   = "ramble_metrics"
    _PROJECT_ID   = var.project_id
    _TABLE_ID     = "perf_test_durations"
    _UPLOAD_TO_BQ = "true"
  }
}
