# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the Application class"""

import pytest

import ramble.workspace

pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path',
                                     'mutable_mock_apps_repo')


@pytest.mark.parametrize('app', [
    'basic', 'basic-inherited', 'input-test', 'interleved-env-vars',
    'register-builtin'
])
def test_app_features(mutable_mock_apps_repo, app):
    app_inst = mutable_mock_apps_repo.get(app)
    assert hasattr(app_inst, 'workloads')
    assert hasattr(app_inst, 'executables')
    assert hasattr(app_inst, 'figures_of_merit')
    assert hasattr(app_inst, 'inputs')
    assert hasattr(app_inst, 'compilers')
    assert hasattr(app_inst, 'software_specs')
    assert hasattr(app_inst, 'required_packages')
    assert hasattr(app_inst, 'workload_variables')
    assert hasattr(app_inst, 'environment_variables')
    assert hasattr(app_inst, 'builtins')


def test_basic_app(mutable_mock_apps_repo):
    basic_inst = mutable_mock_apps_repo.get('basic')
    assert 'foo' in basic_inst.executables
    assert basic_inst.executables['foo'].template == ['bar']
    assert not basic_inst.executables['foo'].mpi
    assert 'bar' in basic_inst.executables
    assert basic_inst.executables['bar'].template == ['baz']
    assert basic_inst.executables['bar'].mpi

    assert 'test_wl' in basic_inst.workloads
    assert basic_inst.workloads['test_wl']['executables'] == ['foo']
    assert basic_inst.workloads['test_wl']['inputs'] == ['input']

    exec_graph = basic_inst._get_executable_graph('test_wl')
    assert exec_graph.get_node('foo') is not None
    assert exec_graph.get_node('builtin::env_vars') is not None

    assert 'test_wl2' in basic_inst.workloads
    assert basic_inst.workloads['test_wl2']['executables'] == ['bar']
    assert basic_inst.workloads['test_wl2']['inputs'] == ['input']

    exec_graph = basic_inst._get_executable_graph('test_wl2')
    assert exec_graph.get_node('bar') is not None
    assert exec_graph.get_node('builtin::env_vars') is not None

    assert 'test_fom' in basic_inst.figures_of_merit
    fom_conf = basic_inst.figures_of_merit['test_fom']
    assert fom_conf['log_file'] == '{log_file}'
    assert fom_conf['regex'] == \
        r'(?P<test>[0-9]+\.[0-9]+).*seconds.*'  # noqa: W605
    assert fom_conf['group_name'] == 'test'
    assert fom_conf['units'] == 's'

    assert 'input' in basic_inst.inputs
    assert basic_inst.inputs['input']['url'] == \
        'file:///tmp/test_file.log'
    assert basic_inst.inputs['input']['description'] == \
        'Not a file'

    assert 'test_wl' in basic_inst.workload_variables
    assert 'my_var' in basic_inst.workload_variables['test_wl']
    assert basic_inst.workload_variables['test_wl']['my_var']['default'] == \
        '1.0'

    assert basic_inst.workload_variables['test_wl']['my_var']['description'] \
        == 'Example var'


