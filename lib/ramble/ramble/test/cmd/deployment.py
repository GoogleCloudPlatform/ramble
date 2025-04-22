# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import sys

import pytest

import llnl.util.filesystem as fs

import ramble.config
import ramble.workspace
from ramble.error import RambleCommandError
from ramble.main import RambleCommand

import spack.util.url

deployment = RambleCommand("deployment")
workspace = RambleCommand("workspace")

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)


def test_local_push(mutable_config, mutable_mock_workspace_path):

    workspace_name = "test_manage_software"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = ws.config_file_path

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

        ws._re_read()

        deployment(
            "push",
            global_args=["-w", workspace_name],
        )

        deployment_dir = os.path.join(ws.root, "deployments")
        this_deployment_dir = os.path.join(deployment_dir, workspace_name)

        configs_dir = os.path.join(this_deployment_dir, "configs")
        tpl = os.path.join(configs_dir, "execute_experiment.tpl")
        yaml = os.path.join(configs_dir, "ramble.yaml")

        object_dir = os.path.join(this_deployment_dir, "object_repo")
        spack_pm = os.path.join(
            object_dir, "package_managers", "spack-lightweight", "package_manager.py"
        )
        wrf_app = os.path.join(object_dir, "applications", "wrfv4", "application.py")
        wrf_pkg = os.path.join(object_dir, "packages", "wrf", "package.py")

        dir_list = [deployment_dir, this_deployment_dir, configs_dir, object_dir]
        for d in dir_list:
            assert os.path.isdir(d)

        file_list = [tpl, yaml, spack_pm, wrf_app, wrf_pkg]
        for f in file_list:
            assert os.path.isfile(f)
