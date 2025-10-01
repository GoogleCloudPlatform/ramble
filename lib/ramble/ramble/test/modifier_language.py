# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the Application class"""

import deprecation
import pytest

import ramble.language.language_helpers
from ramble.language.language_base import DirectiveError
from ramble.modkit import *  # noqa

mod_types = [ModifierBase, BasicModifier]  # noqa: F405

_FS = frozenset()


@deprecation.fail_if_not_removed
@pytest.mark.parametrize("mod_class", mod_types)
def test_modifier_type_features(mod_class):
    mod_path = "/path/to/mod"
    test_mod = mod_class(mod_path)
    assert hasattr(test_mod, "figure_of_merit_contexts")
    assert hasattr(test_mod, "archive_patterns")
    assert hasattr(test_mod, "figures_of_merit")
    assert hasattr(test_mod, "modes")
    assert hasattr(test_mod, "variable_modifications")
    assert hasattr(test_mod, "software_specs")
    assert hasattr(test_mod, "compilers")
    assert hasattr(test_mod, "required_packages")
    assert hasattr(test_mod, "success_criteria")
    assert hasattr(test_mod, "builtins")
    assert hasattr(test_mod, "executable_modifiers")
    assert hasattr(test_mod, "env_var_modifications")
    assert hasattr(test_mod, "maintainers")
    assert hasattr(test_mod, "package_manager_configs")


def add_mode(mod_inst, mode_num=1):
    mode_name = "TestMode%s" % mode_num
    mode_desc = "This is a test mode"

    mod_inst.mode(mode_name, description=mode_desc)

    mode_def = {"name": mode_name, "description": mode_desc}

    return mode_def


@pytest.mark.parametrize("mod_class", mod_types)
def test_mode_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_mode(mod_inst).copy())

    assert hasattr(mod_inst, "modes")
    for test_def in test_defs:
        mode_name = test_def["name"]
        assert mode_name in mod_inst.modes
        assert "description" in mod_inst.modes[mode_name]
        assert mod_inst.modes[mode_name]["description"] == test_def["description"]


def add_variable_modification(mod_inst, var_mod_num=1):
    var_mod_name = f"variable_{var_mod_num}"
    var_mod_mod = "test_append"
    var_mod_method = "append"
    var_mod_mode = "test_mode"
    var_mod_modes = ["another_mode1", "another_mode2"]

    var_mod_def = {
        "name": var_mod_name,
        "modification": var_mod_mod,
        "method": var_mod_method,
        "mode": var_mod_mode,
        "modes": var_mod_modes.copy(),
    }

    mod_inst.variable_modification(
        var_mod_name, var_mod_mod, var_mod_method, mode=var_mod_mode, modes=var_mod_modes
    )

    return var_mod_def


@pytest.mark.parametrize("mod_class", mod_types)
def test_variable_modification_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_variable_modification(mod_inst).copy())
    test_defs.append(add_variable_modification(mod_inst, 2).copy())
    test_defs.append(add_variable_modification(mod_inst).copy())

    expected_attrs = ["modification", "method"]

    assert hasattr(mod_inst, "variable_modifications")

    when_conditions = 0
    mod_count = 0
    for when_set, var_mod_dict in mod_inst.variable_modifications.items():
        when_conditions += len(when_set)
        for var_name in mod_inst.variable_modifications[when_set]:
            for modification in mod_inst.variable_modifications[when_set][var_name]:
                mod_count += 1
    assert mod_count == 3  # Each call to add_variable_modification adds 1 variable modification
    assert when_conditions == 3  # Each modification applies in 3 modes, stored as when conditions

    for test_def in test_defs:
        var_name = test_def["name"]
        mode_name = test_def["mode"]
        mode_when = f"{mod_inst.name}_mode={mode_name}"

        for when_set, var_mod_dict in mod_inst.variable_modifications.items():
            assert mode_when in when_set
            assert var_name in mod_inst.variable_modifications[when_set]
            found_match = (
                False if len(mod_inst.variable_modifications[when_set][var_name]) > 0 else True
            )
            for modification in mod_inst.variable_modifications[when_set][var_name]:
                match = True
                for attr in expected_attrs:
                    assert getattr(modification, attr) is not None
                    if test_def[attr] != getattr(modification, attr):
                        match = False
                if match:
                    found_match = True
            assert found_match

        for mode_name in test_def["modes"]:
            mode_when = f"{mod_inst.name}_mode={mode_name}"

            for when_set, var_mod_dict in mod_inst.variable_modifications.items():
                found_match = (
                    False if len(mod_inst.variable_modifications[when_set][var_name]) > 0 else True
                )
                assert mode_when in when_set
                assert var_name in mod_inst.variable_modifications[when_set]
                for modification in mod_inst.variable_modifications[when_set][var_name]:
                    match = True
                    for attr in expected_attrs:
                        assert getattr(modification, attr) is not None
                        if test_def[attr] != getattr(modification, attr):
                            match = False
                    if match:
                        found_match = True
                assert found_match


