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
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_workspace_concretize_additive(request):
    workspace_name = request.node.name

    ws = ramble.workspace.create(workspace_name)
    global_args = ["-w", workspace_name]

    workspace(
        "generate-config", "gromacs", "-p", "spack", "--wf", "water_*", global_args=global_args
    )
    workspace("concretize", "-q", global_args=global_args)

    with open(ws.config_file_path) as f:
        content = f.read()
        assert "spack_gromacs" in content
        assert "gcc9" in content
        assert "wrfv4" not in content
        assert "intel-oneapi-vtune" not in content

    workspace("generate-config", "wrfv4", "-p", "spack", global_args=global_args)
    workspace("concretize", "-q", global_args=global_args)

    with open(ws.config_file_path) as f:
        content = f.read()
        assert "spack_gromacs" in content
        assert "gcc9" in content
        assert "wrfv4" in content
        assert "intel-oneapi-vtune" not in content

    modifiers_path = os.path.join(ws.config_dir, "modifiers.yaml")

    with open(modifiers_path, "w+") as f:
        f.write(
            """modifiers:
- name: intel-aps"""
        )

    workspace("concretize", "-q", global_args=global_args)

    with open(ws.config_file_path) as f:
        content = f.read()
        assert "spack_gromacs" in content
        assert "gcc9" in content
        assert "wrfv4" in content
        assert "intel-oneapi-vtune" in content
