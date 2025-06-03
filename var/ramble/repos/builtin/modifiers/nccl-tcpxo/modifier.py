# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.modkit import *


class NcclTcpxo(BasicModifier):
    """Modifier to ensure NCCL TCPXO is loaded into the execution environment."""

    name = "nccl-tcpxo"

    tags("gpu")

    maintainers("douglasjacobsen")

    mode(
        "auto", description="Auto detected shell based on config:shell setting"
    )
    mode(
        "ll128",
        description="Use NCCL LL128, reduces latency for small-medium message sizes",
    )
    default_mode("auto")

    def _cos_paths(self):
        return "/usr/local/nvidia/lib64/nccl-env-profile.sh"

    def _debian_paths(self):
        return "/var/lib/tcpxo/lib64/nccl-env-profile.sh"

    register_builtin("source_tcpxo", injection_method="prepend")

    def source_tcpxo(self):
        import ramble.config
        import ramble.util.shell_utils

        shell = ramble.config.get("config:shell")
        source_str = ramble.util.shell_utils.source_str(shell)
        cmds = []

        path_funcs = [self._cos_paths, self._debian_paths]

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
            elif shell == "csh":
                cmds.extend(
                    [
                        f'if ( -d "{script_dir}" ) then',
                        f"    NCCL_LIB_DIR={script_dir} {source_str} {script}",
                        "endif",
                    ]
                )
            elif shell == "fish":
                cmds.extend(
                    [
                        f'if test -d "{script_dir}"',
                        f"    NCCL_LIB_DIR={script_dir} {source_str} {script}",
                        "end",
                    ]
                )
            elif shell == "bat":
                logger.die(
                    "The nccl-tcpxo modifier is not currently supported for batch shell."
                )

        return cmds

    register_builtin(
        "set_ll128_env_vars",
        injection_method="prepend",
        depends_on=["source_tcpxo"],
    )

    def set_ll128_env_vars(self):
        cmds = []
        if self._usage_mode == "ll128":
            cmds.append("NCCL_PROTO=Simple,LL128")
            cmds.append(
                "NCCL_TUNER_CONFIG_PATH=/var/lib/tcpxo/lib64/a3plus_tuner_config_ll128.textproto"
            )
            cmds.append(
                "NCCL_SHIMNET_GUEST_CONFIG_CHECKER_CONFIG_FILE=/var/lib/tcpxo/lib64/a3plus_guest_config_ll128.textproto"
            )
        return cmds
