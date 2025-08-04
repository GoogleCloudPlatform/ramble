# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.test.application import basic_exp_dict

_FS = frozenset()


def test_basic_inheritance(mutable_mock_apps_repo):
    app_inst = mutable_mock_apps_repo.get("basic-inherited")
    exp_dict = basic_exp_dict()
    app_inst.set_variables_and_variants(exp_dict, {}, None)
    app_inst.define_variable("application_name", "basic-inherited")

    assert "foo" in app_inst.executables[_FS]
    assert app_inst.executables[_FS]["foo"].template == ["bar"]
    assert not app_inst.executables[_FS]["foo"].mpi
    assert "bar" in app_inst.executables[_FS]
    assert app_inst.executables[_FS]["bar"].template == ["baz"]
    assert app_inst.executables[_FS]["bar"].mpi

    assert "test_wl" in app_inst.workloads[_FS]
    assert app_inst.workloads[_FS]["test_wl"].executables == ["foo"]
    assert app_inst.workloads[_FS]["test_wl"].inputs == ["input"]

    app_inst.define_variable("workload_name", "test_wl")
    exec_graph = app_inst._get_executable_graph("test_wl")
    assert exec_graph.get_node("foo") is not None
    assert exec_graph.get_node("builtin::env_vars") is not None

    assert "test_wl2" in app_inst.workloads[_FS]
    assert app_inst.workloads[_FS]["test_wl2"].executables == ["bar"]
    assert app_inst.workloads[_FS]["test_wl2"].inputs == ["input"]

    app_inst.define_variable("workload_name", "test_wl2")
    exec_graph = app_inst._get_executable_graph("test_wl2")
    assert exec_graph.get_node("bar") is not None
    assert exec_graph.get_node("builtin::env_vars") is not None

    assert "test_wl3" in app_inst.workloads[_FS]
    assert app_inst.workloads[_FS]["test_wl3"].executables == ["foo"]
    assert app_inst.workloads[_FS]["test_wl3"].inputs == ["inherited_input"]

    app_inst.define_variable("workload_name", "test_wl3")
    exec_graph = app_inst._get_executable_graph("test_wl3")
    assert exec_graph.get_node("foo") is not None
    assert exec_graph.get_node("builtin::env_vars") is not None

    assert "test_fom" in app_inst.figures_of_merit[_FS][_FS]
    fom_conf = app_inst.figures_of_merit[_FS][_FS]["test_fom"]
    assert fom_conf["log_file"] == "{log_file}"
    assert fom_conf["regex"] == r"(?P<test>[0-9]+\.[0-9]+).*seconds.*"
    assert fom_conf["group_name"] == "test"
    assert fom_conf["units"] == "s"

    assert "input" in app_inst.inputs[_FS]
    assert app_inst.inputs[_FS]["input"]["url"] == "file:///tmp/test_file.log"
    assert app_inst.inputs[_FS]["input"]["description"] == "Not a file"
    assert "inherited_input" in app_inst.inputs[_FS]
    assert app_inst.inputs[_FS]["inherited_input"]["url"] == "file:///tmp/inherited_file.log"
    assert app_inst.inputs[_FS]["inherited_input"]["description"] == "Again, not a file"

    possible_vars = app_inst.workloads[_FS]["test_wl"].find_variable("my_base_var")
    assert len(possible_vars) == 1
    possible_vars = app_inst.workloads[_FS]["test_wl"].find_variable("my_var")
    assert len(possible_vars) >= 1
    found = False
    for var in possible_vars:
        if "Shadowed" in var.description and var.default == "1.0":
            found = True
    assert found

    assert app_inst.license_names == ["basic", "basic-inherited-extended", "basic-inherited"]
