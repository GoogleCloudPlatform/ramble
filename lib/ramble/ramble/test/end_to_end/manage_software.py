# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_manage_software(mutable_config, mutable_mock_workspace_path):
    workspace_name = "test_manage_software"
    with ramble.workspace.create(workspace_name) as ws1:
        ws1.write()

        config_path = ws1.config_file_path

        workspace(
            "manage",
            "experiments",
            "wrfv4",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-p",
            "spack",
            global_args=["-w", workspace_name],
        )
        workspace("concretize", global_args=["-w", workspace_name])

        ws1._re_read()

        with open(config_path) as f:
            content = f.read()
            # Check that wrf has a package, and the package is in an environment
            assert "pkg_spec: wrf" in content
            assert "- wrfv4" in content

            # Check that intel-mpi was defined
            assert "intel-mpi" in content

            # Check that gcc was defined
            assert "gcc@9.3.0" in content

            # Check that the (soon to be new) definition of gcc is not defined
            assert "gcc@9.4.0" not in content

        # Change the GCC package definition
        workspace(
            "manage",
            "software",
            "--pkg",
            "gcc9",
            "--overwrite",
            "--package-spec",
            "gcc@9.4.0",
            global_args=["-w", workspace_name],
        )

        with open(config_path) as f:
            content = f.read()
            assert "gcc@9.4.0" in content

        # Delete configs for wrf
        workspace(
            "manage",
            "software",
            "--remove",
            "--env",
            "wrfv4",
            "--pkg",
            "wrfv4",
            global_args=["-w", workspace_name],
        )
        workspace(
            "manage",
            "software",
            "--remove",
            "--pkg",
            "intel-mpi",
            global_args=["-w", workspace_name],
        )
        workspace(
            "manage", "software", "--remove", "--pkg", "gcc9", global_args=["-w", workspace_name]
        )
        workspace(
            "manage",
            "software",
            "--env",
            "foo",
            "--environment-packages",
            "bar,baz",
            global_args=["-w", workspace_name],
        )

        with open(config_path) as f:
            content = f.read()

            # Check that new env definitions are found
            assert "foo" in content
            assert "bar" in content
            assert "baz" in content

            # Check that removed definitions no longer exist
            assert "intel-mpi" not in content
            assert "gcc" not in content
            assert "- wrf" not in content
