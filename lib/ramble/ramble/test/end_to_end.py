# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import glob
import re

import pytest

import spack.util.spack_yaml as syaml
import spack.util.spack_json as sjson

import ramble.workspace
import ramble.config
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path')

workspace = RambleCommand('workspace')


def test_wrfv4_dry_run(mutable_config, mutable_mock_workspace_path):
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
              success_criteria:
              - name: 'timing'
                mode: 'string'
                match: '.*Timing for main.*'
                file: '{experiment_run_dir}/rsl.out.0000'
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

        aux_software_path = os.path.join(ws1.config_dir,
                                         ramble.workspace.auxiliary_software_dir_name)
        aux_software_files = ['packages.yaml', 'my_test.sh']

        with open(config_path, 'w+') as f:
            f.write(test_config)

        with open(license_path, 'w+') as f:
            f.write(test_licenses)

        for file in aux_software_files:
            file_path = os.path.join(aux_software_path, file)
            with open(file_path, 'w+') as f:
                f.write('')

        # Write a command template
        with open(os.path.join(ws1.config_dir, 'full_command.tpl'), 'w+') as f:
            f.write('{command}')

        ws1._re_read()

        output = workspace('setup', '--dry-run', global_args=['-w', workspace_name])
        assert "Would download https://www2.mmm.ucar.edu/wrf/users/benchmark/v422/v42_bench_conus12km.tar.gz" in output

        # Test software directories
        software_dirs = ['wrfv4.CONUS_12km', 'wrfv4-portable.CONUS_12km']
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
                assert 'export OMP_NUM_THREADS="1"' in data
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
                assert 'export OMP_NUM_THREADS="1"' in data
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
        text_simlink_results_files = glob.glob(os.path.join(ws1.root, 'results.latest.txt'))
        text_results_files = glob.glob(os.path.join(ws1.root, 'results*.txt'))
        json_results_files = glob.glob(os.path.join(ws1.root, 'results*.json'))
        yaml_results_files = glob.glob(os.path.join(ws1.root, 'results*.yaml'))
        assert len(text_simlink_results_files) == 1
        assert len(text_results_files) == 2
        assert len(json_results_files) == 2
        assert len(yaml_results_files) == 2

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


def test_hpl_dry_run(mutable_config, mutable_mock_workspace_path):
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
    processes_per_node: 16
    n_threads: 1
  applications:
    hpl:
      workloads:
        standard:
          experiments:
            test_exp:
              variables:
                n_ranks: 4
spack:
  concretized: true
  compilers:
    gcc9:
      base: gcc
      version: 9.3.0
  mpi_libraries:
    impi2018:
      base: intel-mpi
      version: 2018.4.274
  applications:
    hpl:
      hpl:
        base: hpl
        version: '2.3'
        variants: +openmp
        compiler: gcc9
        mpi: impi2018
"""

    workspace_name = 'test_end_to_end_hpl'
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)

        # Write a command template
        with open(os.path.join(ws1.config_dir, 'full_command.tpl'), 'w+') as f:
            f.write('{command}')

        ws1._re_read()

        workspace('setup', '--dry-run', global_args=['-w', workspace_name])

        # Test software directories
        software_dirs = ['hpl.standard']
        software_base_dir = os.path.join(ws1.root, ramble.workspace.workspace_software_path)
        assert os.path.exists(software_base_dir)
        for software_dir in software_dirs:
            software_path = os.path.join(software_base_dir, software_dir)
            assert os.path.exists(software_path)

            spack_file = os.path.join(software_path, 'spack.yaml')
            assert os.path.exists(spack_file)

        expected_experiments = ['test_exp']

        for exp in expected_experiments:
            exp_dir = os.path.join(ws1.root, 'experiments',
                                   'hpl', 'standard', exp)
            assert os.path.isdir(exp_dir)
            assert os.path.exists(os.path.join(exp_dir, 'execute_experiment'))


def test_dependency_dry_run(mutable_config, mutable_mock_workspace_path):
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
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    openfoam:
      workloads:
        motorbike:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
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
    openfoam:
      flex:
        base: flex
        version: 2.6.4
      openfoam:
        base: openfoam
        compiler: gcc
        mpi: intel
        target: 'x86_64'
        dependencies:
          - flex
"""
    workspace_name = 'test_dependant_spec'
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)
        ws._re_read()

        workspace('setup', '--dry-run', global_args=['-w', workspace_name])

        deps = ws.get_spack_dict()['applications']['openfoam']['openfoam']['dependencies']
        assert 'flex' in deps

        software_dir = 'openfoam.motorbike'
        software_base_dir = os.path.join(ws.root, ramble.workspace.workspace_software_path)
        assert os.path.exists(software_base_dir)

        software_path = os.path.join(software_base_dir, software_dir)
        assert os.path.exists(software_path)

        spack_file = os.path.join(software_path, 'spack.yaml')

        import re
        regex = re.compile(r".*openfoam.*\^flex.*")
        with open(spack_file, 'r') as f:
            data = f.read()
            result = regex.search(data)

            assert result


