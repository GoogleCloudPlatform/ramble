# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.wm.builtin.slurm import Slurm as SlurmBase
from ramble.wmkit import *


class SlurmIntelMpi(SlurmBase):
    """
    A slurm workflow manager that sets reasonable defaults for
    making srun work with intel mpi.
    See https://slurm.schedmd.com/mpi_guide.html#intel_srun.
    """

    name = "slurm-intel-mpi"

    maintainers("linsword13")

    tags("workflow", "slurm", "intel-mpi")

    workflow_manager_variable(
        name="srun_args",
        default="-n {n_ranks} --mpi=pmi2",
        description="Arguments passed to srun",
    )

    workflow_manager_variable(
        name="pmi2_lib_path",
        default="/usr/local/lib/libpmi2.so",
        description="Path to the libpmi2 library",
    )

    register_builtin("set_pmi2_path", injection_method="prepend")

    def set_pmi2_path(self):
        lib_path = self.app_inst.expander.expand_var_name("pmi2_lib_path")
        if not lib_path:
            return []
        return [
            f'export I_MPI_PMI_LIBRARY="${{I_MPI_PMI_LIBRARY:-{lib_path}}}"'
        ]
