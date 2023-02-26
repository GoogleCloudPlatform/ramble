# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
import ramble.experiment_set
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path',
                                     'mutable_mock_repo',
                                     )

workspace  = RambleCommand('workspace')


def test_single_experiment_in_set(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        exp_name = 'series1_{n_ranks}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': '2',
        }

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)
        exp_set.set_experiment_context(exp_name, exp_vars, None, None)

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()


def test_vector_experiment_in_set(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        exp_name = 'series1_{n_ranks}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)
        exp_set.set_experiment_context(exp_name, exp_vars, None, None)

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()


def test_nonunique_vector_errors(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        exp_name = 'series1_{preocesses_per_node}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)
        with pytest.raises(SystemExit):
            exp_set.set_experiment_context(exp_name, exp_vars, None, None)
            captured = capsys.readouterr()
            assert "is not unique." in captured


def test_zipped_vector_experiments(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }
        exp_name = 'series1_{n_ranks}_{processes_per_node}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)
        exp_set.set_experiment_context(exp_name, exp_vars, None, None)

        assert 'basic.test_wl.series1_4_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_16_4' in exp_set.experiments.keys()


def test_matrix_experiments(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': '2'
        }
        exp_name = 'series1_{n_ranks}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }

        exp_matrices = [
            ['n_nodes']
        ]

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)
        exp_set.set_experiment_context(exp_name, exp_vars, None, exp_matrices)

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' in exp_set.experiments.keys()


def test_matrix_multiplication_experiments(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['1', '4', '6']
        }
        exp_name = 'series1_{n_ranks}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '4']
        }

        exp_matrices = [
            ['n_nodes', 'processes_per_node']
        ]

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)
        exp_set.set_experiment_context(exp_name, exp_vars, None, exp_matrices)

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

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }
        exp_name = 'series1_{n_ranks}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }

        exp_matrices = [
            ['n_nodes']
        ]

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)
        exp_set.set_experiment_context(exp_name, exp_vars, None, exp_matrices)

        assert 'basic.test_wl.series1_4' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_8' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_6' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_12' in exp_set.experiments.keys()


def test_multi_matrix_experiments(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }
        exp_name = 'series1_{n_ranks}_{processes_per_node}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }

        exp_matrices = [
            ['n_nodes'],
            ['processes_per_node']
        ]

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)
        exp_set.set_experiment_context(exp_name, exp_vars, None, exp_matrices)

        assert 'basic.test_wl.series1_4_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_12_4' in exp_set.experiments.keys()


def test_matrix_undefined_var_errors(mutable_mock_workspace_path, capsys):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }
        exp_name = 'series1_{n_ranks}_{processes_per_node}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }

        exp_matrices = [
            ['n_nodes'],
            ['foo']
        ]

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)

        with pytest.raises(SystemExit):
            exp_set.set_experiment_context(exp_name, exp_vars, None, exp_matrices)
            captured = capsys.readouterr()
            assert "variable foo has not been defined yet." in captured


def test_experiment_names_match(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        exp_set = ramble.experiment_set.ExperimentSet(ws)

        app_name = 'basic'
        app_vars = {
            'app_var1': '1',
            'app_var2': '2',
            'n_ranks': '{processes_per_node}*{n_nodes}'
        }

        wl_name = 'test_wl'
        wl_vars = {
            'wl_var1': '1',
            'wl_var2': '2',
            'processes_per_node': ['2', '4']
        }
        exp_name = 'series1_{n_ranks}_{processes_per_node}'
        exp_vars = {
            'exp_var1': '1',
            'exp_var2': '2',
            'n_nodes': ['2', '3']
        }

        exp_matrices = [
            ['n_nodes'],
            ['processes_per_node']
        ]

        exp_set.set_application_context(app_name, app_vars, None)
        exp_set.set_workload_context(wl_name, wl_vars, None)
        exp_set.set_experiment_context(exp_name, exp_vars, None, exp_matrices)

        assert 'basic.test_wl.series1_4_2' in exp_set.experiments.keys()
        assert 'basic.test_wl.series1_12_4' in exp_set.experiments.keys()

        for exp, app in exp_set.all_experiments():
            assert exp == app.expander.expand_var('{experiment_namespace}')
