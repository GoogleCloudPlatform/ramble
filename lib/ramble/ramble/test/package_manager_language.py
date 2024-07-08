# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the package manager class"""

import pytest
import enum

from ramble.pkgmankit import *  # noqa


pm_types = [
    PackageManagerBase,  # noqa: F405
]

func_types = enum.Enum("func_types", ["method", "directive"])


def generate_pkg_man_class(base_class):

    class GeneratedClass(base_class):
        _language_classes = base_class._language_classes.copy()

        def __init__(self, file_path):
            super().__init__(file_path)

    return GeneratedClass


@pytest.mark.parametrize("base_class", pm_types)
def test_pkg_man_type_features(base_class):
    pm_path = "/path/to/pm"
    pm_class = generate_pkg_man_class(base_class)
    test_pm = pm_class(pm_path)
    assert hasattr(test_pm, "package_manager_variable")
    assert hasattr(test_pm, "maintainers")


def add_variable(pm_inst, pm_num=1, func_type=func_types.directive):
    var_name = f"TestVariable{pm_num}"
    var_default = f"DefaultValue{pm_num}"
    var_description = f"Description{pm_num}"

    if func_type == func_types.directive:
        package_manager_variable(var_name, default=var_default, description=var_description)(
            pm_inst
        )
    elif func_type == func_types.method:
        pm_inst.package_manager_variable(
            var_name, default=var_default, description=var_description
        )
    else:
        return False

    var_def = {"name": var_name, "default": var_default, "description": var_description}

    return var_def


@pytest.mark.parametrize("func_type", func_types)
@pytest.mark.parametrize("base_class", pm_types)
def test_pkg_man_variables(base_class, func_type):
    pm_class = generate_pkg_man_class(base_class)
    pm_inst = pm_class("/not/a/path")
    test_defs = {}
    test_defs.update(add_variable(pm_inst, func_type=func_type))

    var_name = test_defs["name"]

    assert hasattr(pm_inst, "package_manager_variables")
    assert var_name in pm_inst.package_manager_variables
    assert pm_inst.package_manager_variables[var_name].default is not None
    assert pm_inst.package_manager_variables[var_name].default == test_defs["default"]
    assert pm_inst.package_manager_variables[var_name].description is not None
    assert pm_inst.package_manager_variables[var_name].description == test_defs["description"]
