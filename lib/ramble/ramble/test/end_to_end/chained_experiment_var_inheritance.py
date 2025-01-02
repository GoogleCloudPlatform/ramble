# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.filters
import ramble.pipeline
import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


@pytest.mark.filterwarnings("ignore:invalid decimal literal")
def test_chained_experiment_variable_inheritance(mutable_config, mutable_mock_workspace_path):
    test_config = r"""
ramble:
  variants:
    package_manager: spack
  formatted_executables:
    command:
      join_separator: '\n'
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '10'
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    intel-mpi-benchmarks:
      template: true
      workloads:
        pingpong:
          template: true
          experiments:
            pingpong_chain:
              template: true
              variables:
                n_ranks: '1'
                n_nodes: '1'
        collective:
          template: true
          experiments:
            collective_chain:
              template: true
              variables:
                n_ranks: '1'
                n_nodes: '1'
              chained_experiments:
              - name: 'intel-mpi-benchmarks.pingpong.pingpong_chain'
                command: '{execute_experiment}'
                inherit_variables:
                - n_nodes
                - n_ranks
    gromacs:
      chained_experiments:
      - name: intel-mpi-benchmarks.collective.*
        command: '{execute_experiment}'
        order: 'after_root'
        inherit_variables:
        - n_ranks
        - n_nodes
      workloads:
        water_bare:
          chained_experiments:
          - name: intel-mpi-benchmarks.*.collective_chain
            command: '{execute_experiment}'
            order: 'before_root'
            inherit_variables:
            - n_ranks
            - n_nodes
          experiments:
            parent_test:
              chained_experiments:
              - name: intel-mpi-benchmarks.collective.collective_chain
                command: '{execute_experiment}'
                order: 'before_root'
                inherit_variables:
                - n_nodes
                - n_ranks
              variables:
                n_nodes: '2'
  software:
    packages:
      gcc:
        pkg_spec: gcc@9.3.0 target=x86_64
      impi2018:
        pkg_spec: intel-mpi@2018.4.274
        compiler: gcc
      imb:
        pkg_spec: intel-mpi-benchmarks
        compiler: gcc
      gromacs:
        pkg_spec: gromacs
        compiler: gcc
    environments:
      intel-mpi-benchmarks:
        packages:
        - imb
        - impi2018
      gromacs:
        packages:
        - gromacs
        - impi2018
"""

    setup_type = ramble.pipeline.pipelines.setup
    setup_cls = ramble.pipeline.pipeline_class(setup_type)

    filters = ramble.filters.Filters()

    workspace_name = "test_chained_experiment_variable_inheritance"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws.dry_run = True
        ws._re_read()

        setup_pipeline = setup_cls(ws, filters)
        setup_pipeline.run()

        template_dir = os.path.join(ws.experiment_dir, "intel-mpi-benchmarks")
        assert not os.path.exists(template_dir)

        parent_dir = os.path.join(ws.experiment_dir, "gromacs", "water_bare", "parent_test")
        script = os.path.join(parent_dir, "execute_experiment")
        assert os.path.exists(script)

        # Check all chained experiments have the correct arguments
        with open(script) as f:
            parent_script_data = f.read()

        for chain_idx in [1, 3, 5]:
            chained_script = os.path.join(
                parent_dir,
                "chained_experiments",
                f"{chain_idx}" + r".intel-mpi-benchmarks.collective.collective_chain",
                "execute_experiment",
            )
            assert os.path.exists(chained_script)
            assert chained_script in parent_script_data

            with open(chained_script) as f:
                assert "mpirun -n 20 -ppn 10" in f.read()
