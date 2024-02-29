# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the Application class"""

import pytest
import enum
import deprecation

from ramble.appkit import *  # noqa


app_types = [
    ApplicationBase,  # noqa: F405
    ExecutableApplication,  # noqa: F405
    SpackApplication  # noqa: F405
]

func_types = enum.Enum('func_types', ['method', 'directive'])


@pytest.mark.parametrize('app_class', app_types)
def test_application_type_features(app_class):
    app_path = '/path/to/app'
    test_app = app_class(app_path)
    assert hasattr(test_app, 'workloads')
    assert hasattr(test_app, 'executables')
    assert hasattr(test_app, 'figures_of_merit')
    assert hasattr(test_app, 'inputs')
    assert hasattr(test_app, 'workload_variables')
    assert hasattr(test_app, 'environment_variables')
    assert hasattr(test_app, 'compilers')
    assert hasattr(test_app, 'software_specs')
    assert hasattr(test_app, 'required_packages')
    assert hasattr(test_app, 'maintainers')
    assert hasattr(test_app, 'package_manager_configs')


def add_workload(app_inst, wl_num=1, func_type=func_types.directive):
    wl_name = 'TestWorkload%s' % wl_num
    exec_list = ['Workload%sExec1' % wl_num]
    exec_var = 'Workload%sExec2' % wl_num
    inpt_list = ['Workload%sInput1' % wl_num]
    inpt_var = 'Workload%sInput2' % wl_num

    if func_type == func_types.directive:
        workload(wl_name, executables=exec_list, executable=exec_var,  # noqa: F405
                 inputs=inpt_list, input=inpt_var)(app_inst)
    elif func_type == func_types.method:
        app_inst.workload(wl_name, executables=exec_list, executable=exec_var,  # noqa: F405
                          inputs=inpt_list, input=inpt_var)
    else:
        assert False

    workload_def = {
        'name': wl_name,
        'executables': exec_list.copy(),
        'inputs': inpt_list.copy()
    }

    workload_def['executables'].append(exec_var)
    workload_def['inputs'].append(inpt_var)

    return workload_def


def add_executable(app_inst, exe_num=1, func_type=func_types.directive):
    nompi_exec_name = 'SerialExe%s' % exe_num
    mpi_exec_name = 'MpiExe%s' % exe_num
    nompi_list_exec_name = 'MultiLineSerialExe%s' % exe_num
    mpi_list_exec_name = 'MultiLineMpiExe%s' % exe_num
    template = 'application%s.x -i {input_path}' % exe_num
    redirect_test = '{output_file}'
    output_capture = '>>'

    if func_type == func_types.directive:
        executable(nompi_exec_name,
                   template,  # noqa: F405
                   use_mpi=False,
                   redirect=redirect_test,
                   output_capture=output_capture)(app_inst)

        executable(mpi_exec_name, template,  # noqa: F405
                   use_mpi=True)(app_inst)

        executable(nompi_list_exec_name,  # noqa: F405
                   template=[template, template, template],
                   use_mpi=False, redirect=None)(app_inst)

        executable(mpi_list_exec_name, template=[template, template],  # noqa: F405
                   use_mpi=True, redirect=redirect_test)(app_inst)
    elif func_type == func_types.method:
        app_inst.executable(nompi_exec_name,
                            template,  # noqa: F405
                            use_mpi=False,
                            redirect=redirect_test,
                            output_capture=output_capture)

        app_inst.executable(mpi_exec_name, template,  # noqa: F405
                            use_mpi=True)

        app_inst.executable(nompi_list_exec_name,  # noqa: F405
                            template=[template, template, template],
                            use_mpi=False, redirect=None)

        app_inst.executable(mpi_list_exec_name, template=[template, template],  # noqa: F405
                            use_mpi=True, redirect=redirect_test)
    else:
        assert False

    exec_def = {
        nompi_exec_name: {
            'template': [template],
            'mpi': False,
            'redirect': redirect_test,
            'output_capture': output_capture
        },
        mpi_exec_name: {
            'template': [template],
            'mpi': True,
            'redirect': '{log_file}'  # Default value
        },
        nompi_list_exec_name: {
            'template': [template, template, template],
            'mpi': False,
            'redirect': None
        },
        mpi_list_exec_name: {
            'template': [template, template],
            'mpi': True,
            'redirect': redirect_test
        },

    }

    return exec_def


