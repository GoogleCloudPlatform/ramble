# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Perform tests of the Application class"""

from typing import FrozenSet

import deprecation
import pytest

from ramble.appkit import *  # noqa
from ramble.error import DirectiveError

app_types = [
    ApplicationBase,  # noqa: F405
    ExecutableApplication,  # noqa: F405
]

_FS: FrozenSet[str] = frozenset()


@deprecation.fail_if_not_removed
@pytest.mark.parametrize("app_class", app_types)
def test_application_type_features(app_class):
    app_path = "/path/to/app"
    test_app = app_class(app_path)
    assert hasattr(test_app, "workloads")
    assert hasattr(test_app, "executables")
    assert hasattr(test_app, "figures_of_merit")
    assert hasattr(test_app, "inputs")
    assert hasattr(test_app, "compilers")
    assert hasattr(test_app, "software_specs")
    assert hasattr(test_app, "required_packages")
    assert hasattr(test_app, "maintainers")
    assert hasattr(test_app, "license_names")
    assert hasattr(test_app, "package_manager_configs")


def add_workload(app_inst, wl_num=1):
    wl_name = f"TestWorkload{wl_num}"
    exec_list = [f"Workload{wl_num}Exec1"]
    exec_var = f"Workload{wl_num}Exec2"
    inpt_list = [f"Workload{wl_num}Input1"]
    inpt_var = f"Workload{wl_num}Input2"

    app_inst.workload(
        wl_name,
        executables=exec_list,
        executable=exec_var,
        inputs=inpt_list,
        input=inpt_var,
    )

    workload_def = {"name": wl_name, "executables": exec_list.copy(), "inputs": inpt_list.copy()}

    workload_def["executables"].append(exec_var)
    workload_def["inputs"].append(inpt_var)

    return workload_def


def add_executable(app_inst, exe_num=1):
    nompi_bg_exec_name = f"SerialExe{exe_num}"
    mpi_exec_name = f"MpiExe{exe_num}"
    nompi_list_exec_name = f"MultiLineSerialExe{exe_num}"
    mpi_list_exec_name = f"MultiLineMpiExe{exe_num}"
    template = "application%s.x -i {input_path}" % exe_num
    redirect_test = "{output_file}"
    output_capture = ">>"

    app_inst.executable(
        nompi_bg_exec_name,
        template,
        use_mpi=False,
        redirect=redirect_test,
        output_capture=output_capture,
        run_in_background=True,
    )

    app_inst.executable(mpi_exec_name, template, use_mpi=True)

    app_inst.executable(
        nompi_list_exec_name,
        template=[template, template, template],
        use_mpi=False,
        redirect=None,
    )

    app_inst.executable(
        mpi_list_exec_name,
        template=[template, template],
        use_mpi=True,
        redirect=redirect_test,
    )

    exec_def = {
        nompi_bg_exec_name: {
            "template": [template],
            "mpi": False,
            "redirect": redirect_test,
            "output_capture": output_capture,
            "run_in_background": True,
        },
        mpi_exec_name: {
            "template": [template],
            "mpi": True,
            "redirect": "{log_file}",  # Default value
            "run_in_background": False,  # Default
        },
        nompi_list_exec_name: {
            "template": [template, template, template],
            "mpi": False,
            "redirect": None,
        },
        mpi_list_exec_name: {
            "template": [template, template],
            "mpi": True,
            "redirect": redirect_test,
        },
    }

    return exec_def


def add_figure_of_merit(app_inst, fom_num=1):
    fom_name = f"TestFom{fom_num}"
    fom_log = "{log_file}"
    fom_regex = f".*(?P<fom{fom_num}_val>[0-9]+).*"
    fom_group = f"fom{fom_num}_val"
    fom_units = "(s)"

    app_inst.figure_of_merit(
        fom_name,
        log_file=fom_log,
        fom_regex=fom_regex,
        group_name=fom_group,
        units=fom_units,
    )

    fom_def = {
        fom_name: {
            "log_file": fom_log,
            "regex": fom_regex,
            "group_name": fom_group,
            "units": fom_units,
        }
    }

    return fom_def


