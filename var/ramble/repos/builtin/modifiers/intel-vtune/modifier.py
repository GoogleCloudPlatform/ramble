# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class IntelVtune(BasicModifier):
    """Define a modifier for applying VTune profiling."""

    name = "intel-vtune"

    tags("profiler", "performance-analysis")

    maintainers("linsword13")

    mode("mpi", description="Mode for profiling mpi apps")
    default_mode("mpi")

    modifier_variable(
        "vtune_results_dir",
        default="{experiment_run_dir}/vtune_dir",
        description="Path to store darshan logs",
        mode="mpi",
    )

    modifier_variable(
        "vtune_args",
        default="-collect hpc-performance -r {vtune_results_dir}",
        description="vtune arguments",
        mode="mpi",
    )

    archive_pattern("{vtune_results_dir}/*")

    with when("package_manager_family=spack"):
        software_spec(
            "vtune",
            pkg_spec="intel-oneapi-vtune",
        )

        required_package("intel-oneapi-vtune")

    variable_modification(
        "mpi_command",
        "vtune {vtune_args} --",
        method="append",
        mode="mpi",
    )

    register_builtin(
        "setup_vtune_results_dir", required=True, injection_method="prepend"
    )

    def setup_vtune_results_dir(self):
        # For some analysis types (like per-node), the results_dir only acts as a prefix,
        # and a series of directories will be created, such as vtune_dir.node1, vtune_dir.node2
        return ["rm -rf {vtune_results_dir}*"]
