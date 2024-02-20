# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def test_basic_inheritance(mutable_mock_apps_repo):
    app_inst = mutable_mock_apps_repo.get('basic-inherited')

    assert 'foo' in app_inst.executables
    assert app_inst.executables['foo'].template == ['bar']
    assert not app_inst.executables['foo'].mpi
    assert 'bar' in app_inst.executables
    assert app_inst.executables['bar'].template == ['baz']
    assert app_inst.executables['bar'].mpi

    assert 'test_wl' in app_inst.workloads
    assert app_inst.workloads['test_wl']['executables'] == ['builtin::env_vars', 'foo']
    assert app_inst.workloads['test_wl']['inputs'] == ['input']
    assert 'test_wl2' in app_inst.workloads
    assert app_inst.workloads['test_wl2']['executables'] == ['builtin::env_vars', 'bar']
    assert app_inst.workloads['test_wl2']['inputs'] == ['input']
    assert 'test_wl3' in app_inst.workloads
    assert app_inst.workloads['test_wl3']['executables'] == ['builtin::env_vars', 'foo']
    assert app_inst.workloads['test_wl3']['inputs'] == ['inherited_input']

    assert 'test_fom' in app_inst.figures_of_merit
    fom_conf = app_inst.figures_of_merit['test_fom']
    assert fom_conf['log_file'] == '{log_file}'
    assert fom_conf['regex'] == \
        r'(?P<test>[0-9]+\.[0-9]+).*seconds.*'  # noqa: W605
    assert fom_conf['group_name'] == 'test'
    assert fom_conf['units'] == 's'

    assert 'input' in app_inst.inputs
    assert app_inst.inputs['input']['url'] == \
        'file:///tmp/test_file.log'
    assert app_inst.inputs['input']['description'] == \
        'Not a file'
    assert 'inherited_input' in app_inst.inputs
    assert app_inst.inputs['inherited_input']['url'] == \
        'file:///tmp/inherited_file.log'
    assert app_inst.inputs['inherited_input']['description'] == \
        'Again, not a file'

    assert 'test_wl' in app_inst.workload_variables
    assert 'my_var' in app_inst.workload_variables['test_wl']
    assert app_inst.workload_variables['test_wl']['my_var']['default'] == \
        '1.0'

    assert app_inst.workload_variables['test_wl']['my_var']['description'] \
        == 'Example var'