def test_missing_required_dry_run(mutable_config, mutable_mock_workspace_path):
    """Tests tty.die at end of ramble.application_types.spack._create_spack_env"""
    test_config = """
ramble:
  mpi:
    command: mpirun
    args:
    - -n
    - '{n_ranks}'
    - -ppn
    - '{processes_per_node}'
    - -hostfile
    - hostfile
  batch:
    submit: 'sbatch {execute_experiment}'
  variables:
    processes_per_node: 30
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    wrfv3:
      workloads:
        CONUS_2p5km:
          experiments:
            eight_node:
              variables:
                n_nodes: '8'
spack:
  concretized: true
  compilers:
    gcc8:
      base: gcc
      version: 8.2.0
      target: x86_64
  mpi_libraries:
    impi2018:
      base: intel-mpi
      version: 2018.4.274
      target: x86_64
  applications:
    wrfv3:
      my-wrf:
        base: wrf
        version: 3.9.1.1
        variants: build_type=dm+sm compile_type=em_real nesting=basic ~pnetcdf
        compiler: gcc8
        mpi: impi2018
"""

    workspace_name = 'test_missing_required_dry_run'
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)
        ws._re_read()

        output = workspace('setup',
                           '--dry-run',
                           global_args=['-w', workspace_name],
                           fail_on_error=False)

        assert "Software spec wrf is not defined in context wrfv3" in output


def test_env_var_builtin(mutable_config, mutable_mock_workspace_path, mock_applications):
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
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    interleved-env-vars:
      workloads:
        test_wl:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
              env-vars:
                set:
                  MY_VAR: 'TEST'
        test_wl2:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
              env-vars:
                set:
                  MY_VAR: 'TEST'
        test_wl3:
          experiments:
            simple_test:
              variables:
                n_nodes: 1
              env-vars:
                set:
                  MY_VAR: 'TEST'
spack:
  concretized: true
  compilers: {}
  mpi_libraries: {}
  applications: {}
