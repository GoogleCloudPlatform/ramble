# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the Application class"""

import pytest

from ramble.modkit import *  # noqa
from ramble.language.language_base import DirectiveError


mod_types = [
    ModifierBase,  # noqa: F405
    BasicModifier,  # noqa: F405
    SpackModifier  # noqa: F405
]


def generate_mod_class(base_class):

    class GeneratedClass(base_class):

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
    assert hasattr(test_mod, 'default_compilers')
    assert hasattr(test_mod, 'required_packages')
    assert hasattr(test_mod, 'success_criteria')
    assert hasattr(test_mod, 'builtins')
    assert hasattr(test_mod, 'executable_modifiers')
    assert hasattr(test_mod, 'env_var_modifications')
    assert hasattr(test_mod, 'maintainers')


def add_mode(mod_inst, mode_num=1):
    mode_name = 'TestMode%s' % mode_num
    mode_desc = 'This is a test mode'

    mode(mode_name, description=mode_desc)(mod_inst)  # noqa: F405

    mode_def = {
        'name': mode_name,
        'description': mode_desc
    }

    return mode_def


@pytest.mark.parametrize('mod_class', mod_types)
def test_mode_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_mode(mod_inst).copy())

    assert hasattr(mod_inst, 'modes')
    for test_def in test_defs:
        mode_name = test_def['name']
        assert mode_name in mod_inst.modes
        assert 'description' in mod_inst.modes[mode_name]
        assert mod_inst.modes[mode_name]['description'] == test_def['description']


def add_variable_modification(mod_inst, var_mod_num=1):
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

    variable_modification(var_mod_name, var_mod_mod, var_mod_method,
                          mode=var_mod_mode, modes=var_mod_modes)(mod_inst)

    return var_mod_def


@pytest.mark.parametrize('mod_class', mod_types)
def test_variable_modification_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_variable_modification(mod_inst).copy())

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


@pytest.mark.parametrize('mod_class', mod_types)
def test_variable_modification_invalid_method(mod_class):
    var_mod_name = 'invalid_method_variable'
    var_mod_mod = 'invalid_method_mod'
    var_mod_method = 'invalid'
    var_mod_mode = 'invalid_method_mode'
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')

    with pytest.raises(DirectiveError) as err:
        variable_modification(var_mod_name, var_mod_mod,
                              var_mod_method, mode=var_mod_mode)(mod_inst)
        assert 'variable_modification directive given an invalid method' in err


@pytest.mark.parametrize('mod_class', mod_types)
def test_variable_modification_missing_mode(mod_class):
    var_mod_name = 'missing_mode_variable'
    var_mod_mod = 'missing_mode_mod'
    var_mod_method = 'set'
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')

    with pytest.raises(DirectiveError) as err:
        variable_modification(var_mod_name, var_mod_mod, var_mod_method)(mod_inst)
        assert 'variable_modification directive requires:' in err
        assert 'mode or modes to be defined.' in err


def add_software_spec(mod_inst, spec_num=1):
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

    software_spec(spec_name, spack_spec, compiler_spec, compiler)(mod_inst)

    return spec_def


@pytest.mark.parametrize('mod_class', mod_types)
def test_software_spec_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_software_spec(mod_inst).copy())

    expected_attrs = ['spack_spec', 'compiler_spec', 'compiler']

    if mod_inst.uses_spack:
        assert hasattr(mod_inst, 'software_specs')

        for test_def in test_defs:
            spec_name = test_def['name']

            assert spec_name in mod_inst.software_specs
            for attr in expected_attrs:
                assert attr in mod_inst.software_specs[spec_name]
                assert test_def[attr] == mod_inst.software_specs[spec_name][attr]


def add_default_compiler(mod_inst, spec_num=1):
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

    default_compiler(spec_name, spack_spec, compiler_spec, compiler)(mod_inst)

    return spec_def


@pytest.mark.parametrize('mod_class', mod_types)
def test_default_compiler_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_default_compiler(mod_inst).copy())

    expected_attrs = ['spack_spec', 'compiler_spec', 'compiler']

    if mod_inst.uses_spack:
        assert hasattr(mod_inst, 'default_compilers')

        for test_def in test_defs:
            spec_name = test_def['name']

            assert spec_name in mod_inst.default_compilers
            for attr in expected_attrs:
                assert attr in mod_inst.default_compilers[spec_name]
                assert test_def[attr] == mod_inst.default_compilers[spec_name][attr]


