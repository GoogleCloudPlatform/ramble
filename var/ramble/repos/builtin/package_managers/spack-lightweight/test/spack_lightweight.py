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
    workspace("setup", global_args=["-w", ws_name])
    script_path = os.path.join(
        ws.experiment_dir,
        "hostname",
        "local",
        "generated",
        "push_container_image.sh",
    )
    # By default, the push script does not get generated
    assert not os.path.exists(script_path)
    with ramble.config.override(
        "config:spack:", {"buildcache": {"flags": "--private"}}
    ):
        config(
            "add",
            "variants:spack_push_container_image_script:true",
            global_args=global_args,
        )
        workspace("setup", global_args=["-w", ws_name])
    assert os.path.exists(script_path)
    with open(script_path) as f:
        script = f.read()
        assert "spack/setup-env.sh" in script
        assert "spack env activate" in script
        assert "spack buildcache push" in script
        assert '--base-image "base-linux"' in script
        assert '--tag "my-tag" --private' in script


def test_spack_auxiliary_files(request):
    ws_name = request.node.name
    ws = ramble.workspace.create(ws_name)
    global_args = ["-w", ws_name]
    workspace(
        "manage",
        "experiments",
        "gromacs",
        "-p",
        "spack-lightweight",
        "--wf",
        "water_bare",
        "-v",
        "n_nodes=1",
        "-v",
        "processes_per_node=1",
        "-v",
        "opt_target=x86_64",
        global_args=global_args,
    )

    os.makedirs(ws.auxiliary_software_dir)
    with open(
        os.path.join(ws.auxiliary_software_dir, "packages.yaml"), "w+"
    ) as f:
        f.write(
            """packages:
  all:
    target: ['{opt_target}']"""
        )

    ws._re_read()

    workspace("concretize", global_args=["-w", ws_name])

    workspace("setup", "--dry-run", global_args=["-w", ws_name])
    rendered_package_path = os.path.join(
        ws.software_dir, "spack-lightweight", "gromacs", "packages.yaml"
    )

    with open(rendered_package_path) as f:
        data = f.read()
        assert "opt_target" not in data
        assert "x86_64" in data
