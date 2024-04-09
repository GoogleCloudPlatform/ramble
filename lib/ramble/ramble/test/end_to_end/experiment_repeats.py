# Copyright 2022-2024 Google LLC and other Ramble developers
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


def test_gromacs_repeats(mutable_config, mutable_mock_workspace_path):
    test_config = """
ramble:
  config:
    n_repeats: '2'
  variables:
    processes_per_node: 16
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: '{execute_experiment}'
  applications:
    gromacs:
      workloads:
        water_gmx50:
          experiments:
            pme_single_rank:
              variables:
                n_ranks: '1'
                n_threads: '1'
                size: '0003'
                type: 'pme'
            rf_single_rank:
              n_repeats: '1'
              variables:
                n_ranks: '1'
                n_threads: '1'
                size: '0003'
                type: 'rf'
        water_bare:
          experiments:
            pme_single_rank:
              variables:
                n_ranks: '1'
                n_threads: '1'
                size: '0003'
                type: 'pme'
  spack:
    packages:
      gcc:
        spack_spec: gcc@8.5.0
      intel-mpi:
        spack_spec: intel-mpi@2018.4.274
        compiler: gcc
      gromacs:
        spack_spec: gromacs@2021.6
        compiler: gcc
    environments:
      gromacs:
        packages:
        - gromacs
        - intel-mpi
"""

    workspace_name = 'test_end_to_end_repeats'
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        aux_software_path = os.path.join(ws1.config_dir,
                                         ramble.workspace.auxiliary_software_dir_name)
        aux_software_files = ['packages.yaml', 'my_test.sh']

        with open(config_path, 'w+') as f:
            f.write(test_config)

        for file in aux_software_files:
            file_path = os.path.join(aux_software_path, file)
            with open(file_path, 'w+') as f:
                f.write('')

        # Write a command template
        with open(os.path.join(ws1.config_dir, 'full_command.tpl'), 'w+') as f:
            f.write('{command}')

        ws1._re_read()

        workspace('setup', '--dry-run', global_args=['-w', workspace_name])

        out_files = glob.glob(os.path.join(ws1.log_dir, '**', '*.out'), recursive=True)

        assert search_files_for_string(
            out_files, 'Would download https://ftp.gromacs.org/pub/benchmarks/water_GMX50_bare.tar.gz') # noqa

        # Test software directories
        software_dirs = ['gromacs.water_gmx50', 'gromacs.water_bare']
        software_base_dir = os.path.join(ws1.root, ramble.workspace.workspace_software_path)
        assert os.path.exists(software_base_dir)
        for software_dir in software_dirs:
            software_path = os.path.join(software_base_dir, software_dir)
            assert os.path.exists(software_path)

            spack_file = os.path.join(software_path, 'spack.yaml')
            assert os.path.exists(spack_file)
            for file in aux_software_files:
                file_path = os.path.join(software_path, file)
                assert os.path.exists(file_path)

            lock_file = os.path.join(software_path, 'spack.lock')
            with open(lock_file, 'w+') as f:
                f.write('{\n')
                f.write('\t"test_key": "val"\n')
                f.write('}\n')

        # Each tuple (workload, exp base, n_repeats) expands to 1 base exp plus n_repeats exps
        expected_experiments = [
            ('water_gmx50', 'pme_single_rank', 2),
            ('water_gmx50', 'rf_single_rank', 1),
            ('water_bare', 'pme_single_rank', 2)
        ]

        # Test experiment directories
        for wl, exp, repeats in expected_experiments:
            # Test that the base experiment directory is not created
            base_exp_dir = os.path.join(ws1.root, 'experiments', 'gromacs', wl, exp)
            assert not os.path.isdir(base_exp_dir)
            assert not os.path.exists(os.path.join(base_exp_dir, 'execute_experiment'))

            # Test each of the repeat directories
            for r in range(1, repeats + 1):
                repeat_exp_dir = f'{base_exp_dir}.{r}'
                assert os.path.isdir(repeat_exp_dir)
                assert os.path.exists(os.path.join(repeat_exp_dir, 'execute_experiment'))

                # TODO: Create fake experiment figures of merit.
                with open(os.path.join(repeat_exp_dir, 'md.log'), 'w+') as f:
                    f.write('               Core t (s)   Wall t (s)        (%)\n')
                    f.write(f'       Time:       {r}{r}.{r}{r}{r}       {r}.{r}{r}{r}    1000.1\n')
                    f.write('                 (ns/day)    (hour/ns)\n')

            # Test that the number of repeats is not exceeded
            excess_repeat_exp_dir = f'{base_exp_dir}.{repeats + 1}'
            assert not os.path.isdir(excess_repeat_exp_dir)
            assert not os.path.exists(os.path.join(excess_repeat_exp_dir, 'execute_experiment'))

        workspace('analyze', '-f', 'text', 'json', 'yaml', global_args=['-w', workspace_name])

        text_results_files = glob.glob(os.path.join(ws1.root, 'results*.txt'))
        json_results_files = glob.glob(os.path.join(ws1.root, 'results*.json'))
        yaml_results_files = glob.glob(os.path.join(ws1.root, 'results*.yaml'))

        # Match both the file and the simlink
        assert len(text_results_files) == 2
        assert len(json_results_files) == 2
        assert len(yaml_results_files) == 2

        for text_result in text_results_files:
            with open(text_result, 'r') as f:
                data = f.read()
                assert 'Core Time = 11.111 s' in data
                assert 'Core Time = 22.222 s' in data
                assert 'summary::mean = 16.666 s' in data
                assert 'summary::variance = 61.727 s^2' in data
