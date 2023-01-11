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
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures(
    'mutable_mock_workspace_path', 'config')

workspace = RambleCommand('workspace')


def test_wrfv4_dry_run():
    test_config = """
ramble:
  mpi:
    command: mpirun
    args:
    - '-n'
    - '{n_ranks}'
    - '-ppn'
    - '{processes_per_node}'
    - '-hostfile'
    - 'hostfile'
  batch:
    submit: 'batch_submit {execute_experiment}'
  variables:
    partition: ['part1', 'part2']
    processes_per_node: ['16', '36']
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    wrfv4:
      variables:
        spec_name: ['wrfv4', 'wrfv4-portable']
      workloads:
        CONUS_12km:
          experiments:
            scaling_{n_nodes}_{partition}_{spec_name}:
              env-vars:
                set:
                  OMP_NUM_THREADS: '{n_threads}'
                  TEST_VAR: '1'
                append:
                - var-separator: ', '
                  vars:
                    TEST_VAR: 'add_var'
                - paths:
                    TEST_VAR: 'new_path'
                prepend:
                - paths:
                    TEST_VAR: 'pre_path'
                unset:
                - TEST_VAR
              variables:
                n_nodes: ['1', '2', '4', '8', '16']
              matrix:
              - n_nodes
              - spec_name
spack:
  concretized: true
  compilers:
    gcc:
      base: gcc
      version: 8.5.0
  mpi_libraries:
    intel:
      base: intel-mpi
      version: 2018.4.274
  applications:
    wrfv4:
      wrf:
        base: wrf
        version: 4.2
        variants: 'build_type=dm+sm compile_type=em_real nesting=basic ~chem ~pnetcdf'
        compiler: gcc
        mpi: intel
    wrfv4-portable:
      wrf:
        base: wrf
        version: 4.2
        variants: 'build_type=dm+sm compile_type=em_real nesting=basic ~chem ~pnetcdf'
        compiler: gcc
        mpi: intel
        target: 'x86_64'
"""

    test_licenses = """
licenses:
  wrfv4:
    set:
      WRF_LICENSE: port@server
"""

    workspace_name = 'test_end_to_end_wrfv4'
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)
        license_path = os.path.join(ws1.config_dir, 'licenses.yaml')

        with open(config_path, 'w+') as f:
            f.write(test_config)

        with open(license_path, 'w+') as f:
            f.write(test_licenses)

        # Write a command template
        with open(os.path.join(ws1.config_dir, 'full_command.tpl'), 'w+') as f:
            f.write('{command}')

        ws1._re_read()

        output = workspace('setup', '--dry-run', global_args=['-w', workspace_name])
        assert "Would download https://www2.mmm.ucar.edu/wrf/users/benchmark/v42/v42_bench_conus12km.tar.gz" in output

        expected_experiments = [
            'scaling_1_part1_wrfv4',
            'scaling_2_part1_wrfv4',
            'scaling_4_part1_wrfv4',
            'scaling_8_part1_wrfv4',
            'scaling_16_part1_wrfv4',
            'scaling_1_part2_wrfv4',
            'scaling_2_part2_wrfv4',
            'scaling_4_part2_wrfv4',
            'scaling_8_part2_wrfv4',
            'scaling_16_part2_wrfv4',
            'scaling_1_part1_wrfv4-portable',
            'scaling_2_part1_wrfv4-portable',
            'scaling_4_part1_wrfv4-portable',
            'scaling_8_part1_wrfv4-portable',
            'scaling_16_part1_wrfv4-portable',
            'scaling_1_part2_wrfv4-portable',
            'scaling_2_part2_wrfv4-portable',
            'scaling_4_part2_wrfv4-portable',
            'scaling_8_part2_wrfv4-portable',
            'scaling_16_part2_wrfv4-portable'
        ]

        # Test experiment directories
        for exp in expected_experiments:
            exp_dir = os.path.join(ws1.root, 'experiments', 'wrfv4', 'CONUS_12km', exp)
            assert os.path.isdir(exp_dir)
            assert os.path.exists(os.path.join(exp_dir, 'execute_experiment'))
            assert os.path.exists(os.path.join(exp_dir, 'full_command'))

            with open(os.path.join(exp_dir, 'full_command'), 'r') as f:
                data = f.read()
                # Test the license exists
                assert "export WRF_LICENSE=port@server" in data

                # Test the required environment variables exist
                assert "export OMP_NUM_THREADS='1'" in data
                assert "export TEST_VAR=1" in data
                assert 'unset TEST_VAR' in data

                # Test the expected portions of the exection command exist
                assert "sed -i -e 's/ start_hour.*/ start_hour" in data
                assert "sed -i -e 's/ restart .*/ restart" in data
                assert "mpirun" in data
                assert "wrf.exe" in data

                # Test the run script has a reference to the experiment log file
                assert os.path.join(exp_dir, f'{exp}.out') in data

            with open(os.path.join(exp_dir, 'execute_experiment'), 'r') as f:
                data = f.read()
                # Test the license exists
                assert "export WRF_LICENSE=port@server" in data

                # Test the required environment variables exist
                assert "export OMP_NUM_THREADS='1'" in data
                assert "export TEST_VAR=1" in data
                assert 'unset TEST_VAR' in data

                # Test the expected portions of the exection command exist
                assert "sed -i -e 's/ start_hour.*/ start_hour" in data
                assert "sed -i -e 's/ restart .*/ restart" in data
                assert "mpirun" in data
                assert "wrf.exe" in data

                # Test the run script has a reference to the experiment log file
                assert os.path.join(exp_dir, f'{exp}.out') in data

                # Test that spack is used
                assert "spack env activate" in data

            # Create fake figures of merit.
            with open(os.path.join(exp_dir, 'rsl.out.0000'), 'w+') as f:
                for i in range(1, 6):
                    f.write(f'Timing for main {i}{i}.{i}\n')

            # Create files that match archive patterns
            for i in range(0, 5):
                new_name = 'rsl.error.000%s' % i
                new_file = os.path.join(exp_dir, new_name)

                f = open(new_file, 'w+')
                f.close()

        output = workspace('analyze', '-f', 'text',
                           'json', 'yaml', global_args=['-w', workspace_name])
        text_results_files = glob.glob(os.path.join(ws1.root, 'results*.txt'))
        json_results_files = glob.glob(os.path.join(ws1.root, 'results*.json'))
        yaml_results_files = glob.glob(os.path.join(ws1.root, 'results*.yaml'))
        assert len(text_results_files) == 1
        assert len(json_results_files) == 1
        assert len(yaml_results_files) == 1

        with open(text_results_files[0], 'r') as f:
            data = f.read()
            assert 'Average Timestep Time = 3.3 s' in data
            assert 'Cumulative Timestep Time = 16.5 s' in data
            assert 'Minimum Timestep Time = 1.1 s' in data
            assert 'Maximum Timestep Time = 5.5 s' in data
            assert 'Avg. Max Ratio Time = 0.6' in data
            assert 'Number of timesteps = 5' in data

        output = workspace('archive', global_args=['-w', workspace_name])

        assert ws1.latest_archive
        assert os.path.exists(ws1.latest_archive_path)

        for exp in expected_experiments:
            exp_dir = os.path.join(ws1.latest_archive_path, 'experiments',
                                   'wrfv4', 'CONUS_12km', exp)
            assert os.path.isdir(exp_dir)
            assert os.path.exists(os.path.join(exp_dir, 'execute_experiment'))
            assert os.path.exists(os.path.join(exp_dir, 'full_command'))
            assert os.path.exists(os.path.join(exp_dir, 'rsl.out.0000'))
            for i in range(0, 5):
                assert os.path.exists(os.path.join(exp_dir, f'rsl.error.000{i}'))