@pytest.mark.parametrize("mod_class", mod_types)
def test_variable_modification_invalid_method(mod_class):
    var_mod_name = "invalid_method_variable"
    var_mod_mod = "invalid_method_mod"
    var_mod_method = "invalid"
    var_mod_mode = "invalid_method_mode"

    with pytest.raises(
        DirectiveError, match="variable_modification directive given an invalid method"
    ):
        mod_inst = mod_class("/not/a/path")
        mod_inst.variable_modification(
            var_mod_name, var_mod_mod, var_mod_method, mode=var_mod_mode
        )


@pytest.mark.parametrize("mod_class", mod_types)
def test_variable_modification_missing_mode_or_when(mod_class):
    var_mod_name = "missing_mode_variable"
    var_mod_mod = "missing_mode_mod"
    var_mod_method = "set"

    with pytest.raises(DirectiveError, match="mode or modes or when to be defined"):
        mod_inst = mod_class("/not/a/path")
        mod_inst.variable_modification(var_mod_name, var_mod_mod, var_mod_method)


def add_software_spec(mod_inst, spec_num=1):
    spec_name = f"SoftwarePackage{spec_num}"
    pkg_spec = "pkg@1.1 target=x86_64"
    compiler_spec = "pkg@1.1"
    compiler = "gcc9"

    spec_def = {
        "name": spec_name,
        "pkg_spec": pkg_spec,
        "compiler_spec": compiler_spec,
        "compiler": compiler,
    }

    mod_inst.software_spec(spec_name, pkg_spec, compiler_spec, compiler)

    return spec_def


@pytest.mark.parametrize("mod_class", mod_types)
def test_software_spec_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_software_spec(mod_inst).copy())

    expected_attrs = ["pkg_spec", "compiler_spec", "compiler"]

    assert hasattr(mod_inst, "software_specs")

    for test_def in test_defs:
        spec_name = test_def["name"]

        assert spec_name in mod_inst.software_specs
        for attr in expected_attrs:
            assert hasattr(mod_inst.software_specs[spec_name][0], attr)
            assert test_def[attr] == getattr(mod_inst.software_specs[spec_name][0], attr)


def add_compiler(mod_inst, spec_num=1):
    spec_name = f"CompilerPackage{spec_num}"
    pkg_spec = "compiler@1.1 target=x86_64"
    compiler_spec = "compiler@1.1"
    compiler = None

    spec_def = {
        "name": spec_name,
        "pkg_spec": pkg_spec,
        "compiler_spec": compiler_spec,
        "compiler": compiler,
    }

    mod_inst.define_compiler(spec_name, pkg_spec, compiler_spec, compiler)

    return spec_def


@pytest.mark.parametrize("mod_class", mod_types)
def test_define_compiler_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_compiler(mod_inst).copy())

    expected_attrs = ["pkg_spec", "compiler_spec", "compiler"]

    assert hasattr(mod_inst, "compilers")

    for test_def in test_defs:
        spec_name = test_def["name"]

        assert spec_name in mod_inst.compilers
        for attr in expected_attrs:
            assert hasattr(mod_inst.compilers[spec_name][0], attr)
            assert test_def[attr] == getattr(mod_inst.compilers[spec_name][0], attr)


def add_required_package(mod_inst, pkg_num=1):
    pkg_name = f"RequiredPackage{pkg_num}"

    pkg_def = {
        "name": pkg_name,
    }

    mod_inst.required_package(pkg_name)

    return pkg_def


@pytest.mark.parametrize("mod_class", mod_types)
def test_required_package_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_required_package(mod_inst).copy())

    assert hasattr(mod_inst, "required_packages")

    for test_def in test_defs:
        pkg_name = test_def["name"]

        assert pkg_name in mod_inst.required_packages


def add_figure_of_merit_context(mod_inst, context_num=1):
    name = f"FOMContext{context_num}"
    regex = "test(?P<test>[fom]+)regex"
    output_format = "{test}"

    context_def = {
        "name": name,
        "regex": regex,
        "output_format": output_format,
    }

    mod_inst.figure_of_merit_context(name, regex, output_format)

    return context_def


@pytest.mark.parametrize("mod_class", mod_types)
def test_figure_of_merit_context_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_figure_of_merit_context(mod_inst).copy())

    expected_attrs = ["regex", "output_format"]

    assert hasattr(mod_inst, "figure_of_merit_contexts")

    for test_def in test_defs:
        name = test_def["name"]

        assert name in mod_inst.figure_of_merit_contexts[_FS]
        for attr in expected_attrs:
            assert attr in mod_inst.figure_of_merit_contexts[_FS][name]
            assert test_def[attr] == mod_inst.figure_of_merit_contexts[_FS][name][attr]


def add_figure_of_merit(mod_inst, context_num=1):
    name = f"FOM{context_num}"
    log_file = "{log_file}"
    fom_regex = "test(?P<test>[fom]+)regex"
    group_name = "test"
    units = "none"
    contexts = ["a", "b", "c"]

    fom_def = {
        "name": name,
        "log_file": log_file,
        "regex": fom_regex,
        "group_name": group_name,
        "units": units,
        "contexts": contexts.copy(),
    }

    for context in contexts:
        mod_inst.figure_of_merit(
            name,
            fom_regex=fom_regex,
            group_name=group_name,
            units=units,
            log_file=log_file,
            contexts=contexts,
        )

    return fom_def


