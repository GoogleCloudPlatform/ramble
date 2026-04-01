# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class ArchitectureCheck(ExecutableApplication):
    """Application used to check the default architecture from various tools"""

    name = "architecture-check"

    maintainers("douglasjacobsen")

    tags("system-utility", "diagnostics")

    executable(
        "spack_test",
        template=["""which spack &> /dev/null
if [ $? == 0 ]; then
    echo "Spack tuple: `spack arch`" >> {log_file}
fi
"""],
        redirect="",
        output_capture="",
    )

    executable(
        "gcc_version",
        template=[r"""which gcc &> /dev/null
if [ $? == 0 ]; then
    echo "Gcc version: `gcc --version | grep "[0-9]*\.[0-9]*\.[0-9]*"`" >> {log_file}
fi
"""],
        redirect="",
        output_capture="",
    )

    executable(
        "gcc_test",
        template=["""which gcc &> /dev/null
if [ $? == 0 ]; then
    echo "Gcc arch: `gcc -march=native -Q --help=target | grep "march=  "`" >> {log_file}
fi
"""],
        redirect="",
        output_capture="",
    )

    executable("lscpu_test", "lscpu")

    executable("free_test", "free")

    workload(
        "standard",
        executables=[
            "spack_test",
            "gcc_version",
            "gcc_test",
            "lscpu_test",
            "free_test",
        ],
    )

    workload_group("all_workloads", workloads=["standard"])

    spack_regex = r"Spack tuple: (?P<platform>\S+?)-(?P<os>\S+?)-(?P<arch>\S+)"

    figure_of_merit(
        "Spack Platform",
        fom_regex=spack_regex,
        group_name="platform",
        units="",
    )

    figure_of_merit(
        "Spack OS", fom_regex=spack_regex, group_name="os", units=""
    )

    figure_of_merit(
        "Spack Arch", fom_regex=spack_regex, group_name="arch", units=""
    )

    figure_of_merit(
        "GCC Version",
        fom_regex=r"Gcc version:.* (?P<version>[0-9]+\.[0-9]+\.[0-9]+)",
        group_name="version",
        units="",
    )

    figure_of_merit(
        "GCC Arch",
        fom_regex=r"Gcc arch:\s+-march=\s+(?P<arch>\S+)",
        group_name="arch",
        units="",
    )

    figure_of_merit(
        "Lscpu Model",
        fom_regex=r"Model name:\s+(?P<model>.*)",
        group_name="model",
        units="",
    )

    figure_of_merit(
        "Total Ram",
        fom_regex=r"Mem:\s+(?P<total>[0-9\.]+)",
        group_name="total",
        units="b",
    )