@pytest.mark.parametrize('app_name', ['basic', 'zlib'])
def test_application_copy_is_deep(mutable_mock_apps_repo, app_name):
    src_inst = mutable_mock_apps_repo.get(app_name)

    defined_variables = {
        'test_var1': 'test_val1',
        'test_var2': 'test_val2'
    }

    defined_env_vars = {
        'set': {
            'SET_ENV_VAR': 'TEST'
        },
        'unset': [
            'UNSET_ENV_VAR'
        ],
        'append': [
            {
                'var-separator': ',',
                'vars': {
                    'APPEND_VAR': 'APPEND_TEST'
                }
            }
        ],
        'prepend': [
            {
                'var-separator': ',',
                'vars': {
                    'PREPEND_VAR': 'PREPEND_TEST'
                }
            }
        ]
    }

    defined_internals = {
        'custom_executables': {
            'test_exec': {
                'templates': [
                    'test_exec'
                ],
                'use_mpi': False,
                'redirect': '{log_file}'
            }
        }
    }

    src_inst.set_variables(defined_variables, None)
    src_inst.set_env_variable_sets(defined_env_vars)
    src_inst.set_internals(defined_internals)

    copy_inst = src_inst.copy()

    # Test variables
    for var, val in src_inst.variables.items():
        assert var in copy_inst.variables.keys()
        assert copy_inst.variables[var] == val

    # Test env-vars
    for var_set in src_inst._env_variable_sets.keys():
        assert var_set in copy_inst._env_variable_sets.keys()
        # Test set sets
        if var_set == 'set':
            for var, val in src_inst._env_variable_sets[var_set].items():
                assert var in copy_inst._env_variable_sets[var_set]
                assert copy_inst._env_variable_sets[var_set][var] == val
        elif var_set == 'append' or var_set == 'prepend':
            for idx, set_group in enumerate(src_inst._env_variable_sets[var_set]):
                if 'var-separator' in set_group:
                    assert 'var-separator' in copy_inst._env_variable_sets[var_set][idx]
                    assert copy_inst._env_variable_sets[var_set][idx]['var-separator'] == \
                           set_group['var-separator']
                if 'vars' in set_group:
                    assert 'vars' in copy_inst._env_variable_sets[var_set][idx]
                    for var, val in set_group['vars'].items():
                        assert var in copy_inst._env_variable_sets[var_set][idx]['vars']
                        assert copy_inst._env_variable_sets[var_set][idx]['vars'][var] == val
        elif var_set == 'unset':
            for var in src_inst._env_variable_sets[var_set]:
                assert var in copy_inst._env_variable_sets[var_set]

    # Test internals:
    for internal, conf in src_inst.internals.items():
        assert internal in copy_inst.internals
        if internal == 'custom_executables':
            for exec_name, exec_conf in conf.items():
                assert exec_name in copy_inst.internals[internal]
                for option, value in exec_conf.items():
                    assert option in copy_inst.internals[internal][exec_name]
                    assert copy_inst.internals[internal][exec_name][option] == value


@pytest.mark.parametrize('app', [
    'basic', 'basic-inherited', 'input-test', 'interleved-env-vars',
    'register-builtin'
])
def test_required_builtins(mutable_mock_apps_repo, app):
    app_inst = mutable_mock_apps_repo.get(app)

    required_builtins = []
    for builtin, conf in app_inst.builtins.items():
        if conf[app_inst._builtin_required_key]:
            required_builtins.append(builtin)

    for workload, wl_conf in app_inst.workloads.items():
        exec_graph = app_inst._get_executable_graph(workload)
        for builtin in required_builtins:
            assert exec_graph.get_node(builtin) is not None


def test_register_builtin_app(mutable_mock_apps_repo):
    app_inst = mutable_mock_apps_repo.get('register-builtin')

    required_builtins = []
    excluded_builtins = []
    for builtin, conf in app_inst.builtins.items():
        if conf[app_inst._builtin_required_key]:
            required_builtins.append(builtin)
        else:
            excluded_builtins.append(builtin)

    for workload, wl_conf in app_inst.workloads.items():
        exec_graph = app_inst._get_executable_graph(workload)

        for builtin in required_builtins:
            assert exec_graph.get_node(builtin) is not None
        for builtin in excluded_builtins:
            assert exec_graph.get_node(builtin) is None


@pytest.mark.parametrize('app', [
    'basic', 'basic-inherited', 'input-test', 'interleved-env-vars',
    'register-builtin'
])
def test_short_print(mutable_mock_apps_repo, app):
    app_inst = mutable_mock_apps_repo.get(app)
    app_inst._verbosity = 'short'

    str_val = str(app_inst)

    assert str_val == app


def basic_exp_dict():
    """To set expander consistently with test_wl2 of builtin.mock/applications/basic"""
    return {
        'application_name': 'bar',
        'inputs': {'test_wl': 'input', 'test_wl2': 'input'},
        'workload_name': 'test_wl2',
        'experiment_name': 'baz',
        'application_input_dir': '/workspace/inputs/bar',
        'workload_input_dir': '/workspace/inputs/bar/test_wl2',
        'application_run_dir': '/workspace/experiments/bar',
        'workload_run_dir': '/workspace/experiments/bar/test_wl2',
        'experiment_run_dir': '/workspace/experiments/bar/test_wl2/baz',
        'env_name': 'spack_bar.test_wl2',
        'n_ranks': '4',
        'processes_per_node': '2',
        'n_nodes': '2',
        'var1': '{var2}',
        'var2': '{var3}',
        'var3': '3',
        'mpi_command': 'mpirun -n {n_ranks}',
        'batch_command': 'sbatch -p {partition} {execute_experiment}'
    }


