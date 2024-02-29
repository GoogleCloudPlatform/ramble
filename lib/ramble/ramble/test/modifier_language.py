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

from ramble.modkit import *  # noqa
from ramble.language.language_base import DirectiveError


mod_types = [
    ModifierBase,  # noqa: F405
    BasicModifier,  # noqa: F405
    SpackModifier  # noqa: F405
]

func_types = enum.Enum('func_types', ['method', 'directive'])


def generate_mod_class(base_class):

    class GeneratedClass(base_class):
        _language_classes = base_class._language_classes.copy()

        def __init__(self, file_path):
            super().__init__(file_path)

    return GeneratedClass


@pytest.mark.parametrize('mod_class', mod_types)
def test_modifier_type_features(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_path = '/path/to/mod'
    test_mod = test_class(mod_path)
    assert hasattr(test_mod, 'figure_of_merit_contexts')
    assert hasattr(test_mod, 'archive_patterns')
    assert hasattr(test_mod, 'figures_of_merit')
    assert hasattr(test_mod, 'modes')
    assert hasattr(test_mod, 'variable_modifications')
    assert hasattr(test_mod, 'software_specs')
    assert hasattr(test_mod, 'compilers')
    assert hasattr(test_mod, 'required_packages')
    assert hasattr(test_mod, 'success_criteria')
    assert hasattr(test_mod, 'builtins')
    assert hasattr(test_mod, 'modifier_variables')
    assert hasattr(test_mod, 'executable_modifiers')
    assert hasattr(test_mod, 'env_var_modifications')
    assert hasattr(test_mod, 'maintainers')
    assert hasattr(test_mod, 'package_manager_configs')


def add_mode(mod_inst, mode_num=1, func_type=func_types.directive):
    mode_name = 'TestMode%s' % mode_num
    mode_desc = 'This is a test mode'

    if func_type == func_types.directive:
        mode(mode_name, description=mode_desc)(mod_inst)  # noqa: F405
    elif func_type == func_types.method:
        mod_inst.mode(mode_name, description=mode_desc)  # noqa: F405
    else:
        assert False

    mode_def = {
        'name': mode_name,
        'description': mode_desc
    }

    return mode_def


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_mode_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_mode(mod_inst, func_type=func_type).copy())

    assert hasattr(mod_inst, 'modes')
    for test_def in test_defs:
        mode_name = test_def['name']
        assert mode_name in mod_inst.modes
        assert 'description' in mod_inst.modes[mode_name]
        assert mod_inst.modes[mode_name]['description'] == test_def['description']


def add_variable_modification(mod_inst, var_mod_num=1, func_type=func_types.directive):
    var_mod_name = f'variable_{var_mod_num}'
    var_mod_mod = 'test_append'
    var_mod_method = 'append'
    var_mod_mode = 'test_mode'
    var_mod_modes = ['another_mode1', 'another_mode2']

    var_mod_def = {
        'name': var_mod_name,
        'modification': var_mod_mod,
        'method': var_mod_method,
        'mode': var_mod_mode,
        'modes': var_mod_modes.copy(),
    }

    if func_type == func_types.directive:
        variable_modification(var_mod_name, var_mod_mod, var_mod_method,
                              mode=var_mod_mode, modes=var_mod_modes)(mod_inst)
    elif func_type == func_types.method:
        mod_inst.variable_modification(var_mod_name, var_mod_mod, var_mod_method,
                                       mode=var_mod_mode, modes=var_mod_modes)
    else:
        assert False

    return var_mod_def


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_variable_modification_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_variable_modification(mod_inst, func_type=func_type).copy())

    expected_attrs = ['modification', 'method']

    assert hasattr(mod_inst, 'variable_modifications')

    for test_def in test_defs:
        var_name = test_def['name']
        mode_name = test_def['mode']

        assert mode_name in mod_inst.variable_modifications
        assert var_name in mod_inst.variable_modifications[mode_name]
        for attr in expected_attrs:
            assert attr in mod_inst.variable_modifications[mode_name][var_name]
            assert test_def[attr] == mod_inst.variable_modifications[mode_name][var_name][attr]

        for mode_name in test_def['modes']:
            assert mode_name in mod_inst.variable_modifications
            assert var_name in mod_inst.variable_modifications[mode_name]
            for attr in expected_attrs:
                assert attr in mod_inst.variable_modifications[mode_name][var_name]
                assert test_def[attr] == mod_inst.variable_modifications[mode_name][var_name][attr]


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_variable_modification_invalid_method(mod_class, func_type):
    var_mod_name = 'invalid_method_variable'
    var_mod_mod = 'invalid_method_mod'
    var_mod_method = 'invalid'
    var_mod_mode = 'invalid_method_mode'
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')

    with pytest.raises(DirectiveError) as err:
        if func_type == func_types.directive:
            variable_modification(var_mod_name, var_mod_mod,
                                  var_mod_method, mode=var_mod_mode)(mod_inst)
        elif func_type == func_types.method:
            mod_inst.variable_modification(var_mod_name, var_mod_mod,
                                           var_mod_method, mode=var_mod_mode)
        else:
            assert False
        assert 'variable_modification directive given an invalid method' in err


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_variable_modification_missing_mode(mod_class, func_type):
    var_mod_name = 'missing_mode_variable'
    var_mod_mod = 'missing_mode_mod'
    var_mod_method = 'set'
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')

    with pytest.raises(DirectiveError) as err:
        if func_type == func_types.directive:
            variable_modification(var_mod_name, var_mod_mod, var_mod_method)(mod_inst)
        elif func_type == func_types.method:
            mod_inst.variable_modification(var_mod_name, var_mod_mod, var_mod_method)
        assert 'variable_modification directive requires:' in err
        assert 'mode or modes to be defined.' in err