"""
    workspace_name = 'test_env_var_command'
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)
        ws._re_read()

        workspace('setup', '--dry-run', global_args=['-w', workspace_name])

        experiment_root = ws.experiment_dir
        exp1_dir = os.path.join(experiment_root, 'interleved-env-vars', 'test_wl', 'simple_test')
        exp1_script = os.path.join(exp1_dir, 'execute_experiment')
        exp2_dir = os.path.join(experiment_root, 'interleved-env-vars', 'test_wl2', 'simple_test')
        exp2_script = os.path.join(exp2_dir, 'execute_experiment')
        exp3_dir = os.path.join(experiment_root, 'interleved-env-vars', 'test_wl3', 'simple_test')
        exp3_script = os.path.join(exp3_dir, 'execute_experiment')

        import re
        export_regex = re.compile(r'export MY_VAR=TEST')
        cmd1_regex = re.compile('bar >>')
        cmd2_regex = re.compile('baz >>')
        cmd3_regex = re.compile('foo >>')

        # Assert experiment 1 has exports before commands
        with open(exp1_script, 'r') as f:
            cmd_found = False
            export_found = False
            for line in f.readlines():
                if not export_found and export_regex.search(line):
                    assert not cmd_found
                    export_found = True
                if export_found and cmd1_regex.search(line):
                    cmd_found = True
            assert cmd_found and export_found

        # Assert experiment 2 has commands before exports
        with open(exp2_script, 'r') as f:
            cmd_found = False
            export_found = False
            for line in f.readlines():
                if not cmd_found and cmd2_regex.search(line):
                    assert not export_found
                    cmd_found = True
                if cmd_found and export_regex.search(line):
                    export_found = True
            assert cmd_found and export_found

        # Assert experiment 3 has exports before commands
        with open(exp3_script, 'r') as f:
            cmd_found = False
            export_found = False
            for line in f.readlines():
                if not export_found and export_regex.search(line):
                    assert not cmd_found
                    export_found = True
                if export_found and cmd3_regex.search(line):
                    cmd_found = True
            assert cmd_found and export_found


def test_configvar_dry_run(mutable_config, mutable_mock_workspace_path):
    test_scopes = ['site', 'system', 'user']

    var_name1 = 'test1'
    var_name2 = 'envtestvar'
    var_val = 3

    test_config = """
ramble:
  mpi:
    command: mpirun
    args:
    - '-n'
    - '{{n_ranks}}'
    - '-ppn'
    - '{{processes_per_node}}'
    - '-hostfile'
    - 'hostfile'
  batch:
    submit: 'batch_submit {{execute_experiment}}'
  variables:
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    openfoam:
      workloads:
        motorbike:
          experiments:
            "{}_test_{{{var_name}}}":
              variables:
                n_ranks: "{{{var_name}}}"
            "{}_test_{{{var_name}}}":
              variables:
                n_ranks: "{{{var_name}}}"
            "{}_test_{{{var_name}}}":
              variables:
                n_ranks: "{{{var_name}}}"
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
    openfoam:
      openfoam:
        base: openfoam
        compiler: gcc
        mpi: intel
        target: 'x86_64'
""" .format(*test_scopes, var_name=var_name1)

    config = ramble.main.RambleCommand('config')

    expected_experiments = []
    for scope in test_scopes:
        config('--scope', scope, 'add', f'config:variables:{var_name1}:{var_val}')
        expected_experiments.append(f'{scope}_test_{var_val}')

    for i, scope in enumerate(test_scopes):
        config('--scope', scope, 'add', f'config:env-vars:set:{var_name2}{i}:{var_val}')

    workspace_name = 'test_sitevar'
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)
        ws._re_read()

        workspace('setup', '--dry-run', global_args=['-w', workspace_name])

        software_dir = 'openfoam.motorbike'
        software_base_dir = os.path.join(ws.root, ramble.workspace.workspace_software_path)
        assert os.path.exists(software_base_dir)

        software_path = os.path.join(software_base_dir, software_dir)
        assert os.path.exists(software_path)

        for i, exp in enumerate(expected_experiments):
            exp_dir = os.path.join(ws.root, 'experiments', 'openfoam', 'motorbike', exp)
            assert os.path.isdir(exp_dir)
            assert os.path.exists(os.path.join(exp_dir, 'execute_experiment'))

            with open(os.path.join(exp_dir, 'execute_experiment'), 'r') as f:
                data = f.read()
                # Test the license exists
                assert f"export {var_name2}{i}={var_val}" in data


def test_custom_executables(mutable_config, mutable_mock_workspace_path, mock_applications):
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
    partition: 'part1'
    processes_per_node: '16'
    n_threads: '1'
  applications:
    interleved-env-vars:
      workloads:
        test_wl3:
          experiments:
            simple_test:
              internals:
                custom_executables:
                  lscpu:
                    template:
                    - 'lscpu'
                    use_mpi: false
                    redirect: '{log_file}'
                    output_capture: '>>'
                executables:
                - lscpu
                - builtin::env_vars
                - baz
              variables:
                n_nodes: 1
              env-vars:
                set:
                  MY_VAR: 'TEST'
spack:
  concretized: true
  compilers: {}
  mpi_libraries: {}
  applications: {}
"""
    workspace_name = 'test_custom_executables'
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(test_config)
        ws._re_read()

        workspace('setup', '--dry-run', global_args=['-w', workspace_name])

        experiment_root = ws.experiment_dir
        exp_dir = os.path.join(experiment_root, 'interleved-env-vars', 'test_wl3', 'simple_test')
        exp_script = os.path.join(exp_dir, 'execute_experiment')

        import re
        custom_regex = re.compile('lscpu >>')
        export_regex = re.compile(r'export MY_VAR=TEST')
        cmd_regex = re.compile('foo >>')

        # Assert command order is: lscpu -> export -> foo
        with open(exp_script, 'r') as f:
            custom_found = False
            cmd_found = False
            export_found = False

            for line in f.readlines():
                if not custom_found and custom_regex.search(line):
                    assert not cmd_found
                    assert not export_found
                    custom_found = True
                if custom_found and not export_found and export_regex.search(line):
                    assert not cmd_found
                    export_found = True
                if export_found and not cmd_found and cmd_regex.search(line):
                    cmd_found = True
            assert custom_found and cmd_found and export_found


