# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from enum import Enum

import spack.util.spack_yaml as syaml


def check_software_env(base_dir, tests):
    """Validate software environments

    Input arguments:
    - base_dir: the software directory tests should validate against
    - tests: list of tuples. Each tuple should be (env_name, expected_contents).

    This method will validate that expected_contents exists in the spack.yaml
    file in the corresponding env_name.
    """
    for test_env, test_content in tests:
        env_dir = os.path.join(base_dir, test_env)
        assert os.path.exists(env_dir)

        spack_file = os.path.join(env_dir, 'spack.yaml')
        assert os.path.isfile(spack_file)

        with open(spack_file, 'r') as f:
            assert test_content in f.read()


def check_execute_script(script_path, tests):
    assert os.path.isfile(script_path)
    with open(script_path, 'r') as f:
        data = f.read()
        for test in tests:
            assert test in data


SCOPES = Enum('SCOPES', ['workspace', 'application', 'workload', 'experiment'])


def dry_run_config(modifier_injections, config_path):
    """Creates a new configuration with modifiers injected

    Input argument modifier_injections is a list of tuples. Each tuple has two
    values, and takes the form:

    (scope, modifier_dict)

    scope is the scope the modifier should be injected into
    modifier_dict is a dict representing the new modifier

    config_path is the path to the config file that should be written
    """
    ramble_dict = syaml.syaml_dict()
    ramble_dict['ramble'] = syaml.syaml_dict()
    test_dict = ramble_dict['ramble']

    test_dict['variables'] = syaml.syaml_dict()
    test_dict['applications'] = syaml.syaml_dict()
    test_dict['applications']['gromacs'] = syaml.syaml_dict()
    test_dict['spack'] = syaml.syaml_dict()

    spack_dict = test_dict['spack']
    spack_dict['concretized'] = False
    spack_dict['packages'] = syaml.syaml_dict()
    spack_dict['environments'] = syaml.syaml_dict()

    ws_var_dict = test_dict['variables']
    ws_var_dict['mpi_command'] = 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    ws_var_dict['batch_submit'] = 'batch_submit {execute_experiment}'
    ws_var_dict['processes_per_node'] = '16'
    ws_var_dict['n_ranks'] = '{processes_per_node}*{n_nodes}'
    ws_var_dict['n_threads'] = '1'

    app_dict = test_dict['applications']['gromacs']
    app_dict['workloads'] = syaml.syaml_dict()
    app_dict['workloads']['water_bare'] = syaml.syaml_dict()

    workload_dict = app_dict['workloads']['water_bare']
    workload_dict['experiments'] = syaml.syaml_dict()
    workload_dict['experiments']['test_exp'] = syaml.syaml_dict()

    exp_dict = workload_dict['experiments']['test_exp']
    exp_dict['variables'] = syaml.syaml_dict()
    exp_dict['variables']['n_nodes'] = '1'

    for scope, modifier_dict in modifier_injections:
        if scope == SCOPES.workspace:
            dict_to_mod = test_dict
        elif scope == SCOPES.application:
            dict_to_mod = app_dict
        elif scope == SCOPES.workload:
            dict_to_mod = workload_dict
        elif scope == SCOPES.experiment:
            dict_to_mod = exp_dict

        if 'modifiers' not in dict_to_mod:
            dict_to_mod['modifiers'] = syaml.syaml_list()

        dict_to_mod['modifiers'].append(modifier_dict.copy())

    with open(config_path, 'w+') as f:
        syaml.dump(ramble_dict, stream=f)


def named_modifier(name):
    modifier_def = syaml.syaml_dict()
    modifier_def['name'] = name
    return modifier_def


def intel_aps_modifier():
    modifier_def = named_modifier('intel-aps')
    modifier_def['mode'] = 'mpi'
    modifier_def['on_executable'] = syaml.syaml_list()
    modifier_def['on_executable'].append('*')
    return modifier_def


def intel_aps_answer():
    expected_software = [
        ('gromacs.water_bare', 'intel-oneapi-vtune'),
        ('gromacs.water_bare', 'gromacs')
    ]
    expected_strs = [
        'aps -c mpi',
        'aps-report'
    ]
    return expected_software, expected_strs


def lscpu_modifier():
    modifier_def = named_modifier('lscpu')
    modifier_def['mode'] = 'standard'
    modifier_def['on_executable'] = syaml.syaml_list()
    modifier_def['on_executable'].append('*')
    return modifier_def


def lscpu_answer():
    expected_software = [
        ('gromacs.water_bare', 'gromacs'),
    ]
    expected_strs = [
        'lscpu',
    ]
    return expected_software, expected_strs


def env_var_append_paths_modifier():
    modifier_def = named_modifier('append-env-var-mod-paths')
    modifier_def['mode'] = 'test'
    modifier_def['on_executable'] = syaml.syaml_list()
    modifier_def['on_executable'].append('*')
    return modifier_def


def env_var_append_paths_modifier_answer():
    expected_software = [
        ('gromacs.water_bare', 'gromacs'),
    ]
    expected_strs = [
        'export test_var="${test_var}:test_val"'
    ]
    return expected_software, expected_strs


def env_var_append_vars_modifier():
    modifier_def = named_modifier('append-env-var-mod-vars')
    modifier_def['mode'] = 'test'
    modifier_def['on_executable'] = syaml.syaml_list()
    modifier_def['on_executable'].append('*')
    return modifier_def


def env_var_append_vars_modifier_answer():
    expected_software = [
        ('gromacs.water_bare', 'gromacs'),
    ]
    expected_strs = [
        'export test_var="${test_var},test_val"',
    ]
    return expected_software, expected_strs


def env_var_prepend_paths_modifier():
    modifier_def = named_modifier('prepend-env-var-mod-paths')
    modifier_def['mode'] = 'test'
    modifier_def['on_executable'] = syaml.syaml_list()
    modifier_def['on_executable'].append('*')
    return modifier_def


def env_var_prepend_paths_modifier_answer():
    expected_software = [
        ('gromacs.water_bare', 'gromacs'),
    ]
    expected_strs = [
        'export test_var="test_val:${test_var}"',
    ]
    return expected_software, expected_strs


def env_var_set_modifier():
    modifier_def = named_modifier('set-env-var-mod')
    modifier_def['mode'] = 'test'
    modifier_def['on_executable'] = syaml.syaml_list()
    modifier_def['on_executable'].append('*')
    return modifier_def


def env_var_set_modifier_answer():
    expected_software = [
        ('gromacs.water_bare', 'gromacs'),
    ]
    expected_strs = [
        'export test_var=test_val',
    ]
    return expected_software, expected_strs


def env_var_unset_modifier():
    modifier_def = named_modifier('unset-env-var-mod')
    modifier_def['mode'] = 'test'
    modifier_def['on_executable'] = syaml.syaml_list()
    modifier_def['on_executable'].append('*')
    return modifier_def


def env_var_unset_modifier_answer():
    expected_software = [
        ('gromacs.water_bare', 'gromacs'),
    ]
    expected_strs = [
        'unset test_var',
    ]
    return expected_software, expected_strs
