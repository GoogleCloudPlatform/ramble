resource "google_cloudbuild_trigger" "pr_image_build_tests_debian" {
  location    = var.region
  name        = "PR-Image-Build-Tests-Debian"
  description = "A presubmit check for building Debian image used by other cloud build triggers"

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch          = "(?:main|develop)"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-pr-image-builds.yaml"

  included_files = concat(
    local.dependency_and_config_files,
    [
      "share/ramble/cloud-build/ramble-pr-image-builds.yaml",
      "share/ramble/cloud-build/Dockerfile-apt"
    ]
  )

  substitutions = merge(local.default_substitutions, {
    _PKG_MANAGER = "apt"
  })
}

resource "google_cloudbuild_trigger" "pr_image_build_tests_rocky" {
  location    = var.region
  name        = "PR-Image-Build-Tests-Rocky"
  description = "A presubmit check for building Rocky image used by other cloud build triggers"

  github {
    owner = var.github_owner
    name  = var.github_repo
    pull_request {
      branch          = "(?:main|develop)"
      comment_control = "COMMENTS_ENABLED_FOR_EXTERNAL_CONTRIBUTORS_ONLY"
    }
  }

  include_build_logs = "INCLUDE_BUILD_LOGS_WITH_STATUS"

  filename = "share/ramble/cloud-build/ramble-pr-image-builds.yaml"

  included_files = concat(
    local.dependency_and_config_files,
    [
      "share/ramble/cloud-build/ramble-pr-image-builds.yaml",
      "share/ramble/cloud-build/Dockerfile-yum"
    ]
  )

  substitutions = merge(local.default_substitutions, {
    _PKG_MANAGER = "yum"
  })
}