def test_unused_compilers_are_skipped(mutable_config, mutable_mock_workspace_path, capsys):
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
    processes_per_node: '10'
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    wrfv4:
      workloads:
        CONUS_12km:
          experiments:
            test{n_nodes}_{spec_name}:
              variables:
                n_nodes: '1'
spack:
  concretized: true
  compilers:
    gcc8:
      base: gcc
      version: 8.5.0
    gcc9:
      base: gcc
      version: 9.3.0
    gcc10:
      base: gcc
      version: 10.1.0
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
        compiler: gcc8
        mpi: intel
"""

    workspace_name = 'test_unused_compilers_are_skipped'
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws.dry_run = True
    ws._re_read()

    ws.run_pipeline('setup')
    captured = capsys.readouterr()

    required_compiler_str = "gcc @8.5.0"
    unused_gcc9_str = "gcc @9.3.0"
    unused_gcc10_str = "gcc @10.1.0"

    assert required_compiler_str in captured.out
    assert unused_gcc9_str not in captured.out
    assert unused_gcc10_str not in captured.out


def test_dryrun_copies_external_env(mutable_config, mutable_mock_workspace_path, tmpdir):
    test_spack_env = """
spack:
  specs: [ 'zlib' ]
"""

    env_path = str(tmpdir)
    with open(os.path.join(env_path, 'spack.yaml'), 'w+') as f:
        f.write(test_spack_env)

    with open(os.path.join(env_path, 'spack.lock'), 'w+') as f:
        f.write(test_spack_env)

    test_config = f"""
ramble:
  mpi:
    command: mpirun
    args:
    - '-n'
    - '{{n_ranks}}'
    - '-ppn'
    - '{{processes_per_node}}'
    - '-hostfile'
    - 'hostfile'
  batch:
    submit: 'batch_submit {{execute_experiment}}'
  variables:
    processes_per_node: '10'
    n_ranks: '{{processes_per_node}}*{{n_nodes}}'
    n_threads: '1'
  applications:
    wrfv4:
      workloads:
        CONUS_12km:
          experiments:
            test{{n_nodes}}_{{spec_name}}:
              variables:
                n_nodes: '1'
spack:
  concretized: true
  compilers:
    gcc8:
      base: gcc
      version: 8.5.0
    gcc9:
      base: gcc
      version: 9.3.0
    gcc10:
      base: gcc
      version: 10.1.0
  mpi_libraries:
    intel:
      base: intel-mpi
      version: 2018.4.274
  applications:
    wrfv4:
      external_spack_env: {env_path}
      wrf:
        base: wrf
        version: 4.2
        variants: 'build_type=dm+sm compile_type=em_real nesting=basic ~chem ~pnetcdf'
        compiler: gcc8
        mpi: intel
