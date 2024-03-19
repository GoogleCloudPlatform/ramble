# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import pytest

import ramble.workspace
import ramble.experiment_set
import ramble.context
import ramble.renderer
from ramble.application import ChainCycleDetectedError, InvalidChainError
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path',
                                     'mutable_mock_apps_repo',
                                     )

workspace  = RambleCommand('workspace')


def test_single_experiment_in_set(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': '2',
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()


def test_vector_experiment_in_set(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()


def test_vector_length_mismatch_errors(request, mutable_mock_workspace_path, capsys):
    ws_name = request.node.name
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'processes_per_node': ['2', '4', '6']
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{processes_per_node}'
        experiment_context.variables = {
            'n_nodes': ['2', '4']
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        with pytest.raises(SystemExit):
            exp_set.set_experiment_context(experiment_context)

            captured = capsys.readouterr()

            assert 'Length mismatch in vector variables in experiment series1_{n_ranks}' \
                in captured
            assert 'Variable wl_var2 has length 1' in captured
            assert 'Variable n_nodes has length 2' in captured


def test_nonunique_vector_errors(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{processes_per_node}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)

        with pytest.raises(SystemExit):
            exp_set.set_experiment_context(experiment_context)

            captured = capsys.readouterr()
            assert "is not unique." in captured


def test_zipped_vector_experiments(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{processes_per_node}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_16_4' in exp_set.experiments.keys()


def test_matrix_experiments(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }
        experiment_context.matrices = [
            ['n_nodes']
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' in exp_set.experiments.keys()


def test_matrix_multiplication_experiments(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['1', '4', '6']
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }
        experiment_context.matrices = [
            ['n_nodes', 'processes_per_node']
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_12' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_16' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_24' in exp_set.experiments.keys()


def test_matrix_vector_experiments(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }
        experiment_context.matrices = [
            ['n_nodes']
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_12' in exp_set.experiments.keys()


def test_multi_matrix_experiments(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{processes_per_node}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }
        experiment_context.matrices = [
            ['n_nodes'],
            ['processes_per_node']
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_12_4' in exp_set.experiments.keys()


def test_full_experiments_from_dict(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_dict = {
            'variables': {
                'n_ranks': '{processes_per_node}*{n_nodes}',
                'mpi_command': '',
                'batch_submit': ''
            }
        }

        wl_dict = {
            'variables': {
                'partition': ['p1', 'p2'],
                'processes_per_node': ['2', '4']
            }
        }

        exp_dict = {
            'variables': {
                'n_nodes': ['2', '3'],
                'ids': ['1', '2', '3', '4']
            },
            'zips': {
                'part_conf': [
                    'partition',
                    'processes_per_node'
                ]
            },
            'matrices': [
                {
                    'mat_name': [
                        'part_conf',
                        'n_nodes'
                    ]
                }
            ],
            'matrix': [
                'ids'
            ]
        }

        appContext = ramble.context.create_context_from_dict('basic', app_dict)
        wlContext = ramble.context.create_context_from_dict('test_wl', wl_dict)
        expContext = ramble.context.create_context_from_dict(
            'test_{n_ranks}_{processes_per_node}_{ids}',
            exp_dict
        )

        exp_set.set_application_context(appContext)
        exp_set.set_workload_context(wlContext)
        exp_set.set_experiment_context(expContext)

        assert 'basic.test_wl.test_4_2_1' in exp_set.experiments.keys()
        assert 'basic.test_wl.test_6_2_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.test_8_4_3' in exp_set.experiments.keys()
        assert 'basic.test_wl.test_12_4_4' in exp_set.experiments.keys()

        assert exp_set._context[exp_set._contexts.workspace].context_name is not None


def test_matrix_undefined_var_errors(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{processes_per_node}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }
        experiment_context.matrices = [
            ['n_nodes'],
            ['foo']
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)

        with pytest.raises(SystemExit):
            exp_set.set_experiment_context(experiment_context)

            captured = capsys.readouterr()
            assert "variable foo has not been defined yet." in captured


def test_experiment_names_match(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{processes_per_node}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }
        experiment_context.matrices = [
            ['n_nodes'],
            ['processes_per_node']
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_12_4' in exp_set.experiments.keys()

        for exp, app, _ in exp_set.all_experiments():
            assert exp == app.expander.expand_var('{experiment_namespace}')


def test_cross_experiment_variable_references(request, mutable_mock_workspace_path):
    ws_name = request.node.name
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment1_context = ramble.context.Context()
        experiment1_context.context_name = 'series1_{n_ranks}'
        experiment1_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': '2',
            'test_var': 'success'
        }
        experiment1_context.internals = {
            'custom_executables': {
                'echo_test': {'template': 'echo "{test_var}"'},
            },
            'executable_injection': [
                {'name': 'echo_test', 'order': 'after'}
            ]
        }

        experiment2_context = ramble.context.Context()
        experiment2_context.context_name = 'series2_{n_ranks}'
        experiment2_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': '2',
            'test_var': 'test_var in basic.test_wl.series1_4'
        }

        experiment2_context.internals = {
            'custom_executables': {
                'echo_test': {'template': 'echo "{test_var}"'},
            },
            'executable_injection': [
                {'name': 'echo_test', 'order': 'after'}
            ]
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment1_context)
        exp_set.set_experiment_context(experiment2_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series2_4' in exp_set.experiments.keys()

        exp2_app = exp_set.experiments['basic.test_wl.series2_4']
        assert exp2_app.expander.expand_var('{test_var}') == 'success'


def test_cross_experiment_missing_experiment_errors(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment1_context = ramble.context.Context()
        experiment1_context.context_name = 'series1_{n_ranks}'
        experiment1_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': '2',
            'test_var': 'processes_per_node in basic.test_wl.does_not_exist'
        }

        experiment1_context.internals = {
            'custom_executables': {
                'echo_test': {'template': 'echo "{test_var}"'},
            },
            'executable_injection': [
                {'name': 'echo_test', 'order': 'after'}
            ]
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)

        with pytest.raises(ramble.expander.RambleSyntaxError) as e:
            exp_set.set_experiment_context(experiment1_context)

            expected = ('basic.test_wl_does_not_exist does not exist in '
                        f'"{experiment1_context.variables["test_var"]}"')
            assert e.error == expected


def test_n_ranks_correct_defaults(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }
        experiment_context.matrices = [
            ['n_nodes']
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' in exp_set.experiments.keys()


def test_n_nodes_correct_defaults(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': ['4', '6'],
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{n_nodes}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
        }
        experiment_context.matrices = [
            ['n_ranks']
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6_3' in exp_set.experiments.keys()


def test_processes_per_node_correct_defaults(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)
        # Remove workspace vars, which default to a `processes_per_node = -1` definition.
        exp_set._context[exp_set._contexts.workspace].variables = {}

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': ['4', '6'],
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{processes_per_node}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6_2' in exp_set.experiments.keys()


@pytest.mark.parametrize('var', [
    'env_path'
])
def test_reserved_keywords_error_in_application(mutable_mock_workspace_path, var, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': ['4', '6'],
            var: 'should_fail',
            'mpi_command': '',
            'batch_submit': ''
        }

        with pytest.raises(ramble.experiment_set.RambleVariableDefinitionError):
            exp_set.set_application_context(application_context)
            captured = capsys.readouterr()
            assert "In application basic" in captured
            assert f"{var}" in captured
            assert "is reserved by ramble" in captured


@pytest.mark.parametrize('var', [
    'env_path'
])
def test_reserved_keywords_error_in_workload(mutable_mock_workspace_path, var, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': ['4', '6'],
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            var: 'should_fail'
        }

        exp_set.set_application_context(application_context)
        with pytest.raises(ramble.experiment_set.RambleVariableDefinitionError):
            exp_set.set_workload_context(workload_context)
            captured = capsys.readouterr()
            assert "In workload basic.test_wl" in captured
            assert f"{var}" in captured
            assert "is reserved by ramble" in captured


@pytest.mark.parametrize('var', [
    'env_path'
])
def test_reserved_keywords_error_in_experiment(mutable_mock_workspace_path, var, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)
        # Remove workspace vars, which default to a `processes_per_node = -1` definition.
        exp_set._context[exp_set._contexts.base].variables = {}

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': ['4', '6'],
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{processes_per_node}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3'],
            var: 'should_fail'
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        with pytest.raises(ramble.experiment_set.RambleVariableDefinitionError):
            exp_set.set_experiment_context(experiment_context)
            captured = capsys.readouterr()
            assert "In experiment basic.test_wl.series1_{n_ranks}_{processes_per_node}" in captured
            assert f"{var}" in captured
            assert "is reserved by ramble" in captured


@pytest.mark.parametrize('var', [
    'batch_submit', 'mpi_command'
])
def test_missing_required_keyword_errors(mutable_mock_workspace_path, var, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)
        for context in exp_set._contexts:
            if exp_set._context[context].variables and var in exp_set._context[context].variables:
                del exp_set._context[context].variables[var]

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': ['4', '6'],
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }
        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{processes_per_node}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3'],
            'batch_submit': '',
            'mpi_command': ''
        }

        if var in experiment_context.variables.keys():
            del experiment_context.variables[var]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        with pytest.raises(ramble.experiment_set.RambleVariableDefinitionError):
            exp_set.set_experiment_context(experiment_context)
            captured = capsys.readouterr()
            assert f'Required key "{var}" is not defined' in captured.err
            assert 'One or more required keys are not defined within an experiment.' \
                in captured.err
            assert "In experiment basic.test_wl.series1_{n_ranks}_{processes_per_node}" \
                in captured.err


def test_chained_experiments_populate_new_experiments(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'processes_per_node': '1',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }

        experiment1_context = ramble.context.Context()
        experiment1_context.context_name = 'test1'
        experiment1_context.variables = {
            'n_ranks': '2'
        }

        experiment2_context = ramble.context.Context()
        experiment2_context.context_name = 'series2_{n_ranks}'
        experiment2_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_ranks': ['4', '6']
        }
        experiment2_context.chained_experiments = [
            {
                'name': 'basic.test_wl.test1',
                'order': 'before_root',
                'command': '{execute_experiment}',
                'variables': {}
            },
            {
                'name': 'basic.test_wl.test1',
                'order': 'after_root',
                'command': '{execute_experiment}',
                'variables': {}
            }
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment1_context)
        exp_set.set_experiment_context(experiment2_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series2_4' in \
            exp_set.experiments
        assert 'basic.test_wl.series2_4.chain.0.basic.test_wl.test1' in \
            exp_set.chained_experiments
        assert 'basic.test_wl.series2_4.chain.1.basic.test_wl.test1' in \
            exp_set.chained_experiments
        assert 'basic.test_wl.series2_6' in \
            exp_set.experiments
        assert 'basic.test_wl.series2_6.chain.0.basic.test_wl.test1' in \
            exp_set.chained_experiments
        assert 'basic.test_wl.series2_6.chain.1.basic.test_wl.test1' in \
            exp_set.chained_experiments
        assert 'basic.test_wl.test1' in exp_set.experiments


def test_chained_experiment_has_correct_directory(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'processes_per_node': '1',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }

        experiment1_context = ramble.context.Context()
        experiment1_context.context_name = 'test1'
        experiment1_context.variables = {
            'n_ranks': '2'
        }

        experiment2_context = ramble.context.Context()
        experiment2_context.context_name = 'series2_{n_ranks}'
        experiment2_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_ranks': '4'
        }
        experiment2_context.chained_experiments = [
            {
                'name': 'basic.test_wl.test1',
                'order': 'before_root',
                'command': '{execute_experiment}',
                'variables': {}
            },
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment1_context)
        exp_set.set_experiment_context(experiment2_context)
        exp_set.build_experiment_chains()

        parent_name = 'basic.test_wl.series2_4'
        chained_name = 'basic.test_wl.series2_4.chain.0.basic.test_wl.test1'
        chained_dir = '0.basic.test_wl.test1'
        assert parent_name in exp_set.experiments
        assert chained_name in exp_set.chained_experiments

        parent_inst = exp_set.get_experiment(parent_name)
        chained_inst = exp_set.get_experiment(chained_name)

        parent_run_dir = parent_inst.expander.expand_var('{experiment_run_dir}')
        expected_dir = os.path.join(parent_run_dir, 'chained_experiments', chained_dir)
        assert chained_inst.variables['experiment_run_dir'] == expected_dir


def test_chained_cycle_errors(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'processes_per_node': '1',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }

        experiment1_context = ramble.context.Context()
        experiment1_context.context_name = 'test1'
        experiment1_context.variables = {
            'n_ranks': '2'
        }

        experiment2_context = ramble.context.Context()
        experiment2_context.context_name = 'series2_{n_ranks}'
        experiment2_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_ranks': '4'
        }
        experiment2_context.chained_experiments = [
            {
                'name': 'basic.test_wl.series2_4',
                'order': 'before_root',
                'command': '{execute_experiment}',
                'variables': {}
            },
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment1_context)
        exp_set.set_experiment_context(experiment2_context)
        with pytest.raises(ChainCycleDetectedError):
            exp_set.build_experiment_chains()
            captured = capsys.readouterr
            assert "Cycle detected in experiment chain" in captured


def test_chained_invalid_order_errors(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'processes_per_node': '1',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }

        experiment1_context = ramble.context.Context()
        experiment1_context.context_name = 'test1'
        experiment1_context.variables = {
            'n_ranks': '2'
        }

        experiment2_context = ramble.context.Context()
        experiment2_context.context_name = 'series2_{n_ranks}'
        experiment2_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_ranks': '4'
        }
        experiment2_context.chained_experiments = [
            {
                'name': 'basic.test_wl.test1',
                'order': 'foo',
                'command': '{execute_experiment}',
                'variables': {}
            },
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment1_context)
        exp_set.set_experiment_context(experiment2_context)
        with pytest.raises(InvalidChainError):
            exp_set.build_experiment_chains()
            captured = capsys.readouterr
            assert "Invalid experiment chain defined:" in captured


def test_modifiers_set_correctly(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'processes_per_node': '1',
            'mpi_command': '',
            'batch_submit': ''
        }
        application_context.modifiers = [
            {
                'name': 'test_app_mod',
                'mode': 'test_app',
                'on_executable': [
                    'builtin::env_vars'
                ]
            }
        ]

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }
        workload_context.modifiers = [
            {
                'name': 'test_wl_mod',
                'mode': 'test_wl',
                'on_executable': [
                    'builtin::env_vars'
                ]
            }
        ]

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'test1'
        experiment_context.variables = {
            'n_ranks': '2'
        }
        experiment_context.modifiers = [
            {
                'name': 'test_exp1_mod',
                'mode': 'test_exp1',
                'on_executable': [
                    'builtin::env_vars'
                ]
            }
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)

        assert 'basic.test_wl.test1' in exp_set.experiments
        app_inst = exp_set.experiments['basic.test_wl.test1']
        assert app_inst.modifiers is not None

        expected_modifiers = set(['test_app_mod', 'test_wl_mod', 'test_exp1_mod'])
        for mod_def in app_inst.modifiers:
            assert mod_def['name'] in expected_modifiers
            expected_modifiers.remove(mod_def['name'])
        assert len(expected_modifiers) == 0


def test_explicit_zips_work(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }
        experiment_context.zips = {
            'test_zip': ['n_nodes']
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()


def test_explicit_zips_in_matrix(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{exp_var1}'
        experiment_context.variables = {
            'exp_var1': ['1', 'a', '3'],
            'exp_var2': ['2', 'b', '4'],
            'n_nodes': ['2', '4']
        }
        experiment_context.matrices = [['test_zip']]
        experiment_context.zips = {
            'test_zip': ['exp_var1', 'exp_var2']
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4_1' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_4_a' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_4_3' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8_1' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8_a' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8_3' in exp_set.experiments.keys()


def test_explicit_zips_unconsumed(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}_{exp_var1}'
        experiment_context.variables = {
            'exp_var1': ['1', 'a', '3'],
            'exp_var2': ['2', 'b', '4'],
            'n_nodes': ['2', '4']
        }
        experiment_context.matrices = [['n_nodes']]
        experiment_context.zips = {
            'test_zip': ['exp_var1', 'exp_var2']
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4_1' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_4_a' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_4_3' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8_1' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8_a' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8_3' in exp_set.experiments.keys()


def test_single_var_explicit_zip(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }
        experiment_context.zips = {
            'test_zip': ['n_nodes'],
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()


def test_zip_multi_use_var_errors(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }
        experiment_context.zips = {
            'test_zip1': ['n_nodes'],
            'test_zip2': ['n_nodes'],
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        with pytest.raises(SystemExit):
            exp_set.set_experiment_context(experiment_context)
            captured = capsys.readouterr()
            assert 'Variable n_nodes is used across multiple zips' in captured


def test_zip_non_list_var_errors(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'n_nodes': ['2', '4']
        }
        experiment_context.zips = {
            'test_zip': ['exp_var1', 'processes_per_node'],
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        with pytest.raises(SystemExit):
            exp_set.set_experiment_context(experiment_context)
            captured = capsys.readouterr()
            assert 'Variable processes_per_node in zip test_zip does not refer to a vector' in \
                captured


def test_zip_variable_lengths_errors(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {}

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'processes_per_node': ['2'],
            'n_nodes': ['2', '4']
        }
        experiment_context.zips = {
            'test_zip': ['n_nodes', 'processes_per_node'],
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        with pytest.raises(SystemExit):
            exp_set.set_experiment_context(experiment_context)
            captured = capsys.readouterr()
            assert 'Length mismatch in zip test_zip in experiment series1_{n_ranks}' in captured
            assert 'Variable processes_per_node has length 1' in captured
            assert 'Variable n_nodes has length 2' in captured


def test_vector_experiment_with_explicit_excludes(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }
        experiment_context.exclude = {
            'variables': {
                'n_nodes': ['4']
            }
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' not in exp_set.experiments.keys()


def test_matrix_experiments_explicit_excludes(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }
        experiment_context.matrices = [
            ['n_nodes']
        ]
        experiment_context.exclude = {
            'variables': {
                'n_nodes': ['3'],
            },
            'matrix': ['n_nodes']
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' not in exp_set.experiments.keys()


def test_vector_experiment_with_where_excludes(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['1', '2', '3', '4', '5']
        }
        experiment_context.exclude = {
            'where': [
                '{n_nodes} > 2 and {n_nodes} < 5'
            ]
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' not in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' not in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_10' in exp_set.experiments.keys()


def test_vector_experiment_with_multi_where_excludes(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['1', '2', '3', '4', '5']
        }
        experiment_context.exclude = {
            'where': [
                '{n_nodes} < 2',
                '{n_nodes} > 4'
            ]
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_2' not in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_10' not in exp_set.experiments.keys()


def test_unused_vector_no_error(request, mutable_mock_workspace_path):
    ws_name = request.node.name
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'other_var': ['1', '2,', '3'],
            'n_nodes': ['1', '2', '3', '4', '5']
        }
        experiment_context.exclude = {
            'where': [
                '{n_nodes} < 2',
                '{n_nodes} > 4'
            ]
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_2' not in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_10' not in exp_set.experiments.keys()


def test_unused_zip_no_error(request, mutable_mock_workspace_path):
    ws_name = request.node.name
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'series1_{n_ranks}'
        experiment_context.variables = {
            'exp_var1': '1',
            'exp_var2': '2',
            'other_var_1': ['1', '2,', '3'],
            'other_var_2': ['1', '2,', '3'],
            'n_nodes': ['1', '2', '3', '4', '5']
        }
        experiment_context.zips = {
            'test_zip': ['other_var_1', 'other_var_2'],
        }
        experiment_context.exclude = {
            'where': [
                '{n_nodes} < 2',
                '{n_nodes} > 4'
            ]
        }

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.series1_2' not in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_10' not in exp_set.experiments.keys()


def test_unused_var_propagates_to_chain(request, mutable_mock_workspace_path):
    ws_name = request.node.name
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        expanded_app_context = ramble.context.Context()
        expanded_app_context.context_name = 'expanded_foms'
        expanded_app_context.variables = {
            'processes_per_node': '1',
            'mpi_command': '',
            'batch_submit': ''
        }

        expanded_wl_context = ramble.context.Context()
        expanded_wl_context.context_name = 'test_wl'
        expanded_wl_context.variables = {}

        expanded_exp_context = ramble.context.Context()
        expanded_exp_context.context_name = 'test'
        expanded_exp_context.variables = {
            'n_ranks': '1',
            'my_var': '2.0'
        }
        expanded_exp_context.is_template = True

        exp_set.set_application_context(expanded_app_context)
        exp_set.set_workload_context(expanded_wl_context)
        exp_set.set_experiment_context(expanded_exp_context)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'processes_per_node': '1',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'test1'
        experiment_context.variables = {
            'n_ranks': '2',
            'my_var': '5.0'
        }
        experiment_context.chained_experiments = [
            {
                'name': 'expanded_foms.test_wl.test',
                'order': 'after_root',
                'command': '{execute_experiment}',
                'inherit_variables': ['my_var']
            },
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.test1' in exp_set.experiments
        assert 'basic.test_wl.test1.chain.0.expanded_foms.test_wl.test' in \
            exp_set.chained_experiments

        app_inst = exp_set.get_experiment('basic.test_wl.test1.chain.0.expanded_foms.test_wl.test')

        assert app_inst.variables['my_var'] == '5.0'


def test_custom_executables_track_variables(request, mutable_mock_workspace_path):
    ws_name = request.node.name
    workspace('create', ws_name)

    assert ws_name in workspace('list')

    with ramble.workspace.read(ws_name) as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        expanded_app_context = ramble.context.Context()
        expanded_app_context.context_name = 'expanded_foms'
        expanded_app_context.variables = {
            'processes_per_node': '1',
            'mpi_command': '',
            'batch_submit': ''
        }

        expanded_wl_context = ramble.context.Context()
        expanded_wl_context.context_name = 'test_wl'
        expanded_wl_context.variables = {}

        expanded_exp_context = ramble.context.Context()
        expanded_exp_context.context_name = 'test'
        expanded_exp_context.variables = {
            'n_ranks': '1',
            'my_var': '2.0'
        }
        expanded_exp_context.is_template = True

        exp_set.set_application_context(expanded_app_context)
        exp_set.set_workload_context(expanded_wl_context)
        exp_set.set_experiment_context(expanded_exp_context)

        application_context = ramble.context.Context()
        application_context.context_name = 'basic'
        application_context.variables = {
            'app_var1': '1',
            'app_var2': '2',
            'processes_per_node': '1',
            'mpi_command': '',
            'batch_submit': ''
        }

        workload_context = ramble.context.Context()
        workload_context.context_name = 'test_wl'
        workload_context.variables = {
            'wl_var1': '1',
            'wl_var2': '2',
        }

        experiment_context = ramble.context.Context()
        experiment_context.context_name = 'test1'
        experiment_context.variables = {
            'n_ranks': '2',
            'my_var': '5.0'
        }
        experiment_context.chained_experiments = [
            {
                'name': 'expanded_foms.test_wl.test',
                'order': 'after_root',
                'command': '{execute_experiment}',
                'inherit_variables': ['my_var']
            },
        ]

        exp_set.set_application_context(application_context)
        exp_set.set_workload_context(workload_context)
        exp_set.set_experiment_context(experiment_context)
        exp_set.build_experiment_chains()

        assert 'basic.test_wl.test1' in exp_set.experiments
        assert 'basic.test_wl.test1.chain.0.expanded_foms.test_wl.test' in \
            exp_set.chained_experiments

        app_inst = exp_set.get_experiment('basic.test_wl.test1.chain.0.expanded_foms.test_wl.test')

        assert app_inst.variables['my_var'] == '5.0'
