# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
import ramble.expander
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    'mutable_mock_workspace_path', 'config', 'mutable_mock_repo')

workspace  = RambleCommand('workspace')
add  = RambleCommand('add')
remove  = RambleCommand('remove')

ramble_config = RambleCommand('config')


def test_expansions(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        add('basic')
        exp = ramble.expander.Expander(ws)

        assert exp.workspace_vars['processes_per_node'] == -1

        exp.set_var('level1_var', 'level1')
        exp.set_var('level2_var', 'level2 {level1_var}')
        exp.set_var('level3_var', 'level3 {level2_var}')
        assert exp.expand_var('{level3_var}') == \
            "level3 level2 level1"

        assert exp.expand_var('2*{processes_per_node}') == '-2'

        assert exp.expand_var('2**4') == '16'

        assert exp.expand_var('((((16-10+2)/4)**2)*4)') == '16.0'

    workspace('remove', '-y', 'test')


def test_layered_expansions(mutable_mock_workspace_path):
    application_vars = {
        'app_var': 'test_app',
        'ppn': '5'
    }
    workload_vars = {
        'wl_var': 'test_wl',
        'n_threads': '2'
    }
    experiment_vars = {
        'exp_var': 'test_exp',
        'n_nodes': '3'
    }

    workspace('create', 'test')

    assert 'test' in workspace('list')

    with ramble.workspace.read('test') as ws:
        add('basic')
        exp = ramble.expander.Expander(ws)

        exp.set_application('basic')
        exp.set_application_vars(application_vars)

        exp.set_workload('test_wl')
        exp.set_workload_vars(workload_vars)

        exp.set_experiment('single_node')
        exp.set_experiment_vars(experiment_vars)

        union = {}
        union.update(application_vars)
        union.update(workload_vars)
        union.update(experiment_vars)

        for key, val in union.items():
            expansion = '{' + key + '}'
            result = exp.expand_var(expansion)
            assert result == val

    workspace('remove', '-y', 'test')


def test_experiment_name_expansions(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    experiment_name_template = 'exp_name_{new_var}'

    with ramble.workspace.read('test') as ws:
        exp = ramble.expander.Expander(ws)
        exp.set_application('basic')
        exp.set_application_vars({})

        exp.set_workload('test_wl')
        exp.set_workload_vars({})

        exp.set_experiment(experiment_name_template)
        exp.set_experiment_vars({'new_var': '2'})

        exp._finalize_experiment()

        assert exp.experiment_name == 'exp_name_2'

    workspace('remove', '-y', 'test')


def test_vector_expansions(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    template_base = 'exp_name'
    experiment_name_template = template_base + '_{n_nodes}'

    exp_vars_vector = {
        'n_nodes': [1, 2, 4, 8],
        'n_ranks': '{processes_per_node}*{n_nodes}',
        'processes_per_node': '1'
    }

    expected_exp_names = set()
    for n in exp_vars_vector['n_nodes']:
        expected_exp_names.add(template_base + '_%s' % n)

    with ramble.workspace.read('test') as ws:
        exp = ramble.expander.Expander(ws)
        exp.set_application('basic')
        exp.set_application_vars({})

        exp.set_workload('test_wl')
        exp.set_workload_vars({})

        exp.set_experiment(experiment_name_template)
        exp.set_experiment_vars(exp_vars_vector)

        for _ in exp.rendered_experiments():
            assert exp.experiment_name in expected_exp_names
            expected_exp_names.remove(exp.experiment_name)

    assert len(expected_exp_names) == 0

    workspace('remove', '-y', 'test')


def test_zipped_vector_expansions(mutable_mock_workspace_path):
    workspace('create', 'test')

    assert 'test' in workspace('list')

    template_base = 'exp_name'
    experiment_name_template = template_base + '_{n_nodes}_{processes_per_node}'

    exp_vars_vector = {
        'n_nodes': [1, 2, 4, 8],
        'n_ranks': '{processes_per_node}*{n_nodes}',
        'processes_per_node': [10, 20, 30, 40]
    }

    expected_exp_names = set()
    for n, p in zip(exp_vars_vector['n_nodes'], exp_vars_vector['processes_per_node']):
        expected_exp_names.add(template_base + '_%s_%s' % (n, p))

    with ramble.workspace.read('test') as ws:
        exp = ramble.expander.Expander(ws)
        exp.set_application('basic')
        exp.set_application_vars({})

        exp.set_workload('test_wl')
        exp.set_workload_vars({})

        exp.set_experiment(experiment_name_template)
        exp.set_experiment_vars(exp_vars_vector)

        for _ in exp.rendered_experiments():
            assert exp.experiment_name in expected_exp_names
            expected_exp_names.remove(exp.experiment_name)

    assert len(expected_exp_names) == 0

    workspace('remove', '-y', 'test')


def test_matrix_expansions(mutable_mock_workspace_path):
    import itertools
    workspace('create', 'test')

    assert 'test' in workspace('list')

    template_base = 'exp_name'
    experiment_name_template = template_base + '_{n_nodes}_{processes_per_node}'

    exp_vars_vector = {
        'n_nodes': [1, 2, 4],
        'n_ranks': '{processes_per_node}*{n_nodes}',
        'processes_per_node': [10, 20, 30, 40]
    }

    exp_matrix_vecs = [['n_nodes', 'processes_per_node']]

    expected_exp_names = set()
    for config in itertools.product(exp_vars_vector['n_nodes'],
                                    exp_vars_vector['processes_per_node']):
        expected_exp_names.add(template_base + '_%s_%s' % (config[0],
                                                           config[1]))

    with ramble.workspace.read('test') as ws:
        exp = ramble.expander.Expander(ws)
        exp.set_application('basic')
        exp.set_application_vars({})

        exp.set_workload('test_wl')
        exp.set_workload_vars({})

        exp.set_experiment(experiment_name_template)
        exp.set_experiment_vars(exp_vars_vector)
        exp.set_experiment_matrices(exp_matrix_vecs)

        for _ in exp.rendered_experiments():
            assert exp.experiment_name in expected_exp_names
            expected_exp_names.remove(exp.experiment_name)

    assert len(expected_exp_names) == 0

    workspace('remove', '-y', 'test')


def test_multi_matrix_expansions(mutable_mock_workspace_path):
    import itertools
    workspace('create', 'test')

    assert 'test' in workspace('list')

    template_base = 'exp_name'
    experiment_name_template = template_base + '_{n_nodes}_{processes_per_node}_{exp_idx}'

    exp_vars_vector = {
        'n_nodes': [1, 2, 4],
        'n_ranks': '{processes_per_node}*{n_nodes}',
        'processes_per_node': [10, 20, 30, 40],
        'exp_idx': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    }

    exp_matrix_vecs = [['n_nodes', 'processes_per_node'], ['exp_idx']]

    expected_exp_names = set()
    for config in zip(itertools.product(exp_vars_vector['n_nodes'],
                                        exp_vars_vector['processes_per_node']),
                      exp_vars_vector['exp_idx']):
        expected_exp_names.add(template_base + '_%s_%s_%s' % (config[0][0],
                                                              config[0][1],
                                                              config[1]))

    with ramble.workspace.read('test') as ws:
        exp = ramble.expander.Expander(ws)
        exp.set_application('basic')
        exp.set_application_vars({})

        exp.set_workload('test_wl')
        exp.set_workload_vars({})

        exp.set_experiment(experiment_name_template)
        exp.set_experiment_vars(exp_vars_vector)
        exp.set_experiment_matrices(exp_matrix_vecs)

        for _ in exp.rendered_experiments():
            assert exp.experiment_name in expected_exp_names
            expected_exp_names.remove(exp.experiment_name)

    assert len(expected_exp_names) == 0

    workspace('remove', '-y', 'test')


def test_matrix_vector_expansions(mutable_mock_workspace_path):
    import itertools
    workspace('create', 'test')

    assert 'test' in workspace('list')

    template_base = 'exp_name'
    experiment_name_template = template_base + '_{n_nodes}_{processes_per_node}_{exp_idx}'

    exp_vars_vector = {
        'n_nodes': [1, 2, 4],
        'n_ranks': '{processes_per_node}*{n_nodes}',
        'processes_per_node': [10, 20, 30, 40],
        'exp_idx': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    }

    exp_matrix_vecs = [['n_nodes', 'processes_per_node']]

    expected_exp_names = set()
    for config in itertools.product(exp_vars_vector['n_nodes'],
                                    exp_vars_vector['processes_per_node'],
                                    exp_vars_vector['exp_idx']):
        expected_exp_names.add(template_base + '_%s_%s_%s' % (config[0],
                                                              config[1],
                                                              config[2]))

    # with ramble.workspace.read('test') as ws:
    ws = ramble.workspace.read('test')
    exp = ramble.expander.Expander(ws)
    exp.set_application('basic')
    exp.set_application_vars({})

    exp.set_workload('test_wl')
    exp.set_workload_vars({})

    exp.set_experiment(experiment_name_template)
    exp.set_experiment_vars(exp_vars_vector)
    exp.set_experiment_matrices(exp_matrix_vecs)

    for _ in exp.rendered_experiments():
        assert exp.experiment_name in expected_exp_names
        expected_exp_names.remove(exp.experiment_name)

    assert len(expected_exp_names) == 0

    workspace('remove', '-y', 'test')