def add_software_spec(mod_inst, spec_num=1, func_type=func_types.directive):
    spec_name = f'SoftwarePackage{spec_num}'
    spack_spec = 'pkg@1.1 target=x86_64'
    compiler_spec = 'pkg@1.1'
    compiler = 'gcc9'

    spec_def = {
        'name': spec_name,
        'spack_spec': spack_spec,
        'compiler_spec': compiler_spec,
        'compiler': compiler
    }

    if func_type == func_types.directive:
        software_spec(spec_name, spack_spec, compiler_spec, compiler)(mod_inst)
    elif func_type == func_types.method:
        mod_inst.software_spec(spec_name, spack_spec, compiler_spec, compiler)
    else:
        assert False

    return spec_def


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_software_spec_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_software_spec(mod_inst, func_type=func_type).copy())

    expected_attrs = ['spack_spec', 'compiler_spec', 'compiler']

    if mod_inst.uses_spack:
        assert hasattr(mod_inst, 'software_specs')

        for test_def in test_defs:
            spec_name = test_def['name']

            assert spec_name in mod_inst.software_specs
            for attr in expected_attrs:
                assert attr in mod_inst.software_specs[spec_name]
                assert test_def[attr] == mod_inst.software_specs[spec_name][attr]


def add_compiler(mod_inst, spec_num=1, func_type=func_types.directive):
    spec_name = f'CompilerPackage{spec_num}'
    spack_spec = 'compiler@1.1 target=x86_64'
    compiler_spec = 'compiler@1.1'
    compiler = None

    spec_def = {
        'name': spec_name,
        'spack_spec': spack_spec,
        'compiler_spec': compiler_spec,
        'compiler': compiler
    }

    if func_type == func_types.directive:
        define_compiler(spec_name, spack_spec, compiler_spec, compiler)(mod_inst)
    elif func_type == func_types.method:
        mod_inst.define_compiler(spec_name, spack_spec, compiler_spec, compiler)
    else:
        assert False

    return spec_def


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_define_compiler_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_compiler(mod_inst, func_type=func_type).copy())

    expected_attrs = ['spack_spec', 'compiler_spec', 'compiler']

    if mod_inst.uses_spack:
        assert hasattr(mod_inst, 'compilers')

        for test_def in test_defs:
            spec_name = test_def['name']

            assert spec_name in mod_inst.compilers
            for attr in expected_attrs:
                assert attr in mod_inst.compilers[spec_name]
                assert test_def[attr] == mod_inst.compilers[spec_name][attr]


def add_required_package(mod_inst, pkg_num=1, func_type=func_types.directive):
    pkg_name = f'RequiredPackage{pkg_num}'

    pkg_def = {
        'name': pkg_name,
    }

    if func_type == func_types.directive:
        required_package(pkg_name)(mod_inst)
    elif func_type == func_types.method:
        mod_inst.required_package(pkg_name)
    else:
        assert False

    return pkg_def


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_required_package_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_required_package(mod_inst, func_type=func_type).copy())

    if mod_inst.uses_spack:
        assert hasattr(mod_inst, 'required_packages')

        for test_def in test_defs:
            pkg_name = test_def['name']

            assert pkg_name in mod_inst.required_packages


def add_figure_of_merit_context(mod_inst, context_num=1, func_type=func_types.directive):
    name = f'FOMContext{context_num}'
    regex = 'test(?P<test>[fom]+)regex'
    output_format = '{test}'

    context_def = {
        'name': name,
        'regex': regex,
        'output_format': output_format,
    }

    if func_type == func_types.directive:
        figure_of_merit_context(name, regex, output_format)(mod_inst)
    elif func_type == func_types.method:
        mod_inst.figure_of_merit_context(name, regex, output_format)

    return context_def


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_figure_of_merit_context_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_figure_of_merit_context(mod_inst, func_type=func_type).copy())

    expected_attrs = ['regex', 'output_format']

    assert hasattr(mod_inst, 'figure_of_merit_contexts')

    for test_def in test_defs:
        name = test_def['name']

        assert name in mod_inst.figure_of_merit_contexts
        for attr in expected_attrs:
            assert attr in mod_inst.figure_of_merit_contexts[name]
            assert test_def[attr] == mod_inst.figure_of_merit_contexts[name][attr]


