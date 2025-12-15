# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.variants
import ramble.workspace
from ramble.appkit import ExecutableApplication
from ramble.definitions.versions import ObjectVersion
from ramble.error import ObjectValidationError
from ramble.language.language_base import DirectiveError
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
    "mutable_mock_apps_repo",
    "mock_modifiers",
    "mock_base_applications",
)

config = RambleCommand("config")
workspace = RambleCommand("workspace")


def test_only_one_preferred_version_allowed():
    app_inst = ExecutableApplication("/not/a/path")

    app_inst.preferred_version = ObjectVersion("1.0", preferred=True)

    with pytest.raises(DirectiveError, match="Only one version can be marked preferred."):
        app_inst.version("1.1", description="Version 1.1", preferred=True)


@pytest.mark.parametrize(
    "version,expected_zlib",
    [
        ("2.0a1", ["zlib-greater"]),
        ("1.0", ["zlib-exact", "zlib-greater", "zlib-range"]),
        ("0.9", ["zlib-range", "zlib-less"]),
        ("0.8", ["zlib-less"]),
    ],
)
def test_application_version_variant_when(workspace_name, version, expected_zlib):
    global_args = ["-w", workspace_name]

    zlib_versions = {
        ("zlib-exact", "zlib@1.2.14"),
        ("zlib-greater", "zlib@1.2.13"),
        ("zlib-range", "zlib@1.2.12"),
        ("zlib-less", "zlib@1.2.11"),
    }

    with ramble.workspace.create(workspace_name) as ws:
        workspace(
            "manage",
            "experiments",
            f"versions@{version}",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        workspace("concretize", global_args=global_args)
        # workspace("setup", "--dry-run", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()

            for zlib_name, zlib_version in zlib_versions:
                if zlib_name in expected_zlib:
                    assert zlib_version in data
                else:
                    assert zlib_version not in data


def test_strict_versions_config(workspace_name, capsys):
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        workspace(
            "manage",
            "experiments",
            "versions@0.1",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        with pytest.raises(ObjectValidationError):
            captured = workspace("concretize", global_args=global_args)
            assert "You must select from defined versions" in captured

        config("add", "config:enable_strict_versions:false", global_args=global_args)
        ws._re_read()

        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()
            assert "versions@0.1" in data


def test_strict_versions_directive(workspace_name):
    """Test that the strict_versions(False) directive works correctly."""
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        workspace(
            "manage",
            "experiments",
            "versions-strict-disabled@0.1",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()
            assert "versions-strict-disabled@0.1" in data


def test_versions_inherited_from_base_app(workspace_name):
    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        # Add a version inherited from base application
        workspace(
            "manage",
            "experiments",
            "versions@0.8",
            "--wf",
            "test_wl_base",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        # Add a version from application
        workspace(
            "manage",
            "experiments",
            "versions@1.0",
            "--wf",
            "test_wl",
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            "-p",
            "spack",
            global_args=global_args,
        )

        workspace("concretize", global_args=global_args)

        with open(ws.config_file_path) as f:
            data = f.read()
            assert "versions@0.8" in data
            assert "versions@1.0" in data
