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
}
