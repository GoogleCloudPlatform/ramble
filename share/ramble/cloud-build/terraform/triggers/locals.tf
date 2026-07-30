locals {
  # This map holds the full list of available images.
  # A trigger should always reference these images instead of hard-coding new ones.
  image_map = {
    "debian12-5-py3-12-0-spack-v0-21-2" = { python = "3.12.0", spack = "v0.21.2", base = "debian", base_ver = "12.5" },
    "debian12-5-py3-8-0-spack-v0-21-2"  = { python = "3.8.0", spack = "v0.21.2", base = "debian", base_ver = "12.5" },
    "debian12-5-py3-12-1-spack-v0-22-1" = { python = "3.12.1", spack = "v0.22.1", base = "debian", base_ver = "12.5" },
    "debian12-5-py3-8-0-spack-v0-22-1"  = { python = "3.8.0", spack = "v0.22.1", base = "debian", base_ver = "12.5" },
    "debian12-5-py3-13-5-spack-v1-0-0"  = { python = "3.13.5", spack = "v1.0.0", base = "debian", base_ver = "12.5" },
    "debian12-5-py3-7-17-spack-v1-0-0"  = { python = "3.7.17", spack = "v1.0.0", base = "debian", base_ver = "12.5" },
    "rocky8-py3-12-0-spack-v0-21-2"     = { python = "3.12.0", spack = "v0.21.2", base = "rockylinux", base_ver = "8" },
    "rocky8-py3-7-0-spack-v0-21-2"      = { python = "3.7.0", spack = "v0.21.2", base = "rockylinux", base_ver = "8" },
    "rocky8-py3-12-1-spack-v0-22-1"     = { python = "3.12.1", spack = "v0.22.1", base = "rockylinux", base_ver = "8" },
    "rocky8-py3-7-0-spack-v0-22-1"      = { python = "3.7.0", spack = "v0.22.1", base = "rockylinux", base_ver = "8" },
    "rocky8-py3-13-5-spack-v1-0-0"      = { python = "3.13.5", spack = "v1.0.0", base = "rockylinux", base_ver = "8" },
    "rocky8-py3-7-17-spack-v1-0-0"      = { python = "3.7.17", spack = "v1.0.0", base = "rockylinux", base_ver = "8" },
  }

  pm_map = {
    "debian"     = "apt"
    "rockylinux" = "yum"
  }

  docs_files = [
    "lib/ramble/docs/**"
  ]

  core_source_files = [
    "bin/**",
    "lib/ramble/**",
    "var/ramble/repos/**",
    "conftest.py"
  ]

  dependency_and_config_files = [
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-pinned.txt",
    "pyproject.toml",
    "pyproject_objects.toml"
  ]

  # Default execution settings shared across Cloud Build triggers
  default_trigger_config = {
    machine_type = "E2_HIGHCPU_8"
    queue_ttl    = "7200s"
    timeout      = "6000s"
  }

  # Default substitution variables to pass into all Cloud Build triggers
  default_substitutions = {
    _MACHINE_TYPE = local.default_trigger_config.machine_type
    _QUEUE_TTL    = local.default_trigger_config.queue_ttl
    _TIMEOUT      = local.default_trigger_config.timeout
  }
}