def add_figure_of_merit(mod_inst, context_num=1, func_type=func_types.directive):
    name = f'FOM{context_num}'
    log_file = '{log_file}'
    fom_regex = 'test(?P<test>[fom]+)regex'
    group_name = 'test'
    units = 'none'
    contexts = ['a', 'b', 'c']

    fom_def = {
        'name': name,
        'log_file': log_file,
        'regex': fom_regex,
        'group_name': group_name,
        'units': units,
        'contexts': contexts.copy(),
    }

    if func_type == func_types.directive:
        figure_of_merit(name, fom_regex=fom_regex, group_name=group_name,
                        units=units, log_file=log_file, contexts=contexts)(mod_inst)
    elif func_type == func_types.method:
        mod_inst.figure_of_merit(name, fom_regex=fom_regex, group_name=group_name,
                                 units=units, log_file=log_file, contexts=contexts)
    else:
        assert False

    return fom_def


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_figure_of_merit_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_figure_of_merit(mod_inst, func_type=func_type).copy())

    expected_attrs = ['log_file', 'regex', 'group_name', 'units', 'contexts']

    assert hasattr(mod_inst, 'figures_of_merit')

    for test_def in test_defs:
        name = test_def['name']

        assert name in mod_inst.figures_of_merit
        for attr in expected_attrs:
            assert attr in mod_inst.figures_of_merit[name]
            assert test_def[attr] == mod_inst.figures_of_merit[name][attr]


def add_archive_pattern(mod_inst, archive_num=1, func_type=func_types.directive):
    pattern = f'my_archive{archive_num}.*'

    if func_type == func_types.directive:
        archive_pattern(pattern)(mod_inst)
    elif func_type == func_types.method:
        mod_inst.archive_pattern(pattern)
    else:
        assert False

    return pattern


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_archive_pattern_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_archive_pattern(mod_inst, func_type=func_type))

    assert hasattr(mod_inst, 'archive_patterns')

    for test_def in test_defs:
        pattern = test_def

        assert pattern in mod_inst.archive_patterns
        assert pattern == mod_inst.archive_patterns[pattern]


def add_executable_modifier(mod_inst, exec_mod_num=1, func_type=func_types.directive):
    mod_name = f'exec_mod{exec_mod_num}'

    if func_type == func_type.directive:
        executable_modifier(mod_name)(mod_inst)
    elif func_type == func_type.method:
        mod_inst.executable_modifier(mod_name)
    else:
        assert False

    return mod_name


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_executable_modifier_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_executable_modifier(mod_inst, func_type))

    assert hasattr(mod_inst, 'executable_modifiers')

    for test_def in test_defs:
        mod_name = test_def

        assert mod_name in mod_inst.executable_modifiers
        assert mod_name == mod_inst.executable_modifiers[mod_name]


def add_env_var_modification(mod_inst, env_var_mod_num=1, func_type=func_types.directive):
    mod_name = f'env_var_mod_{env_var_mod_num}'
    mod_val = f'value_{env_var_mod_num}'
    mod_method = 'set'
    mod_mode = 'env_var_mod_mode'

    test_defs = {
        'name': mod_name,
        'modification': mod_val,
        'method': mod_method,
        'mode': mod_mode
    }

    if func_type == func_types.directive:
        env_var_modification(mod_name, mod_val, mode=mod_mode)(mod_inst)
    elif func_type == func_types.method:
        mod_inst.env_var_modification(mod_name, mod_val, mode=mod_mode)
    else:
        assert False

    return test_defs


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_env_var_modification_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_env_var_modification(mod_inst, func_type))

    assert hasattr(mod_inst, 'env_var_modifications')

    for test_def in test_defs:
        method = test_def['method']
        mode = test_def['mode']

        assert method in mod_inst.env_var_modifications[mode]
        if method == 'set':
            assert test_def['name'] in mod_inst.env_var_modifications[mode][method]
            assert test_def['modification'] == \
                mod_inst.env_var_modifications[mode][method][test_def['name']]


def add_modifier_variable(mod_inst, mod_var_num=1, func_type=func_types.directive):
    var_name = f'mod_var_{mod_var_num}'
    var_default = f'default_{mod_var_num}'
    var_desc = f'Test variable {mod_var_num}'
    var_mode = 'mod_var_mode'

    test_defs = {
        'name': var_name,
        'default': var_default,
        'description': var_desc,
        'mode': var_mode
    }

    if func_type == func_types.directive:
        modifier_variable(var_name, default=var_default, description=var_desc,
                          mode=var_mode)(mod_inst)
    elif func_type == func_types.method:
        mod_inst.modifier_variable(var_name, default=var_default, description=var_desc,
                                   mode=var_mode)
    else:
        assert False

    return test_defs


@pytest.mark.parametrize('func_type', func_types)
@pytest.mark.parametrize('mod_class', mod_types)
def test_modifier_variable_directive(mod_class, func_type):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_modifier_variable(mod_inst, func_type))

    assert hasattr(mod_inst, 'modifier_variables')

    for test_def in test_defs:
        mode = test_def['mode']
        var_name = test_def['name']

        assert mode in mod_inst.modifier_variables
        assert test_def['name'] in mod_inst.modifier_variables[mode]
        for attr in ['description', 'default']:
            assert test_def[attr] == mod_inst.modifier_variables[mode][var_name][attr]
