# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *

import ramble.util.shell_utils


class Lscpu(BasicModifier):
    """Define a modifier for lspcu

    lscpu gives useful information about the underlying compute platform. This
    modifier allows experiments to easily extract system information while the
    experiment is being performed.
    """

    name = "lscpu"

    tags("system-info", "sysinfo", "platform-info")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode for lscpu")
    default_mode("standard")

    variable_modification(
        "lscpu_log",
        "{experiment_run_dir}/lscpu_output.log",
        method="set",
        modes=["standard"],
    )

    archive_pattern("lscpu_output.log")

    figure_of_merit_context(
        "architecture",
        regex=r"Architecture:\s+(?P<arch>[\w-]+)",
        output_format="{arch}",
    )

    section_list = [
        "CPU op-mode(s)",
        "Address sizes",
        "Byte Order",
        "CPU(s)",
        "On-line CPU(s) list",
        "Vendor ID",
        "Model name",
        "CPU family",
        "Model",
        "Thread(s) per core",
        "Core(s) per socket",
        "Socket(s)",
        "Stepping",
        "CPU(s) scaling MHz",
        "CPU max MHz",
        "CPU min MHz",
        "BogoMIPS",
        "Virtualization",
        "L1d cache",
        "L1i cache",
        "L2 cache",
        "L3 cache",
        "NUMA",
        "NUMA node(s)",
        "NUMA node0 CPU(s)",
        "Vulnerability Itlb multihit",
        "Vulnerability L1tf",
        "Vulnerability Mds",
        "Vulnerability Meltdown",
        "Vulnerability Mmio stale data",
        "Vulnerability Retbleed",
        "Vulnerability Spec store bypass",
        "Vulnerability Spectre v1",
        "Vulnerability Spectre v2",
        "Vulnerability Srbds",
        "Vulnerability Tsx async abort",
    ]

    for section in section_list:
        figure_of_merit(
            section,
            fom_regex=r"\s*"
            + f"{section}".replace("(", r"\(").replace(")", r"\)")
            + r":\s+(?P<fom>.*)",
            group_name="fom",
            units="",
            log_file="{lscpu_log}",
            contexts=["architecture"],
            fom_type=FomType.INFO,
        )

    register_builtin("lscpu_exec")

    def lscpu_exec(self):
        return ["lscpu >> {lscpu_log}"]

    register_builtin("get_detected_arch", injection_method="append")

    def get_detected_arch(self):
        """Collect detected arch from both Spack and GCC, if they are available."""
        shell = ramble.config.get("config:shell")
        spack_arch = ramble.util.shell_utils.cmd_sub_str(shell, "spack arch")
        gcc_arch = ramble.util.shell_utils.cmd_sub_str(
            shell,
            "gcc -march=native -Q --help=target | grep -- '-march=  ' | cut -f3",
        )
        return [
            f"""
if which spack > /dev/null; then
    spack_arch={spack_arch}
    echo "Spack detected arch=$spack_arch" >> {{lscpu_log}}
fi

if which gcc > /dev/null; then
    gcc_arch={gcc_arch}
    echo "GCC detected arch=$gcc_arch" >> {{lscpu_log}}
fi\n"""
        ]

    figure_of_merit(
        "spack_arch",
        fom_regex=r"^\s*Spack detected arch=\s*(?P<spack_arch>.*)",
        group_name="spack_arch",
        log_file="{lscpu_log}",
    )

    figure_of_merit(
        "gcc_arch",
        fom_regex=r"^\s*GCC detected arch=\s*(?P<gcc_arch>.*)",
        group_name="gcc_arch",
        log_file="{lscpu_log}",
    )