def add_input_file(app_inst, input_num=1):
    input_name = f"MainTestInput{input_num}"
    input_url = f"https://input{input_num}.com/file.tar.gz"
    input_desc = f"This is a test input file #{input_num}"
    input_target = "{application_input_dir}/test_dir%s" % input_num

    # Add an input with a target dir
    app_inst.input_file(input_name, input_url, input_desc, target_dir=input_target)

    input_defs = {}
    input_defs[input_name] = {
        "url": input_url,
        "description": input_desc,
        "target_dir": input_target,
    }

    input_name = f"SecondaryTestInput{input_num}"
    input_url = f"https://input{input_num}.com/file.tar.gz"
    input_desc = f"This is a test secondary input file #{input_num}"

    # Add an input without a target dir
    app_inst.input_file(input_name, input_url, input_desc)

    input_defs[input_name] = {
        "url": input_url,
        "description": input_desc,
        "target_dir": "{workload_input_dir}",
    }

    return input_defs


# TODO: can this be dried with the modifier language add_compiler?
@deprecation.fail_if_not_removed
def add_compiler(app_inst, spec_num=1):
    spec_name = f"Compiler{spec_num}"
    spec_pkg_spec = f"compiler_base@{spec_num}.0 +var1 ~var2"
    spec_compiler_spec = "compiler1_base@{spec_num}"

    spec_defs = {}
    spec_defs[spec_name] = {"pkg_spec": spec_pkg_spec, "compiler_spec": spec_compiler_spec}

    app_inst.define_compiler(spec_name, pkg_spec=spec_pkg_spec, compiler_spec=spec_compiler_spec)

    spec_name = f"OtherCompiler{spec_num}"
    spec_pkg_spec = f"compiler_base@{spec_num}.1 +var1 ~var2 target=x86_64"
    spec_compiler_spec = "compiler2_base@{spec_num}"

    spec_defs[spec_name] = {"pkg_spec": spec_pkg_spec, "compiler_spec": spec_compiler_spec}

    app_inst.define_compiler(spec_name, pkg_spec=spec_pkg_spec, compiler_spec=spec_compiler_spec)

    return spec_defs


def add_software_spec(app_inst, spec_num=1):
    spec_name = f"NoMPISpec{spec_num}"
    spec_pkg_spec = f"NoMPISpec@{spec_num} +var1 ~var2 target=x86_64"
    spec_compiler = "spec_compiler1@1.1"

    spec_defs = {}
    spec_defs[spec_name] = {"pkg_spec": spec_pkg_spec, "compiler": spec_compiler}

    app_inst.software_spec(spec_name, pkg_spec=spec_pkg_spec, compiler=spec_compiler)

    spec_name = f"MPISpec{spec_num}"
    spec_pkg_spec = f"MPISpec@{spec_num} +var1 ~var2 target=x86_64"
    spec_compiler = "spec_compiler1@1.1"

    spec_defs[spec_name] = {"pkg_spec": spec_pkg_spec, "compiler": spec_compiler}

    app_inst.software_spec(spec_name, pkg_spec=spec_pkg_spec, compiler=spec_compiler)

    return spec_defs


@pytest.mark.parametrize("app_class", app_types)
def test_workload_directive(app_class):
    test_defs = {}

    app_inst = app_class("/not/a/path")
    test_defs.update(add_workload(app_inst))

    wl_name = test_defs["name"]

    assert hasattr(app_inst, "workloads")
    assert wl_name in app_inst.workloads[_FS]
    assert app_inst.workloads[_FS][wl_name].executables is not None
    assert app_inst.workloads[_FS][wl_name].inputs is not None
    for test in test_defs["executables"]:
        assert app_inst.workloads[_FS][wl_name].find_executable(test) is not None

    for test in test_defs["inputs"]:
        assert app_inst.workloads[_FS][wl_name].find_input(test) is not None


@pytest.mark.parametrize("app_class", app_types)
def test_executable_directive(app_class):
    test_defs = {}

    app_inst = app_class("/not/a/path")
    test_defs.update(add_executable(app_inst))

    assert hasattr(app_inst, "executables")
    for exe_name, conf in test_defs.items():
        assert exe_name in app_inst.executables[_FS]
        for conf_name, conf_val in conf.items():
            assert hasattr(app_inst.executables[_FS][exe_name], conf_name)
            assert conf_val == getattr(app_inst.executables[_FS][exe_name], conf_name)


