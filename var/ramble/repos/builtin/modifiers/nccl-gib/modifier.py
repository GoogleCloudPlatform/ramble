# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.modkit import *


class NcclGib(BasicModifier):
    """Modifier to ensure NCCL gIB is loaded into the execution environment."""

    name = "nccl-gib"

    tags("gpu")

    maintainers("douglasjacobsen")

    mode(
        "auto", description="Auto detected shell based on config:shell setting"
    )
    default_mode("auto")

    modifier_variable(
        "nccl_socket_ifname",
        default="",
        description="Specification of which IP interfaces to use for communication",
        modes=["auto"],
    )

    def _nccl_env_script_path(self):
        return "/usr/local/gib/scripts/set_nccl_env.sh"

    register_builtin("source_gib", injection_method="prepend")

    def source_gib(self):
        import ramble.config
        import ramble.util.shell_utils

        shell = ramble.config.get("config:shell")
        source_str = ramble.util.shell_utils.source_str(shell)
        cmds = []

        path_funcs = [self._nccl_env_script_path]
        ifname = self.expander.expand_var_name("nccl_socket_ifname")

        for path_func in path_funcs:
            script = path_func()
            script_dir = os.path.dirname(script)
            if shell in ["bash", "sh"]:
                cmds.extend(
                    [
                        f'if [ -d "{script_dir}" ]; then',
                        f"    NCCL_LIB_DIR={script_dir} {source_str} {script}",
                        "fi",
                    ]
                )

                if ifname != "":
                    cmds.append(f"export NCCL_SOCKET_IFNAME={ifname}")
            elif shell == "csh":
                cmds.extend(
                    [
                        f'if ( -d "{script_dir}" ) then',
                        f"    NCCL_LIB_DIR={script_dir} {source_str} {script}",
                        "endif",
                    ]
                )
                if ifname != "":
                    cmds.append(f"setenv NCCL_SOCKET_IFNAME {ifname}")
            elif shell == "fish":
                cmds.extend(
                    [
                        f'if test -d "{script_dir}"',
                        f"    NCCL_LIB_DIR={script_dir} {source_str} {script}",
                        "end",
                    ]
                )
                if ifname != "":
                    cmds.append(f"set -x NCCL_SOCKET_IFNAME {ifname}")
            elif shell == "bat":
                logger.die(
                    "The nccl-gib modifier is not currently supported for batch shell."
                )

        return cmds