@pytest.mark.parametrize("mod_class", mod_types)
def test_figure_of_merit_directive(mod_class):
    test_defs = []

    _FS = frozenset()

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_figure_of_merit(mod_inst).copy())

    expected_attrs = ["log_file", "regex", "group_name", "units", "contexts"]

    assert hasattr(mod_inst, "figures_of_merit")

    for test_def in test_defs:
        name = test_def["name"]
        context_key = frozenset(test_def["contexts"])

        assert name in mod_inst.figures_of_merit[_FS][context_key]
        for attr in expected_attrs:
            assert attr in mod_inst.figures_of_merit[_FS][context_key][name]
            assert test_def[attr] == mod_inst.figures_of_merit[_FS][context_key][name][attr]


def add_archive_pattern(mod_inst, archive_num=1):
    pattern = f"my_archive{archive_num}.*"

    mod_inst.archive_pattern(pattern)

    return pattern


@pytest.mark.parametrize("mod_class", mod_types)
def test_archive_pattern_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_archive_pattern(mod_inst))

    assert hasattr(mod_inst, "archive_patterns")

    for test_def in test_defs:
        pattern = test_def

        assert pattern in mod_inst.archive_patterns
        assert pattern == mod_inst.archive_patterns[pattern]


def add_executable_modifier(mod_inst, exec_mod_num=1):
    mod_name = f"exec_mod{exec_mod_num}"

    mod_inst.executable_modifier(mod_name)

    return mod_name


@pytest.mark.parametrize("mod_class", mod_types)
def test_executable_modifier_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_executable_modifier(mod_inst))

    assert hasattr(mod_inst, "executable_modifiers")

    for test_def in test_defs:
        mod_name = test_def

        assert mod_name in mod_inst.executable_modifiers[frozenset()]


def add_env_var_modification(mod_inst, env_var_mod_num=1):
    mod_name = f"env_var_mod_{env_var_mod_num}"
    mod_val = f"value_{env_var_mod_num}"
    mod_method = "set"
    mod_mode = "env_var_mod_mode"

    test_defs = {"name": mod_name, "modification": mod_val, "method": mod_method, "mode": mod_mode}

    mod_inst.env_var_modification(mod_name, mod_val, mode=mod_mode)

    return test_defs


@pytest.mark.parametrize("mod_class", mod_types)
def test_env_var_modification_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    test_defs.append(add_env_var_modification(mod_inst))

    assert hasattr(mod_inst, "env_var_modifications")

    for test_def in test_defs:
        mode = test_def["mode"]
        name = test_def["name"]

        mode_when = frozenset([f"{mod_inst.name}_mode={mode}"])

        assert name in mod_inst.env_var_modifications[mode_when]
        env_var_mod = mod_inst.env_var_modifications[mode_when][name]
        assert test_def["modification"] == env_var_mod.set[name]


def add_modifier_variable(mod_inst, mod_var_num=1):
    var_name = f"mod_var_{mod_var_num}"
    var_default = f"default_{mod_var_num}"
    var_desc = f"Test variable {mod_var_num}"
    var_mode = "mod_var_mode"

    test_defs = {
        "name": var_name,
        "default": var_default,
        "description": var_desc,
        "mode": var_mode,
    }

    mod_inst.modifier_variable(var_name, default=var_default, description=var_desc, mode=var_mode)

    return test_defs


@pytest.mark.parametrize("mod_class", mod_types)
def test_modifier_variable_directive(mod_class):
    test_defs = []

    mod_inst = mod_class("/not/a/path")
    mod_inst.name = "mock-test-mod"
    test_defs.append(add_modifier_variable(mod_inst))

    for test_def in test_defs:
        found = False

        for when_set, var_list in mod_inst.object_variables.items():
            for var in var_list:
                if var.name == test_def["name"]:
                    mode_variant = f"mock-test-mod_mode={test_def['mode']}"
                    assert mode_variant in when_set
                    assert test_def["description"] == var.description
                    assert test_def["default"] == var.default
                    found = True
        assert found


@pytest.mark.parametrize("mod_class", mod_types)
def test_modifier_class_attributes(mod_class):
    mod_inst = mod_class("/not/a/path")
    mod_copy = mod_inst.copy()

    mod_copy.mode("added_mode", description="Mode added to test attributes")

    assert "added_mode" in mod_copy.modes
    assert "added_mode" not in mod_inst.modes


@pytest.mark.parametrize("mod_class", mod_types)
def test_require_condition_creates_when_list(mod_class):
    mod_inst = mod_class("/not/a/path")
    mod_inst.name = "test-mod"
    for i in range(4):
        mod_inst.mode(f"mode_{i}", description="mode")

    when_list = ramble.language.language_helpers.require_condition(
        mod_inst,
        "test_require_condition",
        "mode",
        "modes",
        mode="mode_0",
        modes=["mode_1", "mode_2"],
        when=["test-mod_mode=mode_3"],
    )

    for i in range(4):
        assert f"test-mod_mode=mode_{i}" in when_list