@pytest.mark.parametrize("app_class", app_types)
def test_figure_of_merit_directive(app_class):
    test_defs = {}

    app_inst = app_class("/not/a/path")
    test_defs.update(add_figure_of_merit(app_inst))

    assert hasattr(app_inst, "figures_of_merit")
    for fom_name, conf in test_defs.items():
        assert fom_name in app_inst.figures_of_merit[_FS][_FS]
        for conf_name, conf_val in conf.items():
            assert conf_name in app_inst.figures_of_merit[_FS][_FS][fom_name]
            assert app_inst.figures_of_merit[_FS][_FS][fom_name][conf_name] == conf_val


def test_figure_of_merit_directive_required_args():
    app_inst = ExecutableApplication("/not/a/path")  # noqa: F405
    with pytest.raises(DirectiveError, match="required for defining file-based FOM"):
        app_inst.figure_of_merit(
            "test_fom",
            units="s",
        )
    app_inst.figure_of_merit(
        "test_inmem_fom",
        units="s",
        fom_map_key="test_fom_map_key",
    )
    foms = list(list(app_inst.figures_of_merit.values())[0].values())[0]
    assert len(foms) == 1
    assert foms["test_inmem_fom"]["fom_map_key"] == "test_fom_map_key"


@pytest.mark.parametrize("app_class", app_types)
def test_input_file_directive(app_class):
    test_defs = {}

    app_inst = app_class("/not/a/path")
    test_defs.update(add_input_file(app_inst))

    assert hasattr(app_inst, "inputs")
    for input_name, conf in test_defs.items():
        assert input_name in app_inst.inputs[_FS]

        for conf_name, conf_val in conf.items():
            assert conf_name in app_inst.inputs[_FS][input_name]
            assert app_inst.inputs[_FS][input_name][conf_name] == conf_val

        assert "extension" in app_inst.inputs[_FS][input_name]
        assert "expand" in app_inst.inputs[_FS][input_name]


@pytest.mark.parametrize("app_class", app_types)
def test_define_compiler_directive(app_class):
    test_defs = {}

    app_inst = app_class("/not/a/path")
    test_defs.update(add_compiler(app_inst, 1))
    test_defs.update(add_compiler(app_inst, 2))

    assert hasattr(app_inst, "compilers")
    for name, info in test_defs.items():
        assert name in app_inst.compilers
        print(app_inst.compilers.keys())
        assert len(app_inst.compilers[name]) == 1
        for key, value in info.items():
            assert getattr(app_inst.compilers[name][0], key) == value


@pytest.mark.parametrize("app_class", app_types)
def test_software_spec_directive(app_class):
    test_defs = {}

    app_inst = app_class("/not/a/path")
    test_defs.update(add_software_spec(app_inst, 1))
    test_defs.update(add_software_spec(app_inst, 2))

    assert hasattr(app_inst, "software_specs")
    for name, info in test_defs.items():
        assert name in app_inst.software_specs
        for key, value in info.items():
            assert getattr(app_inst.software_specs[name][0], key) == value


@pytest.mark.parametrize("app_class", app_types)
def test_license_name_directive(app_class):
    new_license_name = "fake-app"

    app_inst = app_class("/not/a/path")
    app_inst.license_name(new_license_name)

    assert new_license_name in app_inst.license_names


def test_workload_variable_workload_defaults_works():
    class BrokenWorkloadDefaults(ExecutableApplication):  # noqa: F405
        name = "broken-workload-defaults"

    broken_app = BrokenWorkloadDefaults("/not/a/path")
    broken_app.executable("test", "echo '{test_var}'")
    broken_app.workload("test", executables=["test"])
    broken_app.workload_variable(
        "test_var", description="Test var", workload_defaults={"test": "test_value"}
    )

    workload = broken_app.workloads[frozenset()]["test"]
    workload_var = workload.find_variable("test_var")

    assert workload_var


def test_workload_variable_workload_defaults_error():
    class BrokenWorkloadDefaults(ExecutableApplication):  # noqa: F405
        name = "broken-workload-defaults"

    broken_app = BrokenWorkloadDefaults("/not/a/path")
    broken_app.executable("test", "echo '{test_var}'")
    broken_app.workload("test", executables=["test"])
    with pytest.raises(DirectiveError) as err:
        broken_app.workload_variable(
            "test_var",
            description="Test var",
            workload_defaults={"test": "test_value"},
            workloads=["test"],
        )
        assert "workload_defaults cannot be used with workload, workloads" in err


def test_stage_files_directive_no_dst():
    import ramble.config

    with ramble.config.override("config:stage_method", "cp"):

        class TestApp(ExecutableApplication):  # noqa: F405
            name = "test-app"

        app_inst = TestApp("/not/a/path")
        app_inst.stage_files(src="src")

        assert "stage-files" in app_inst.executables[frozenset()]
        exec = app_inst.executables[frozenset()]["stage-files"]
        assert exec.template == ["cp -Lr src {experiment_run_dir}/."]