def test_get_executable_graph_initial(mutable_mock_apps_repo):
    """_get_executable_graph, test1, workload executables"""

    executable_application_instance = mutable_mock_apps_repo.get('basic')

    expansion_vars = basic_exp_dict()

    # Set up the instance to test just the initial part of the function
    executable_application_instance.expander = ramble.expander.Expander(expansion_vars, None)
    executable_application_instance.workloads = {'test_wl': {'executables': ['foo'],
                                                             'inputs': ['input']},
                                                 'test_wl2': {'executables': ['bar'],
                                                              'inputs': ['input']}}
    executable_application_instance.internals = {}

    executable_graph = executable_application_instance._get_executable_graph('test_wl2')
    bar_node = executable_graph.get_node('bar')

    assert bar_node is not None


def test_get_executable_graph_yaml_defined(mutable_mock_apps_repo):
    """_get_executable_graph, test2, yaml-defined order"""

    executable_application_instance = mutable_mock_apps_repo.get('basic')

    expansion_vars = basic_exp_dict()

    # Set up the instance to pass the initial part of the function
    executable_application_instance.expander = ramble.expander.Expander(expansion_vars, None)
    executable_application_instance.workloads = {'test_wl': {'executables': ['foo'],
                                                             'inputs': ['input']},
                                                 'test_wl2': {'executables': ['bar'],
                                                              'inputs': ['input']}}

    # Insert namespace.executables into the instance's internals to pass the
    # second part of the function
    defined_internals = {
        'custom_executables': {
            'test_exec': {
                'template': [
                    'test_exec'
                ],
                'use_mpi': False,
                'redirect': '{log_file}'
            }
        },
        'executables': [
            'bar',
            'test_exec'
        ]
    }
    executable_application_instance.set_internals(defined_internals)

    executable_graph = executable_application_instance._get_executable_graph('test_wl')

    test_node = executable_graph.get_node('test_exec')

    assert test_node is not None


def test_get_executable_graph_custom_executables(mutable_mock_apps_repo):
    """_get_executable_graph, test3, custom executables"""

    executable_application_instance = mutable_mock_apps_repo.get('basic')

    expansion_vars = basic_exp_dict()

    # Set up the instance to pass the initial part of the function
    executable_application_instance.expander = ramble.expander.Expander(expansion_vars, None)
    executable_application_instance.workloads = {'test_wl': {'executables': ['foo'],
                                                             'inputs': ['input']},
                                                 'test_wl2': {'executables': ['bar'],
                                                              'inputs': ['input']}}

    # Insert namespace.executables into the instance's internals to pass the
    # second part of the function
    defined_internals = {
        'custom_executables': {
            'test_exec2': {
                'template': [
                    'test_exec2'
                ],
                'use_mpi': False,
                'redirect': '{log_file}',
            }
        },
        'executables': [
            'test_exec2',
            'bar'
        ]
    }
    executable_application_instance.set_internals(defined_internals)

    executable_graph = executable_application_instance._get_executable_graph('test_wl2')
    test_node = executable_graph.get_node('test_exec2')

    assert test_node is not None


def test_set_input_path(mutable_mock_apps_repo):
    """_set_input_path"""

    executable_application_instance = mutable_mock_apps_repo.get('basic')

    expansion_vars = basic_exp_dict()

    # Set up the instance to pass the initial part of the function
    executable_application_instance.expander = ramble.expander.Expander(expansion_vars, None)

    executable_application_instance.internals = {}

    executable_application_instance.variables = {}

    executable_application_instance._set_input_path()

    default_answer = '/workspace/inputs/bar/test_wl2/input'

    assert executable_application_instance.variables['input'] == default_answer


def test_set_input_path_multi_input(mutable_mock_apps_repo):
    """Tests set_input_path with multiple inputs in a given workload"""

    executable_application_instance = mutable_mock_apps_repo.get('input-test')

    expansion_vars = basic_exp_dict()
    del expansion_vars['inputs']
    expansion_vars['application_name'] = 'input-test'
    expansion_vars['workload_name'] = 'test'

    # Set up the instance to pass the initial part of the function
    executable_application_instance.expander = ramble.expander.Expander(expansion_vars, None)

    executable_application_instance.internals = {}

    executable_application_instance.variables = {}

    executable_application_instance._set_input_path()

    input1_path = '/workspace/inputs/bar/test_wl2/test-input1'
    input2_path = '/workspace/inputs/bar/test_wl2/test-input2'
    input3_path = '/workspace/inputs/bar/test_wl2/input3.txt'

    assert executable_application_instance.variables['test-input1'] == input1_path
    assert executable_application_instance.variables['test-input2'] == input2_path
    assert executable_application_instance.variables['test-input3'] == input3_path


