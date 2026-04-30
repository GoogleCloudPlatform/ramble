# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.syskit import *


class SpackSlurmSys(SystemBase):
    """Mock system that uses spack and slurm"""

    name = "spack-slurm-sys"

    default_workflow_manager("slurm")
    default_package_manager("spack")
    default_platform("mock-platform1")

    available_platforms(["mock-platform1"])

    with when("package_manager_family=spack"):
        auxiliary_software_file(
            "spack_packages",
            src_path="packages.yaml.tpl",
            dest_path="packages.yaml",
        )

    command_variable(
        "max_nodes",
        command="sinfo -p {slurm_partition} -O 'Nodes' | tail -n 1",
        dry_run_value="4",
        description="Number of nodes in a partition",
    )

    with when("platform=mock-platform1"):
        variable_defaults(
            variable_definitions={
                "slurm_partition": "mock-partition",
            }
        )
