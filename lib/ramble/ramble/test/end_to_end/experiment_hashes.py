# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import ramble.workspace
import spack.util.spack_json as sjson
from ramble.main import RambleCommand
from ramble.application import ApplicationBase


workspace = RambleCommand("workspace")


def test_experiment_hashes(mutable_config, mutable_mock_workspace_path, request):
    workspace_name = request.node.name

    ws1 = ramble.workspace.create(workspace_name)

    global_args = ["-w", workspace_name]

    workspace(
        "generate-config",
        "gromacs",
        "--wf",
        "water_bare",
        "-e",
        "unit_test",
        "-v",
        "n_nodes=1",
        "-v",
        "n_ranks=1",
        "-p",
        "spack",
        global_args=global_args,
    )

    workspace("concretize", global_args=global_args)
    workspace("setup", "--dry-run", global_args=global_args)

    experiment_inventory = os.path.join(
        ws1.experiment_dir,
        "gromacs",
        "water_bare",
        "unit_test",
        ApplicationBase._inventory_file_name,
    )

    workspace_inventory = os.path.join(ws1.root, ramble.workspace.Workspace.inventory_file_name)

    # Test experiment inventory
    assert os.path.isfile(experiment_inventory)
    with open(experiment_inventory) as f:
        data = sjson.load(f)

    assert "application_definition" in data
    assert data["application_definition"] != ""
    assert data["application_definition"] is not None

    # Test Attributes
    expected_attrs = {"variables", "modifiers", "env_vars", "internals", "chained_experiments"}
    assert "attributes" in data
    for attr in data["attributes"]:
        if attr["name"] in expected_attrs:
            assert attr["digest"] != ""
            assert attr["digest"] is not None
            expected_attrs.remove(attr["name"])

    assert len(expected_attrs) == 0

    # Test Templates
    expected_templates = {"execute_experiment"}
    assert "templates" in data
    for temp in data["templates"]:
        if temp["name"] in expected_templates:
            assert temp["digest"] != ""
            assert temp["digest"] is not None
            expected_templates.remove(temp["name"])

    assert len(expected_templates) == 0

    # Test software environments
    expected_envs = {"software/spack/gromacs"}
    assert "software" in data
    for env in data["software"]:
        if env["name"] in expected_envs:
            assert env["digest"] != ""
            assert env["digest"] is not None
            expected_envs.remove(env["name"])

    assert len(expected_envs) == 0

    # Test package manager
    expected_pkgmans = {"spack"}
    assert "package_manager" in data
    for pkgman in data["package_manager"]:
        if pkgman["name"] in expected_pkgmans:
            assert pkgman["digest"] != ""
            assert pkgman["digest"] is not None
            assert pkgman["version"] != ""
            assert pkgman["version"] is not None
            expected_pkgmans.remove(pkgman["name"])

    assert len(expected_pkgmans) == 0

    # Test workspace inventory
    assert os.path.isfile(workspace_inventory)
    with open(workspace_inventory) as f:
        data = sjson.load(f)

    # Test experiments
    expected_experiments = {"gromacs.water_bare.unit_test"}

    assert "experiments" in data
    for exp in data["experiments"]:
        if exp["name"] in expected_experiments:
            assert exp["digest"] != ""
            assert exp["digest"] is not None
            assert "contents" in exp
            expected_experiments.remove(exp["name"])

    assert len(expected_experiments) == 0

    # Test versions
    expected_versions = {"ramble"}

    assert "versions" in data
    for ver in data["versions"]:
        if ver["name"] in expected_versions:
            assert ver["digest"] != ""
            assert ver["digest"] is not None
            expected_versions.remove(ver["name"])
    assert len(expected_versions) == 0