"""

    workspace_name = 'test_dryrun_copies_external_env'
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws.dry_run = True
    ws._re_read()

    ws.run_pipeline('setup')

    env_file = os.path.join(ws.software_dir, 'wrfv4.CONUS_12km', 'spack.yaml')
    lock_file = os.path.join(ws.software_dir, 'wrfv4.CONUS_12km', 'spack.lock')

    assert os.path.exists(env_file)

    with open(env_file, 'r') as f:
        assert 'zlib' in f.read()

    assert os.path.exists(lock_file)

    with open(lock_file, 'r') as f:
        assert 'zlib' in f.read()


def test_dryrun_series_contains_package_paths(mutable_config,
                                              mutable_mock_workspace_path,
                                              mock_applications):
    test_config = r"""
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
    processes_per_node: '10'
    n_ranks: '{processes_per_node}*{n_nodes}'
    n_threads: '1'
  applications:
    zlib:
      workloads:
        ensure_installed:
          experiments:
            test_{test_id}:
              variables:
                n_nodes: '1'
                test_id: [1, 2]
spack:
  concretized: true
  compilers: {}
  mpi_libraries: {}
  applications:
    zlib:
      zlib:
        base: zlib
"""

    workspace_name = 'test_dryrun_series_contains_package_paths'
    ws = ramble.workspace.create(workspace_name)
    ws.write()

    config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws.dry_run = True
    ws._re_read()

    ws.run_pipeline('setup')

    for test in ['test_1', 'test_2']:
        script = os.path.join(ws.experiment_dir, 'zlib', 'ensure_installed',
                              test, 'execute_experiment')

        assert os.path.exists(script)
        with open(script, 'r') as f:
            assert r'{zlib}' not in f.read()


def test_dryrun_chained_experiments(mutable_config,
                                    mutable_mock_workspace_path):
    test_config = r"""
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
  compilers:
    gcc:
      base: gcc
      version: 9.3.0
      target: x86_64
  mpi_libraries:
    impi2018:
      base: intel-mpi
      version: 2018.4.274
  applications:
    intel-mpi-benchmarks:
      intel-mpi-benchmarks:
        base: intel-mpi-benchmarks
        compiler: gcc
        mpi: impi2018
    gromacs:
      gromacs:
        base: gromacs
        compiler: gcc
        mpi: impi2018
"""

    mock_output_data = """
  14 100 1.5 1.0 2.0
"""

    workspace_name = 'test_dryrun_chained_experiments'
    ws = ramble.workspace.create(workspace_name)
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


@pytest.mark.long
def test_known_applications(application):
    info_cmd = RambleCommand('info')

    workload_regex = re.compile(r'Workload: (?P<wl_name>.*)')
    ws_name = f'test_all_apps_{application}'

    base_config = """ramble:
  mpi:
    command: 'mpirun'
    args:
    - '-n'
    - '{n_ranks}'
  batch:
    submit: '{execute_experiment}'
  applications:\n"""

    app_info = info_cmd(application)
    workloads = []
    for line in app_info.split('\n'):
        match = workload_regex.search(line)
        if match:
            workloads.append(match.group('wl_name').replace(' ', ''))

    with ramble.workspace.create(ws_name) as ws:
        ws.write()
        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(base_config)
            f.write(f'    {application}:\n')
            f.write('      workloads:\n')
            for workload in workloads:
                f.write(f"""        {workload.strip()}:
          experiments:
            test_experiment:
              variables:
                n_ranks: '1'
                n_nodes: '1'
                processes_per_node: '1'\n""")
            f.write("""spack:
  concretized: false
  compilers: {}
  mpi_libraries: {}
  applications: {}\n""")

        ws._re_read()
        ws.concretize()
        ws._re_read()
        ws.dry_run = True
        ws.run_pipeline('setup')
        ws.run_pipeline('analyze')
        ws.archive(create_tar=True)