def add_required_package(mod_inst, pkg_num=1):
    pkg_name = f'RequiredPackage{pkg_num}'

    pkg_def = {
        'name': pkg_name,
    }

    required_package(pkg_name)(mod_inst)

    return pkg_def


@pytest.mark.parametrize('mod_class', mod_types)
def test_required_package_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_required_package(mod_inst).copy())

    if mod_inst.uses_spack:
        assert hasattr(mod_inst, 'required_packages')

        for test_def in test_defs:
            pkg_name = test_def['name']

            assert pkg_name in mod_inst.required_packages


def add_figure_of_merit_context(mod_inst, context_num=1):
    name = f'FOMContext{context_num}'
    regex = 'test(?P<test>[fom]+)regex'
    output_format = '{test}'

    context_def = {
        'name': name,
        'regex': regex,
        'output_format': output_format,
    }

    figure_of_merit_context(name, regex, output_format)(mod_inst)

    return context_def


@pytest.mark.parametrize('mod_class', mod_types)
def test_figure_of_merit_context_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_figure_of_merit_context(mod_inst).copy())

    expected_attrs = ['regex', 'output_format']

    assert hasattr(mod_inst, 'figure_of_merit_contexts')

    for test_def in test_defs:
        name = test_def['name']

        assert name in mod_inst.figure_of_merit_contexts
        for attr in expected_attrs:
            assert attr in mod_inst.figure_of_merit_contexts[name]
            assert test_def[attr] == mod_inst.figure_of_merit_contexts[name][attr]


def add_figure_of_merit(mod_inst, context_num=1):
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

    figure_of_merit(name, fom_regex=fom_regex, group_name=group_name,
                    units=units, log_file=log_file, contexts=contexts)(mod_inst)

    return fom_def


@pytest.mark.parametrize('mod_class', mod_types)
def test_figure_of_merit_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_figure_of_merit(mod_inst).copy())

    expected_attrs = ['log_file', 'regex', 'group_name', 'units', 'contexts']

    assert hasattr(mod_inst, 'figures_of_merit')

    for test_def in test_defs:
        name = test_def['name']

        assert name in mod_inst.figures_of_merit
        for attr in expected_attrs:
            assert attr in mod_inst.figures_of_merit[name]
            assert test_def[attr] == mod_inst.figures_of_merit[name][attr]


def add_archive_pattern(mod_inst, archive_num=1):
    pattern = f'my_archive{archive_num}.*'

    archive_pattern(pattern)(mod_inst)

    return pattern


@pytest.mark.parametrize('mod_class', mod_types)
def test_archive_pattern_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_archive_pattern(mod_inst))

    assert hasattr(mod_inst, 'archive_patterns')

    for test_def in test_defs:
        pattern = test_def

        assert pattern in mod_inst.archive_patterns
        assert pattern == mod_inst.archive_patterns[pattern]


def add_executable_modifier(mod_inst, exec_mod_num=1):
    mod_name = f'exec_mod{exec_mod_num}'

    executable_modifier(mod_name)(mod_inst)

    return mod_name


@pytest.mark.parametrize('mod_class', mod_types)
def test_executable_modifier_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_executable_modifier(mod_inst))

    assert hasattr(mod_inst, 'executable_modifiers')

    for test_def in test_defs:
        mod_name = test_def

        assert mod_name in mod_inst.executable_modifiers
        assert mod_name == mod_inst.executable_modifiers[mod_name]


def add_env_var_modification(mod_inst, env_var_mod_num=1):
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

    env_var_modification(mod_name, mod_val, mode=mod_mode)(mod_inst)

    return test_defs


@pytest.mark.parametrize('mod_class', mod_types)
def test_env_var_modification_directive(mod_class):
    test_class = generate_mod_class(mod_class)
    mod_inst = test_class('/not/a/path')
    test_defs = []
    test_defs.append(add_env_var_modification(mod_inst))

    assert hasattr(mod_inst, 'env_var_modifications')

    for test_def in test_defs:
        method = test_def['method']
        mode = test_def['mode']

        assert method in mod_inst.env_var_modifications[mode]
        if method == 'set':
            assert test_def['name'] in mod_inst.env_var_modifications[mode][method]
            assert test_def['modification'] == \
                mod_inst.env_var_modifications[mode][method][test_def['name']]
