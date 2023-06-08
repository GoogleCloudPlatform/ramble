# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import re

import pytest

import spack.util.spack_yaml as syaml
import spack.util.spack_json as sjson

import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path')

workspace = RambleCommand('workspace')


@pytest.mark.filterwarnings("ignore:invalid decimal literal:DeprecationWarning")
def test_dryrun_chained_experiments(mutable_config,
                                    mutable_mock_workspace_path):
    test_config = r"""
ramble:
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
                n_ranks: '2'
        collective:
          template: true
          experiments:
            collective_chain:
              template: true
              variables:
                n_ranks: '2'
              chained_experiments:
              - name: 'intel-mpi-benchmarks.pingpong.pingpong_chain'
                command: '{execute_experiment}'
    gromacs:
      chained_experiments:
      - name: intel-mpi-benchmarks.collective.*
        command: '{execute_experiment}'
        order: 'after_root'
      workloads:
        water_bare:
          chained_experiments:
          - name: intel-mpi-benchmarks.*.collective_chain
            command: '{execute_experiment}'
            order: 'before_root'
            variables:
              n_ranks: '4'
          experiments:
            parent_test:
              chained_experiments:
              - name: intel-mpi-benchmarks.collective.collective_chain
                command: '{execute_experiment}'
                order: 'before_root'
              variables:
                n_nodes: '2'
  spack:
    concretized: true
    packages:
      gcc:
        spack_spec: gcc@9.3.0 target=x86_64
      impi2018:
        spack_spec: intel-mpi@2018.4.274
        compiler: gcc
      imb:
        spack_spec: intel-mpi-benchmarks
        compiler: gcc
      gromacs:
        spack_spec: gromacs
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

    mock_output_data = """
  14 100 1.5 1.0 2.0
"""

    workspace_name = 'test_dryrun_chained_experiments'
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)

        ws.dry_run = True
        ws._re_read()

        ws.run_pipeline('setup')

        template_dir = os.path.join(ws.experiment_dir, 'intel-mpi-benchmarks')
        assert not os.path.exists(template_dir)

        parent_dir = os.path.join(ws.experiment_dir, 'gromacs', 'water_bare',
                                  'parent_test')
        script = os.path.join(parent_dir, 'execute_experiment')
        assert os.path.exists(script)

        # Check all chained experiments are referenced
        with open(script, 'r') as f:
            parent_script_data = f.read()

        for chain_idx in [1, 3, 5]:
            chained_script = os.path.join(parent_dir, 'chained_experiments',
                                          f'{chain_idx}' +
                                          r'.intel-mpi-benchmarks.collective.collective_chain',
                                          'execute_experiment')
            assert os.path.exists(chained_script)
            assert chained_script in parent_script_data

            # Check that experiment 1 has n_ranks = 4 instead of 2
            if chain_idx == 3:
                with open(chained_script, 'r') as f:
                    assert 'mpirun -n 4' in f.read()

        expected_order = [
            re.compile(r'.*3.intel-mpi-benchmarks.collective.collective_chain.*'),
            re.compile(r'.*5.intel-mpi-benchmarks.collective.collective_chain.*'),
            re.compile(r'.*4.intel-mpi-benchmarks.pingpong.pingpong_chain.*'),
            re.compile(r'.*2.intel-mpi-benchmarks.pingpong.pingpong_chain.*'),
            re.compile(r'.*1.intel-mpi-benchmarks.collective.collective_chain.*'),
            re.compile(r'.*0.intel-mpi-benchmarks.pingpong.pingpong_chain.*')
        ]

        # Check prepend / append order is correct
        with open(script, 'r') as f:

            for line in f.readlines():
                if expected_order[0].match(line):
                    expected_order.pop(0)

        # Ensure results contain chain information, and properly extract figures of merit
        chain_exp_name = r'3.intel-mpi-benchmarks.collective.collective_chain'
        output_path_3 = os.path.join(parent_dir, 'chained_experiments',
                                     chain_exp_name,
                                     f'gromacs.water_bare.parent_test.chain.{chain_exp_name}.out')

        with open(output_path_3, 'w+') as f:
            f.write(mock_output_data)

        ws.run_pipeline('analyze')
        ws.dump_results(output_formats=['json', 'yaml'])

        base_name = r'gromacs.water_bare.parent_test'
        collective_name = r'intel-mpi-benchmarks.collective.collective_chain'
        pingpong_name = r'intel-mpi-benchmarks.pingpong.pingpong_chain'

        chain_def = [f'{base_name}.chain.3.{collective_name}',
                     f'{base_name}.chain.5.{collective_name}',
                     f'{base_name}',
                     f'{base_name}.chain.4.{pingpong_name}',
                     f'{base_name}.chain.2.{pingpong_name}',
                     f'{base_name}.chain.1.{collective_name}',
                     f'{base_name}.chain.0.{pingpong_name}',
                     ]

        names = ['results.latest.json', 'results.latest.yaml']
        loaders = [sjson.load, syaml.load]
        for name, loader in zip(names, loaders):
            with open(os.path.join(ws.root, name), 'r') as f:
                data = loader(f)

                assert 'experiments' in data

                for exp_def in data['experiments']:
                    if exp_def['name'] == r'gromacs.water_bare.parent_test.' + \
                            r'chain.3.intel-mpi-benchmarks.collective.collective_chain':
                        assert exp_def['RAMBLE_STATUS'] == 'SUCCESS'
                    else:
                        assert exp_def['RAMBLE_STATUS'] == 'FAILED'
                    assert exp_def['EXPERIMENT_CHAIN'] == chain_def
