# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")
config = RambleCommand("config")


def test_env_dirs_do_not_collide(mutable_config, mutable_mock_workspace_path, request):
    workspace_name = request.node.name

    ws = ramble.workspace.create(workspace_name)

    global_args = ["-w", workspace_name]

    # Add tests to workspace
    workspace(
        "generate-config",
        "gromacs",
        "-v",
        "n_nodes=1",
        "-v",
        "n_ranks=1",
        "-v",
        "env_name=multiple_env",
        "-p",
        "spack",
        "--wf",
        "water_bare",
        global_args=global_args,
    )

    workspace(
        "generate-config",
        "pip-test",
        "-v",
        "n_nodes=1",
        "-v",
        "n_ranks=1",
        "-v",
        "env_name=multiple_env",
        "-p",
        "pip",
        "--wf",
        "import",
        global_args=global_args,
    )

    # Add software packages to workspace
    config("add", "software:packages:package:spack_pkg_spec:gromacs", global_args=global_args)
    config("add", "software:packages:package:pip_pkg_spec:semver", global_args=global_args)

    config("add", "software:environments:multiple_env:packages:[package]", global_args=global_args)

    workspace("setup", "--dry-run", global_args=global_args)

    # Check pip and spack directories exist
    spack_dir = os.path.join(ws.software_dir, "spack")
    pip_dir = os.path.join(ws.software_dir, "pip")

    for pm_dir in [spack_dir, pip_dir]:
        assert os.path.isdir(pm_dir)
        env_dir = os.path.join(pm_dir, "multiple_env")
        assert os.path.isdir(env_dir)

        req_file = os.path.join(env_dir, "requirements.txt")
        spack_file = os.path.join(env_dir, "spack.yaml")

        if os.path.isfile(req_file):
            with open(req_file) as f:
                content = f.read()
                assert "gromacs" not in content
                assert "semver" in content
        elif os.path.isfile(spack_file):
            with open(spack_file) as f:
                content = f.read()
                assert "gromacs" in content
                assert "semver" not in content
