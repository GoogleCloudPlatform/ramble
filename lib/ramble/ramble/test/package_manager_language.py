# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the package manager class"""

import pytest

from ramble.pkgmankit import *  # noqa


pm_types = [
    PackageManagerBase,  # noqa: F405
]


@pytest.mark.parametrize("pm_class", pm_types)
def test_pkg_man_type_features(pm_class):
    pm_path = "/path/to/pm"
    test_pm = pm_class(pm_path)
    assert hasattr(test_pm, "package_manager_variable")
    assert hasattr(test_pm, "maintainers")


def add_variable(pm_inst, pm_num=1):
    var_name = f"TestVariable{pm_num}"
    var_default = f"DefaultValue{pm_num}"
    var_description = f"Description{pm_num}"

    pm_inst.package_manager_variable(var_name, default=var_default, description=var_description)

    var_def = {"name": var_name, "default": var_default, "description": var_description}

    return var_def


@pytest.mark.parametrize("pm_class", pm_types)
def test_pkg_man_variables(pm_class):
    test_defs = {}

    pm_inst = pm_class("/not/a/path")
    test_defs.update(add_variable(pm_inst))

    var_name = test_defs["name"]

    assert hasattr(pm_inst, "package_manager_variables")
    assert var_name in pm_inst.package_manager_variables
    assert pm_inst.package_manager_variables[var_name].default is not None
    assert pm_inst.package_manager_variables[var_name].default == test_defs["default"]
    assert pm_inst.package_manager_variables[var_name].description is not None
    assert pm_inst.package_manager_variables[var_name].description == test_defs["description"]
