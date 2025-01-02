# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Hostname(ExecutableApplication):
    """This is an example application that will simply run the hostname command"""  # noqa: E501

    name = "hostname"

    tags("test-app")

    maintainers("douglasjacobsen")

    # TODO: Remove in the future. local should be replaced by serial in all cases.
    executable(
        "local", "hostname", use_mpi=False, output_capture=OUTPUT_CAPTURE.ALL
    )

    executable(
        "local_bg",
        "(sleep 5; hostname)",
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
        run_in_background=True,
    )
    executable(
        "local_bg2",
        "(sleep 10; hostname)",
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
        run_in_background=True,
    )
    executable(
        "serial",
        "hostname",
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )
    executable(
        "parallel",
        "hostname",
        use_mpi=True,
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    workload("local", executable="local")
    workload("local_bg", executables=["local_bg", "local_bg2"])
    workload("serial", executable="serial")
    workload("parallel", executable="parallel")

    figure_of_merit(
        "possible hostname",
        fom_regex=r"(?P<hostname>\S+)\s*",
        group_name="hostname",
        units="",
    )

    success_criteria("wrote_anything", mode="string", match=r".*")
