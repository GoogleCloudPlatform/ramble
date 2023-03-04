# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the Application class"""

import pytest


@pytest.mark.parametrize('app', [
    'basic', 'basic-inherited'
])
def test_app_features(mutable_mock_repo, app):
    app_inst = mutable_mock_repo.get(app)
    assert hasattr(app_inst, 'workloads')
    assert hasattr(app_inst, 'executables')
    assert hasattr(app_inst, 'figures_of_merit')
    assert hasattr(app_inst, 'inputs')
    assert hasattr(app_inst, 'default_compilers')
    assert hasattr(app_inst, 'mpi_libraries')
    assert hasattr(app_inst, 'software_specs')
    assert hasattr(app_inst, 'workload_variables')


def test_basic_app(mutable_mock_repo):
    basic_inst = mutable_mock_repo.get('basic')
    assert 'foo' in basic_inst.executables
    assert basic_inst.executables['foo']['template'] == 'bar'
    assert not basic_inst.executables['foo']['mpi']
    assert 'bar' in basic_inst.executables
    assert basic_inst.executables['bar']['template'] == 'baz'
    assert basic_inst.executables['bar']['mpi']

    assert 'test_wl' in basic_inst.workloads
    assert basic_inst.workloads['test_wl']['executables'] == ['builtin::env_vars', 'foo']
    assert basic_inst.workloads['test_wl']['inputs'] == ['input']
    assert 'test_wl2' in basic_inst.workloads
    assert basic_inst.workloads['test_wl2']['executables'] == ['builtin::env_vars', 'bar']
    assert basic_inst.workloads['test_wl2']['inputs'] == ['input']

    assert 'test_fom' in basic_inst.figures_of_merit
    fom_conf = basic_inst.figures_of_merit['test_fom']
    assert fom_conf['log_file'] == 'log_file'
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


def test_env_var_set_command_gen(mutable_mock_repo):
    basic_inst = mutable_mock_repo.get('basic')

    tests = {
        'var1': 'val1',
        'var2': 'val2'
    }

    answer = [
        'export var1=val1;',
        'export var2=val2;'
    ]

    out_cmds, _ = basic_inst._get_env_set_commands(tests, set())
    for cmd in answer:
        assert cmd in out_cmds


def test_env_var_append_command_gen(mutable_mock_repo):
    basic_inst = mutable_mock_repo.get('basic')

    tests = [
        {
            'var-separator': ',',
            'vars': {
                'var1': 'val1',
                'var2': 'val2'
            },
            'paths': {
                'path1': 'path1',
                'path2': 'path2'
            }
        },
        {
            'var-separator': ',',
            'vars': {
                'var1': 'val2',
                'var2': 'val1'
            },
        }
    ]

    answer = [
        "export var1='${var1},val1,val2';",
        "export var2='${var2},val2,val1';",
        "export path1='${path1}:path1';",
        "export path2='${path2}:path2';"
    ]

    out_cmds, _ = basic_inst._get_env_append_commands(tests, set())
    for cmd in answer:
        assert cmd in out_cmds


def test_env_var_prepend_command_gen(mutable_mock_repo):
    basic_inst = mutable_mock_repo.get('basic')

    tests = [
        {
            'paths': {
                'path1': 'path1',
                'path2': 'path2'
            }
        },
        {
            'paths': {
                'path1': 'path2',
                'path2': 'path1'
            }
        }
    ]

    answer = [
        "export path1='path2:path1:${path1}';",
        "export path2='path1:path2:${path2}';"
    ]

    out_cmds, _ = basic_inst._get_env_prepend_commands(tests, set())
    for cmd in answer:
        assert cmd in out_cmds


def test_env_var_unset_command_gen(mutable_mock_repo):
    basic_inst = mutable_mock_repo.get('basic')

    tests = [
        'var1',
        'var2'
    ]

    answer = [
        'unset var1;',
        'unset var2;'
    ]

    out_cmds, _ = basic_inst._get_env_unset_commands(tests, set())
    for cmd in answer:
        assert cmd in out_cmds
