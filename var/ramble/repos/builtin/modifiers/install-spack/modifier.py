# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class InstallSpack(BasicModifier):
    """Modifier to define commands to install spack"""

    name = "install-spack"

    tags("tool-installation")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode for install-spack")
    mode(
        "quiet",
        description="Quiet execution mode for install-spack. Does not "
        + "auto inject commands into experiments.",
    )
    default_mode("quiet")

    modifier_variable(
        "spack_url",
        default="https://github.com/spack/spack",
        description="URL to clone spack from",
        modes=["standard", "quiet"],
    )

    modifier_variable(
        "spack_ref",
        default="develop",
        description="Ref to checkout for spack",
        modes=["standard", "quiet"],
    )

    modifier_variable(
        "spack_install_dir",
        default="${HOME}/.ramble/spack",
        description="Directory to install spack into",
        modes=["standard", "quiet"],
    )

    install_spack_full = """
if [ ! -d {spack_install_dir} ]; then
  git clone {spack_url} {spack_install_dir}
  cd {spack_install_dir}
  git checkout {spack_ref}
  cd -
fi
"""

    install_spack_shallow = """
if [ ! -d {spack_install_dir} ]; then
  git init {spack_install_dir}
  cd {spack_install_dir}
  git remote add origin {spack_url}
  git fetch --depth 1 origin {spack_ref}
  git checkout FETCH_HEAD
  cd -
fi
"""
    modifier_variable(
        "install_spack_full",
        default=install_spack_full,
        description="Install script for full spack history",
        modes=["standard", "quiet"],
    )

    modifier_variable(
        "install_spack_shallow",
        default=install_spack_shallow,
        description="Install script for shallow spack history",
        modes=["standard", "quiet"],
    )

    modifier_variable(
        "source_spack",
        default=". {spack_install_dir}/share/spack/setup-env.sh",
        description="Command for sourcing spack into an environment",
        modes=["standard", "quiet"],
    )

    executable_modifier("source_installed_spack")

    def source_installed_spack(
        self, executable_name, executable, app_inst=None
    ):
        from ramble.util.executable import CommandExecutable

        pre_exec = []
        post_exec = []

        if self._usage_mode == "quiet":
            return pre_exec, post_exec

        if not hasattr(self, "_already_applied"):
            pre_exec.append(
                CommandExecutable(
                    "source-installed-spack",
                    template=[
                        "{source_spack}",
                    ],
                )
            )

            self._already_applied = True
        return pre_exec, post_exec