def test_stage_files_directive_stages():
    import ramble.config

    with ramble.config.override("config:stage_method", "cp"):

        class TestApp(ExecutableApplication):  # noqa: F405
            name = "test-app"

        app_inst = TestApp("/not/a/path")
        app_inst.stage_files(stages=[("src1", "a/b"), ("src2", "c/d")])

        assert "stage-files" in app_inst.executables[frozenset()]
        exec = app_inst.executables[frozenset()]["stage-files"]
        assert exec.template == [
            "mkdir -p a",
            "cp -Lr src1 a/b",
            "mkdir -p c",
            "cp -Lr src2 c/d",
        ]


def test_stage_files_directive_overwrite():
    import ramble.config

    with ramble.config.override("config:stage_method", "cp"):

        class TestApp(ExecutableApplication):  # noqa: F405
            name = "test-app"

        app_inst = TestApp("/not/a/path")
        app_inst.stage_files(src="src", dst="a/b")

        assert "stage-files" in app_inst.executables[frozenset()]
        exec = app_inst.executables[frozenset()]["stage-files"]
        assert exec.template == ["mkdir -p a", "cp -Lr src a/b"]

        app_inst.stage_files(src="src2", dst="c/d")
        exec = app_inst.executables[frozenset()]["stage-files"]
        assert exec.template == ["mkdir -p c", "cp -Lr src2 c/d"]


@pytest.mark.parametrize(
    "stage_method,template_contents",
    [
        ("cp", "cp -Lr src dst"),
        ("rsync", "rsync -Lr src dst"),
        ("symbolic_link", "ln -sf src dst"),
        ("hard_link", "ln -f src dst"),
    ],
)
def test_stage_files_directive_method(stage_method, template_contents):
    class TestApp(ExecutableApplication):  # noqa: F405
        name = "test-app"

    app_inst = TestApp("/not/a/path")
    app_inst.stage_files(src="src", dst="dst", method=stage_method)

    assert "stage-files" in app_inst.executables[frozenset()]
    exec = app_inst.executables[frozenset()]["stage-files"]

    assert exec.template == [template_contents]


def test_stage_files_directive_user_defined():
    import ramble.config

    with ramble.config.override("config:stage_method", "rsync"):

        class TestApp(ExecutableApplication):  # noqa: F405
            name = "test-app"

        app_inst = TestApp("/not/a/path")
        app_inst.stage_files(src="src", dst="dst", method="user-defined")

        assert "stage-files" in app_inst.executables[frozenset()]
        exec = app_inst.executables[frozenset()]["stage-files"]

        assert exec.template == ["rsync -Lr src dst"]


def test_stage_files_directive_invalid_method():
    class TestApp(ExecutableApplication):  # noqa: F405
        name = "test-app"

    app_inst = TestApp("/not/a/path")
    with pytest.raises(DirectiveError):
        app_inst.stage_files(src="src", dst="dst", method="invalid")


@pytest.mark.parametrize("app_class", app_types)
def test_non_reserved_variables(app_class):
    app_inst = app_class("/not/a/path")
    app_inst.variables = {
        "user_var1": "value1",
        "workspace_name": "reserved_value",
        "user_var2": "value2",
        "n_nodes": "reserved_value2",
        "template1": "path1",
        "tpl_var_name": "template_value",
    }

    # Mock the workspace object
    class MockWorkspace:
        def all_templates(self):
            return [("template1", "path1")]

    workspace = MockWorkspace()
    app_inst.workspace = workspace

    # Mock _object_templates
    app_inst._object_templates = lambda: [("template2", {"var_name": "tpl_var_name"})]

    # Test without remove_keys
    non_reserved = app_inst.non_reserved_variables()
    assert "user_var1" in non_reserved
    assert "user_var2" in non_reserved
    assert "workspace_name" not in non_reserved
    assert "template1" not in non_reserved
    assert "tpl_var_name" not in non_reserved
    assert len(non_reserved) == 3

    # Test with remove_keys
    non_reserved = app_inst.non_reserved_variables(remove_keys={"user_var1"})
    assert "user_var1" not in non_reserved
    assert "user_var2" in non_reserved
    assert len(non_reserved) == 2
