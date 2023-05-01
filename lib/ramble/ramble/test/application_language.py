# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the Application class"""

import pytest

from ramble.appkit import *  # noqa


app_types = [
    ApplicationBase,  # noqa: F405
    ExecutableApplication,  # noqa: F405
    SpackApplication  # noqa: F405
]


@pytest.mark.parametrize('app_class', app_types)
def test_application_type_features(app_class):
    app_path = '/path/to/app'
    test_app = app_class(app_path)
    assert hasattr(test_app, 'workloads')
    assert hasattr(test_app, 'executables')
    assert hasattr(test_app, 'figures_of_merit')
    assert hasattr(test_app, 'inputs')
    assert hasattr(test_app, 'workload_variables')
    assert hasattr(test_app, 'default_compilers')
    assert hasattr(test_app, 'mpi_libraries')
    assert hasattr(test_app, 'software_specs')


def add_workload(app_inst, wl_num=1):
    wl_name = 'TestWorkload%s' % wl_num
    exec_list = ['Workload%sExec1' % wl_num]
    exec_var = 'Workload%sExec2' % wl_num
    inpt_list = ['Workload%sInput1' % wl_num]
    inpt_var = 'Workload%sInput2' % wl_num

    workload(wl_name, executables=exec_list, executable=exec_var,  # noqa: F405
             inputs=inpt_list, input=inpt_var)(app_inst)

    workload_def = {
        'name': wl_name,
        'executables': exec_list.copy(),
        'inputs': inpt_list.copy()
    }

    workload_def['executables'].append(exec_var)
    workload_def['inputs'].append(inpt_var)

    return workload_def


