locals {
  # This matrix is used by both the image-build and unit-test triggers
  image_matrix = [
    { python = "3.12.0", spack = "v0.21.2", base = "debian", base_ver = "12.5" },
    { python = "3.8.0", spack = "v0.21.2", base = "debian", base_ver = "12.5" },
    { python = "3.12.1", spack = "v0.22.1", base = "debian", base_ver = "12.5" },
    { python = "3.8.0", spack = "v0.22.1", base = "debian", base_ver = "12.5" },
    { python = "3.13.5", spack = "v1.0.0", base = "debian", base_ver = "12.5" },
    { python = "3.7.17", spack = "v1.0.0", base = "debian", base_ver = "12.5" },
    { python = "3.12.0", spack = "v0.21.2", base = "rockylinux", base_ver = "8" },
    { python = "3.7.0", spack = "v0.21.2", base = "rockylinux", base_ver = "8" },
    { python = "3.12.1", spack = "v0.22.1", base = "rockylinux", base_ver = "8" },
    { python = "3.7.0", spack = "v0.22.1", base = "rockylinux", base_ver = "8" },
    { python = "3.13.5", spack = "v1.0.0", base = "rockylinux", base_ver = "8" },
    { python = "3.7.17", spack = "v1.0.0", base = "rockylinux", base_ver = "8" },
  ]

  pm_map = {
    "debian"     = "apt"
    "rockylinux" = "yum"
  }
}
