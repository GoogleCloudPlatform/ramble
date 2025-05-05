# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the util/naming functions"""

import pytest

from ramble.util import naming


@pytest.mark.parametrize(
    "mod_name,expected_cls_name",
    [
        ("test_mod_1", "TestMod1"),
        ("2_test_mod", "_2TestMod"),
    ],
)
def test_mod_to_class(mod_name, expected_cls_name):
    assert naming.mod_to_class(mod_name) == expected_cls_name


@pytest.mark.parametrize(
    "mod_name,expected_py_mod_name",
    [
        ("app", "app"),
        ("intel-mlc", "intel_mlc"),
        ("1-app", "num1_app"),
    ],
)
def test_ramble_module_to_python_module(mod_name, expected_py_mod_name):
    assert naming.ramble_module_to_python_module(mod_name) == expected_py_mod_name


@pytest.mark.parametrize(
    "py_mod_name,expected_names",
    [
        ("app", ["app"]),
        ("py_mod", ["py_mod", "py-mod"]),
        ("num1_app", ["1_app", "1-app"]),
    ],
)
def test_possible_ramble_module_names(py_mod_name, expected_names):
    assert naming.possible_ramble_module_names(py_mod_name) == expected_names


@pytest.mark.parametrize(
    "in_name,expected_out_name",
    [
        ("ImageMagick", "imagemagick"),
        ("l_mkl", "mkl"),
        ("ALLCAPS", "allcaps"),
        ("a_b.c++", "a-b-cpp"),
    ],
)
def test_simplify_name(in_name, expected_out_name):
    assert naming.simplify_name(in_name) == expected_out_name


@pytest.mark.parametrize(
    "mod_name,expect_error",
    [
        ("valid-mod", False),
        ("a.b", True),
        ("-ab", True),
    ],
)
def test_validate_module_name(mod_name, expect_error):
    if expect_error:
        with pytest.raises(naming.InvalidModuleNameError):
            naming.validate_module_name(mod_name)
    else:
        naming.validate_module_name(mod_name)


@pytest.mark.parametrize(
    "mod_name,expect_error",
    [
        ("valid-mod", False),
        ("a.b", False),
        ("-ab", True),
        ("valid-mod.a.b-c", False),
    ],
)
def test_validate_fully_qualified_module_name(mod_name, expect_error):
    if expect_error:
        with pytest.raises(naming.InvalidFullyQualifiedModuleNameError):
            naming.validate_fully_qualified_module_name(mod_name)
    else:
        naming.validate_fully_qualified_module_name(mod_name)