def add_figure_of_merit(app_inst, fom_num=1, func_type=func_types.directive):
    fom_name = 'TestFom%s' % fom_num
    fom_log = '{log_file}'
    fom_regex = '.*(?P<fom%s_val>[0-9]+).*' % fom_num
    fom_group = 'fom%s_val' % fom_num
    fom_units = '(s)'

    if func_type == func_types.directive:
        figure_of_merit(fom_name, log_file=fom_log, fom_regex=fom_regex,  # noqa: F405
                        group_name=fom_group, units=fom_units)(app_inst)
    elif func_type == func_types.method:
        app_inst.figure_of_merit(fom_name, log_file=fom_log, fom_regex=fom_regex,  # noqa: F405
                                 group_name=fom_group, units=fom_units)
    else:
        assert False

    fom_def = {
        fom_name: {
            'log_file': fom_log,
            'regex': fom_regex,
            'group_name': fom_group,
            'units': fom_units
        }
    }

    return fom_def


def add_input_file(app_inst, input_num=1, func_type=func_types.directive):
    input_name = 'MainTestInput%s' % input_num
    input_url = 'https://input%s.com/file.tar.gz' % input_num
    input_desc = 'This is a test input file #%s' % input_num
    input_target = '{application_input_dir}/test_dir%s' % input_num

    # Add an input with a target dir
    if func_type == func_types.directive:
        input_file(input_name, input_url, input_desc,  # noqa: F405
                   target_dir=input_target)(app_inst)
    elif func_type == func_types.method:
        app_inst.input_file(input_name, input_url, input_desc,  # noqa: F405
                            target_dir=input_target)
    else:
        assert False

    input_defs = {}
    input_defs[input_name] = {
        'url': input_url,
        'description': input_desc,
        'target_dir': input_target
    }

    input_name = 'SecondaryTestInput%s' % input_num
    input_url = 'https://input%s.com/file.tar.gz' % input_num
    input_desc = 'This is a test secondary input file #%s' % input_num

    # Add an input without a target dir
    if func_type == func_types.directive:
        input_file(input_name, input_url, input_desc)(app_inst)  # noqa: F405
    elif func_type == func_types.method:
        app_inst.input_file(input_name, input_url, input_desc)  # noqa: F405
    else:
        assert False

    input_defs[input_name] = {
        'url': input_url,
        'description': input_desc,
        'target_dir': '{input_name}'
    }

    return input_defs


# TODO: can this be dried with the modifier language add_compiler?
@deprecation.fail_if_not_removed
def add_compiler(app_inst, spec_num=1, func_type=func_types.directive):
    spec_name = 'Compiler%spec_num'
    spec_spack_spec = f'compiler_base@{spec_num}.0 +var1 ~var2'
    spec_compiler_spec = 'compiler1_base@{spec_num}'

    spec_defs = {}
    spec_defs[spec_name] = {
        'spack_spec': spec_spack_spec,
        'compiler_spec': spec_compiler_spec
    }

    if func_type == func_types.directive:
        default_compiler(spec_name, spack_spec=spec_spack_spec,  # noqa: F405
                         compiler_spec=spec_compiler_spec)(app_inst)
        define_compiler(spec_name, spack_spec=spec_spack_spec,  # noqa: F405
                        compiler_spec=spec_compiler_spec)(app_inst)
    elif func_type == func_types.method:
        app_inst.default_compiler(spec_name, spack_spec=spec_spack_spec,  # noqa: F405
                                  compiler_spec=spec_compiler_spec)
        app_inst.define_compiler(spec_name, spack_spec=spec_spack_spec,  # noqa: F405
                                 compiler_spec=spec_compiler_spec)
    else:
        assert False

    spec_name = 'OtherCompiler%spec_num'
    spec_spack_spec = f'compiler_base@{spec_num}.1 +var1 ~var2 target=x86_64'
    spec_compiler_spec = 'compiler2_base@{spec_num}'

    spec_defs[spec_name] = {
        'spack_spec': spec_spack_spec,
        'compiler_spec': spec_compiler_spec
    }

    if func_type == func_types.directive:
        define_compiler(spec_name, spack_spec=spec_spack_spec,  # noqa: f405
                        compiler_spec=spec_compiler_spec)(app_inst)
    elif func_type == func_types.method:
        app_inst.define_compiler(spec_name, spack_spec=spec_spack_spec,  # noqa: F405
                                 compiler_spec=spec_compiler_spec)
    else:
        assert False

    return spec_defs


