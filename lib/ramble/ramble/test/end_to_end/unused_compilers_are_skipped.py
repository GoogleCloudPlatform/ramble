# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import glob

import pytest

import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand
from ramble.test.dry_run_helpers import search_files_for_string


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path')

workspace = RambleCommand('workspace')


def test_unused_compilers_are_skipped(mutable_config, mutable_mock_workspace_path, capsys):
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '10'
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    wrfv4:
      workloads:
        CONUS_12km:
          experiments:
            test{n_nodes}_{env_name}:
              variables:
                n_nodes: '1'
  spack:
    concretized: true
    packages:
      gcc8:
        spack_spec: gcc@8.5.0
      gcc9:
        spack_spec: gcc@9.3.0
      gcc10:
        spack_spec: gcc@10.1.0
      intel:
        spack_spec: intel-mpi@2018.4.274
        compiler: gcc8
      wrf:
        spack_spec: wrf@4.2 build_type=dm+sm compile_type=em_real nesting=basic ~chem ~pnetcdf
        compiler: gcc8
    environments:
      wrfv4:
        packages:
        - wrf
        - intel
"""

    workspace_name = 'test_unused_compilers_are_skipped'
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)

        ws.dry_run = True
        ws._re_read()

        ws.run_pipeline('setup')

        required_compiler_str = "gcc@8.5.0"
        unused_gcc9_str = "gcc@9.3.0"
        unused_gcc10_str = "gcc@10.1.0"

        out_files = glob.glob(os.path.join(ws.log_dir, '**', '*.out'), recursive=True)

        assert search_files_for_string(out_files, required_compiler_str) is True
        assert search_files_for_string(out_files, unused_gcc9_str) is False
        assert search_files_for_string(out_files, unused_gcc10_str) is False
