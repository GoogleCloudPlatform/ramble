# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_spack_package_manager_provenance_zlib(mock_applications, request):
    workspace_name = request.node.name

    ws = ramble.workspace.create(workspace_name)

    global_args = ["-w", workspace_name]

    workspace("manage", "experiments", "zlib", "-p", "spack-lightweight", global_args=global_args)

    workspace("concretize", global_args=global_args)

    workspace("setup", global_args=global_args)

    spack_yaml = os.path.join(ws.software_dir, "spack-lightweight", "zlib", "spack.yaml")
    spack_lock = os.path.join(ws.software_dir, "spack-lightweight", "zlib", "spack.lock")

    assert os.path.isfile(spack_yaml)

    with open(spack_yaml) as f:
        data = f.read()
        assert "- zlib" in data

    assert os.path.isfile(spack_lock)

    with open(spack_lock) as f:
        data = f.read()
        assert '"spec":"zlib"' in data

    out_log = os.path.join(
        ws.experiment_dir, "zlib", "ensure_installed", "generated", "generated.out"
    )

    with open(out_log, "w+") as f:
        f.write("libz.so.2\n")

    workspace("analyze", global_args=global_args)

    results_file = os.path.join(ws.root, "results.latest.txt")

    assert os.path.isfile(results_file)

    with open(results_file) as f:
        data = f.read()
        assert "Software definitions" in data
        assert "spack packages:" in data
