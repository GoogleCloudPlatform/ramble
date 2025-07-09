# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)

config = RambleCommand("config")
workspace = RambleCommand("workspace")


def test_container_push_cache_script(request):
    ws_name = request.node.name
    ws = ramble.workspace.create(ws_name)
    global_args = ["-w", ws_name]
    config(
        "add",
        "variants:generate_push_container_image_script:true",
        global_args=global_args,
    )
    workspace(
        "manage",
        "experiments",
        "hostname",
        "-p",
        "spack-lightweight",
        "--wf",
        "local",
        "-v",
        "n_nodes=1",
        "-v",
        "processes_per_node=1",
        "-v",
        "container_registry_name=my-oci",
        "-v",
        "container_base_image=base-linux",
        "-v",
        "container_image_tag=my-tag",
        global_args=global_args,
    )
    ws._re_read()
    with ramble.config.override(
        "config:spack:", {"buildcache": {"flags": "--private"}}
    ):
        workspace("setup", global_args=["-w", ws_name])
    script_path = os.path.join(
        ws.experiment_dir,
        "hostname",
        "local",
        "generated",
        "push_container_image.sh",
    )
    assert os.path.exists(script_path)
    with open(script_path) as f:
        script = f.read()
        assert "spack/setup-env.sh" in script
        assert "spack env activate" in script
        assert "spack buildcache push" in script
        assert '--base-image "base-linux"' in script
        assert '--tag "my-tag" --private' in script