def test_set_default_experiment_variables(mutable_mock_apps_repo):
    """_set_default_experiment_variables"""

    executable_application_instance = mutable_mock_apps_repo.get('basic')

    expansion_vars = basic_exp_dict()

    # Set up the instance to pass the initial part of the function
    executable_application_instance.expander = ramble.expander.Expander(expansion_vars, None)

    executable_application_instance.workloads = {'test_wl': {'executables': ['foo'],
                                                             'inputs': ['input']},
                                                 'test_wl2': {'executables': ['bar'],
                                                              'inputs': ['input']}}

    executable_application_instance.internals = {}

    executable_application_instance.inputs = {'input': {'target_dir': '.'}}
    executable_application_instance.variables = {}

    executable_application_instance.workload_variables = {'test_wl2': {'n_ranks':
                                                                       {'default': '1'}}}

    executable_application_instance._set_default_experiment_variables()

    assert executable_application_instance.variables['n_ranks'] == '1'


def test_define_commands(mutable_mock_apps_repo):
    """ test _define_commands """

    executable_application_instance = mutable_mock_apps_repo.get('basic')

    expansion_vars = basic_exp_dict()

    # Set up the instance to pass the initial part of the function
    executable_application_instance.expander = ramble.expander.Expander(expansion_vars, None)

    executable_application_instance.workloads = {'test_wl': {'executables': ['foo'],
                                                             'inputs': ['input']},
                                                 'test_wl2': {'executables': ['bar'],
                                                              'inputs': ['input']}}

    executable_application_instance.internals = {}

    executable_application_instance.inputs = {'input': {'target_dir': '.'}}
    executable_application_instance.variables = {}

    exec_graph = executable_application_instance._get_executable_graph('test_wl2')

    executable_application_instance.workload_variables = {'test_wl2': {'n_ranks':
                                                                       {'default': '1'}}}

    executable_application_instance.set_formatted_executables(
        {'command': {'join_separator': '\n'}}
    )
    executable_application_instance._set_default_experiment_variables()

    executable_application_instance.chain_prepend = []
    executable_application_instance._define_commands(exec_graph)
    executable_application_instance._define_formatted_executables()
    assert 'mpirun' in executable_application_instance.variables['command']


def test_derive_variables_for_template_path(mutable_mock_apps_repo):
    """_set_default_variables_for_template_path"""
    test_config = """
ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
    batch_submit: 'batch_submit {execute_experiment}'
    processes_per_node: '5'
    n_ranks: '{processes_per_node}*{n_nodes}'
  applications:
    basic:
      workloads:
        test_wl:
          experiments:
            test_experiment:
              template: true
              variables:
                n_nodes: '2'
        test_wl2:
          experiments:
            test_experiment:
              variables:
                n_nodes: '2'

  spack:
    concretized: true
    packages: {}
    environments: {}
"""
    import os.path
    workspace_name = 'test_derive_variables_for_template_path'
    ws1 = ramble.workspace.create(workspace_name)
    ws1.write()

    config_path = os.path.join(ws1.config_dir, ramble.workspace.config_file_name)

    with open(config_path, 'w+') as f:
        f.write(test_config)

    ws1._re_read()

    executable_application_instance = mutable_mock_apps_repo.get('basic')

    expansion_vars = basic_exp_dict()

    # Set up the instance to pass the initial part of the function
    executable_application_instance.expander = ramble.expander.Expander(expansion_vars, None)

    executable_application_instance.workloads = {'test_wl': {'executables': ['foo'],
                                                             'inputs': ['input']},
                                                 'test_wl2': {'executables': ['bar'],
                                                              'inputs': ['input'],
                                                              'template': ['input'],
                                                              },
                                                 }

    executable_application_instance.internals = {}

    executable_application_instance.inputs = {'input': {'target_dir': '.'}}
    executable_application_instance.variables = {}

    exec_graph = executable_application_instance._get_executable_graph('test_wl2')

    executable_application_instance.workload_variables = {'test_wl2': {'n_ranks':
                                                                       {'default': '1'}}}

    executable_application_instance._set_default_experiment_variables()

    executable_application_instance.chain_prepend = []
    executable_application_instance._define_commands(exec_graph)
    executable_application_instance._define_formatted_executables()

    test_answer = "/workspace/experiments/bar/test_wl2/baz/execute_experiment"
    executable_application_instance._derive_variables_for_template_path(ws1)
    assert executable_application_instance.variables['execute_experiment'] == test_answer