def add_software_spec(app_inst, spec_num=1, func_type=func_types.directive):
    spec_name = 'NoMPISpec%s' % spec_num
    spec_spack_spec = f'NoMPISpec@{spec_num} +var1 ~var2 target=x86_64'
    spec_compiler = 'spec_compiler1@1.1'

    spec_defs = {}
    spec_defs[spec_name] = {
        'spack_spec': spec_spack_spec,
        'compiler': spec_compiler
    }

    if func_type == func_types.directive:
        software_spec(spec_name,  # noqa: F405
                      spack_spec=spec_spack_spec,
                      compiler=spec_compiler)(app_inst)
    elif func_type == func_types.method:
        app_inst.software_spec(spec_name,  # noqa: F405
                               spack_spec=spec_spack_spec,
                               compiler=spec_compiler)
    else:
        assert False

    spec_name = 'MPISpec%s' % spec_num
    spec_spack_spec = f'MPISpec@{spec_num} +var1 ~var2 target=x86_64'
    spec_compiler = 'spec_compiler1@1.1'

    spec_defs[spec_name] = {
        'spack_spec': spec_spack_spec,
        'compiler': spec_compiler
    }

    if func_type == func_types.directive:
        software_spec(spec_name,  # noqa: F405
                      spack_spec=spec_spack_spec,
                      compiler=spec_compiler)(app_inst)
    elif func_type == func_types.method:
        app_inst.software_spec(spec_name,  # noqa: F405
                               spack_spec=spec_spack_spec,
                               compiler=spec_compiler)
    else:
        assert False

    return spec_defs


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('app_class', app_types)
def test_workload_directive(app_class, func_type):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    test_defs.update(add_workload(app_inst, func_type=func_type))

    wl_name = test_defs['name']

    assert hasattr(app_inst, 'workloads')
    assert wl_name in app_inst.workloads
    assert 'executables' in app_inst.workloads[wl_name]
    assert 'inputs' in app_inst.workloads[wl_name]
    for test in test_defs['executables']:
        assert test in app_inst.workloads[wl_name]['executables']

    for test in test_defs['inputs']:
        assert test in app_inst.workloads[wl_name]['inputs']


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('app_class', app_types)
def test_executable_directive(app_class, func_type):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    test_defs.update(add_executable(app_inst, func_type=func_type))

    assert hasattr(app_inst, 'executables')
    for exe_name, conf in test_defs.items():
        assert exe_name in app_inst.executables
        for conf_name, conf_val in conf.items():
            assert hasattr(app_inst.executables[exe_name], conf_name)
            assert conf_val == getattr(app_inst.executables[exe_name],
                                       conf_name)


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('app_class', app_types)
def test_figure_of_merit_directive(app_class, func_type):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    test_defs.update(add_figure_of_merit(app_inst, func_type=func_type))

    assert hasattr(app_inst, 'figures_of_merit')
    for fom_name, conf in test_defs.items():
        assert fom_name in app_inst.figures_of_merit
        for conf_name, conf_val in conf.items():
            assert conf_name in app_inst.figures_of_merit[fom_name]
            assert app_inst.figures_of_merit[fom_name][conf_name] \
                == conf_val


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('app_class', app_types)
def test_input_file_directive(app_class, func_type):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    test_defs.update(add_input_file(app_inst, func_type=func_type))

    assert hasattr(app_inst, 'inputs')
    for input_name, conf in test_defs.items():
        assert input_name in app_inst.inputs

        for conf_name, conf_val in conf.items():
            assert conf_name in app_inst.inputs[input_name]
            assert app_inst.inputs[input_name][conf_name] \
                == conf_val

        assert 'extension' in app_inst.inputs[input_name]
        assert 'expand' in app_inst.inputs[input_name]


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('app_class', app_types)
def test_define_compiler_directive(app_class, func_type):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    if app_inst.uses_spack:
        test_defs.update(add_compiler(app_inst, 1, func_type=func_type))
        test_defs.update(add_compiler(app_inst, 2, func_type=func_type))

        assert hasattr(app_inst, 'compilers')
        for name, info in test_defs.items():
            assert name in app_inst.compilers
            for key, value in info.items():
                assert app_inst.compilers[name][key] == value
    else:
        test_defs.update(add_compiler(app_inst, 1, func_type=func_type))

        assert hasattr(app_inst, 'compilers')
        assert not app_inst.compilers


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('app_class', app_types)
def test_software_spec_directive(app_class, func_type):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    if app_inst.uses_spack:
        test_defs.update(add_software_spec(app_inst, 1, func_type=func_type))
        test_defs.update(add_software_spec(app_inst, 2, func_type=func_type))

        assert hasattr(app_inst, 'software_specs')
        for name, info in test_defs.items():
            assert name in app_inst.software_specs
            for key, value in info.items():
                assert app_inst.software_specs[name][key] == value
    else:
        test_defs.update(add_software_spec(app_inst, 1, func_type=func_type))

        assert hasattr(app_inst, 'software_specs')
        assert not app_inst.software_specs