def add_executable(app_inst, exe_num=1):
    nompi_exec_name = 'SerialExe%s' % exe_num
    mpi_exec_name = 'MpiExe%s' % exe_num
    nompi_list_exec_name = 'MultiLineSerialExe%s' % exe_num
    mpi_list_exec_name = 'MultiLineMpiExe%s' % exe_num
    template = 'application%s.x -i {input_path}' % exe_num
    redirect_test = '{output_file}'
    output_capture = '>>'

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

    exec_def = {
        nompi_exec_name: {
            'template': template,
            'mpi': False,
            'redirect': redirect_test,
            'output_capture': output_capture
        },
        mpi_exec_name: {
            'template': template,
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


def add_figure_of_merit(app_inst, fom_num=1):
    fom_name = 'TestFom%s' % fom_num
    fom_log = '{log_file}'
    fom_regex = '.*(?P<fom%s_val>[0-9]+).*' % fom_num
    fom_group = 'fom%s_val' % fom_num
    fom_units = '(s)'

    figure_of_merit(fom_name, fom_log, fom_regex,  # noqa: F405
                    fom_group, fom_units)(app_inst)

    fom_def = {
        fom_name: {
            'log_file': fom_log,
            'regex': fom_regex,
            'group_name': fom_group,
            'units': fom_units
        }
    }

    return fom_def


def add_input_file(app_inst, input_num=1):
    input_name = 'MainTestInput%s' % input_num
    input_url = 'https://input%s.com/file.tar.gz' % input_num
    input_desc = 'This is a test input file #%s' % input_num
    input_target = '{application_input_dir}/test_dir%s' % input_num

    # Add an input with a target dir
    input_file(input_name, input_url, input_desc,  # noqa: F405
               target_dir=input_target)(app_inst)

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
    input_file(input_name, input_url, input_desc)(app_inst)  # noqa: F405

    input_defs[input_name] = {
        'url': input_url,
        'description': input_desc,
        'target_dir': '{workload_name}'
    }

    return input_defs


def add_default_compiler(app_inst, spec_num=1):
    spec_name = 'Compiler%spec_num'
    spec_base = 'compiler_base'
    spec_ver = '%s.0' % spec_num
    spec_variants = '+var1 ~var2'
    spec_deps = 'dep1 dep2 dep3'
    spec_target = 'x86_64'

    spec_defs = {}
    spec_defs[spec_name] = {
        'base': spec_base,
        'version': spec_ver,
        'variants': spec_variants,
        'dependencies': spec_deps,
        'target': spec_target
    }

    default_compiler(spec_name, base=spec_base, version=spec_ver,  # noqa: F405
                     variants=spec_variants, dependencies=spec_deps,
                     target=spec_target)(app_inst)

    spec_name = 'OtherCompiler%spec_num'
    spec_base = 'compiler_base'
    spec_ver = '%s.1' % spec_num
    spec_variants = '+var1 ~var2'
    spec_deps = 'dep1 dep2 dep3'
    spec_target = 'x86_64'

    spec_defs[spec_name] = {
        'base': spec_base,
        'version': spec_ver,
        'variants': spec_variants,
        'dependencies': spec_deps,
        'target': spec_target
    }

    default_compiler(spec_name, base=spec_base, version=spec_ver,  # noqa: F405
                     variants=spec_variants, dependencies=spec_deps,
                     target=spec_target)(app_inst)

    return spec_defs


def add_mpi_library(app_inst, spec_num=1):
    spec_name = 'MpiLibrary%spec_num'
    spec_base = 'mpi_base'
    spec_ver = '%s.0' % spec_num
    spec_variants = '+var1 ~var2'
    spec_deps = 'dep1 dep2 dep3'
    spec_target = 'x86_64'

    spec_defs = {}
    spec_defs[spec_name] = {
        'base': spec_base,
        'version': spec_ver,
        'variants': spec_variants,
        'dependencies': spec_deps,
        'target': spec_target
    }

    mpi_library(spec_name, base=spec_base, version=spec_ver,  # noqa: F405
                variants=spec_variants, dependencies=spec_deps,
                target=spec_target)(app_inst)

    spec_name = 'MpiLibrary%spec_num'
    spec_base = 'mpi_base'
    spec_ver = '%s.1' % spec_num
    spec_variants = '+var1 ~var2'
    spec_deps = 'dep1 dep2 dep3'
    spec_target = 'x86_64'

    spec_defs[spec_name] = {
        'base': spec_base,
        'version': spec_ver,
        'variants': spec_variants,
        'dependencies': spec_deps,
        'target': spec_target
    }

    mpi_library(spec_name, base=spec_base, version=spec_ver,  # noqa: F405
                variants=spec_variants, dependencies=spec_deps,
                target=spec_target)(app_inst)

    return spec_defs


def add_software_spec(app_inst, spec_num=1):
    spec_name = 'NoMPISpec%s' % spec_num
    spec_base = 'NoMPISpec'
    spec_ver = spec_num
    spec_variants = '+var1 ~var2'
    spec_compiler = 'SpecComp'
    spec_deps = 'dep1 dep2 dep3'
    spec_target = 'x86_64'

    spec_defs = {}
    spec_defs[spec_name] = {
        'base': spec_base,
        'version': spec_ver,
        'variants': spec_variants,
        'compiler': spec_compiler,
        'dependencies': spec_deps,
        'target': spec_target
    }

    software_spec(spec_name, base=spec_base, version=spec_ver,  # noqa: F405
                  variants=spec_variants,
                  compiler=spec_compiler, dependencies=spec_deps,
                  target=spec_target)(app_inst)

    spec_name = 'MPISpec%s' % spec_num
    spec_base = 'MPISpec'
    spec_ver = spec_num
    spec_variants = '+var1 ~var2'
    spec_compiler = 'SpecComp'
    spec_mpi = 'SpecMPI'
    spec_deps = 'dep1 dep2 dep3'
    spec_target = 'x86_64'

    spec_defs[spec_name] = {
        'base': spec_base,
        'version': spec_ver,
        'variants': spec_variants,
        'compiler': spec_compiler,
        'mpi': spec_mpi,
        'dependencies': spec_deps,
        'target': spec_target
    }

    software_spec(spec_name, base=spec_base, version=spec_ver,  # noqa: F405
                  variants=spec_variants,
                  compiler=spec_compiler, dependencies=spec_deps,
                  mpi=spec_mpi, target=spec_target)(app_inst)

    return spec_defs


@pytest.mark.parametrize('app_class', app_types)
def test_workload_directive(app_class):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    test_defs.update(add_workload(app_inst))

    wl_name = test_defs['name']

    assert hasattr(app_inst, 'workloads')
    assert wl_name in app_inst.workloads
    assert 'executables' in app_inst.workloads[wl_name]
    assert 'inputs' in app_inst.workloads[wl_name]
    for test in test_defs['executables']:
        assert test in app_inst.workloads[wl_name]['executables']

    for test in test_defs['inputs']:
        assert test in app_inst.workloads[wl_name]['inputs']


@pytest.mark.parametrize('app_class', app_types)
def test_executable_directive(app_class):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    test_defs.update(add_executable(app_inst))

    assert hasattr(app_inst, 'executables')
    for exe_name, conf in test_defs.items():
        assert exe_name in app_inst.executables
        for conf_name, conf_val in conf.items():
            assert conf_name in app_inst.executables[exe_name]
            assert app_inst.executables[exe_name][conf_name] == conf_val
            assert isinstance(conf_val,
                   type(app_inst.executables[exe_name][conf_name]))


@pytest.mark.parametrize('app_class', app_types)
def test_figure_of_merit_directive(app_class):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    test_defs.update(add_figure_of_merit(app_inst))

    assert hasattr(app_inst, 'figures_of_merit')
    for fom_name, conf in test_defs.items():
        assert fom_name in app_inst.figures_of_merit
        for conf_name, conf_val in conf.items():
            assert conf_name in app_inst.figures_of_merit[fom_name]
            assert app_inst.figures_of_merit[fom_name][conf_name] \
                == conf_val


@pytest.mark.parametrize('app_class', app_types)
def test_input_file_directive(app_class):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    test_defs.update(add_input_file(app_inst))

    assert hasattr(app_inst, 'inputs')
    for input_name, conf in test_defs.items():
        assert input_name in app_inst.inputs

        for conf_name, conf_val in conf.items():
            assert conf_name in app_inst.inputs[input_name]
            assert app_inst.inputs[input_name][conf_name] \
                == conf_val

        assert 'extension' in app_inst.inputs[input_name]
        assert 'expand' in app_inst.inputs[input_name]


@pytest.mark.parametrize('app_class', app_types)
def test_default_compiler_directive(app_class):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    if app_inst.uses_spack:
        test_defs.update(add_default_compiler(app_inst, 1))
        test_defs.update(add_default_compiler(app_inst, 2))

        assert hasattr(app_inst, 'default_compilers')
        for name, info in test_defs.items():
            assert name in app_inst.default_compilers
            for key, value in info.items():
                assert app_inst.default_compilers[name][key] == value
    else:
        test_defs.update(add_default_compiler(app_inst, 1))

        assert hasattr(app_inst, 'default_compilers')
        assert not app_inst.default_compilers


@pytest.mark.parametrize('app_class', app_types)
def test_mpi_library_directive(app_class):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    if app_inst.uses_spack:
        test_defs.update(add_mpi_library(app_inst, 1))
        test_defs.update(add_mpi_library(app_inst, 2))

        assert hasattr(app_inst, 'mpi_libraries')
        for name, info in test_defs.items():
            assert name in app_inst.mpi_libraries
            for key, value in info.items():
                assert app_inst.mpi_libraries[name][key] == value
    else:
        test_defs.update(add_mpi_library(app_inst, 1))

        assert hasattr(app_inst, 'mpi_libraries')
        assert not app_inst.mpi_libraries


@pytest.mark.parametrize('app_class', app_types)
def test_software_spec_directive(app_class):
    app_inst = app_class('/not/a/path')
    test_defs = {}
    if app_inst.uses_spack:
        test_defs.update(add_software_spec(app_inst, 1))
        test_defs.update(add_software_spec(app_inst, 2))

        assert hasattr(app_inst, 'software_specs')
        for name, info in test_defs.items():
            assert name in app_inst.software_specs
            for key, value in info.items():
                assert app_inst.software_specs[name][key] == value
    else:
        test_defs.update(add_software_spec(app_inst, 1))

        assert hasattr(app_inst, 'software_specs')
        assert not app_inst.software_specs
