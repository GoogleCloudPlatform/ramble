# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
from ramble.error import RambleCommandError
from ramble.main import RambleCommand
from ramble.software_environments import RambleSoftwareEnvironmentError

pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_software_spec_injection_works(mock_modifiers, workspace_name, ensure_spack_runner):

    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        with open(os.path.join(ws.config_dir, "variants.yaml"), "w+", encoding="utf-8") as f:
            f.write("""variants:
  implicit_compiler: True""")

        workspace(
            "manage",
            "experiments",
            "gromacs",
            "--wf",
            "water_bare",
            "-v",
            "n_nodes=1",
            "-v",
            "n_ranks=1",
            "-p",
            "spack",
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        workspace("concretize", global_args=global_args)

        ws.write()

        info_output = workspace("info", "--software", global_args=global_args)

        assert "missing_mod_package" not in info_output
        assert "missing_package@1.1" not in info_output
        assert "mod_compiler" not in info_output

        workspace(
            "manage",
            "modifiers",
            "--add",
            "--name",
            "spack-mod",
            "--scope",
            "workspace",
            global_args=global_args,
        )

        info_output = workspace("info", "--software", global_args=global_args)

        assert "missing_mod_package" in info_output
        assert "missing_package@1.1" in info_output
        assert "mod_compiler" in info_output
        assert "injected by ramble" in info_output


def test_existing_software_spec_does_not_inject(
    mock_modifiers, workspace_name, ensure_spack_runner
):

    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        with open(os.path.join(ws.config_dir, "variants.yaml"), "w+", encoding="utf-8") as f:
            f.write("""variants:
  implicit_compiler: True""")

        workspace(
            "manage",
            "experiments",
            "gromacs",
            "--wf",
            "water_bare",
            "-v",
            "n_nodes=1",
            "-v",
            "n_ranks=1",
            "-p",
            "spack",
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        workspace("concretize", global_args=global_args)

        ws.write()

        info_output = workspace("info", "--software", global_args=global_args)

        assert "missing_mod_package" not in info_output
        assert "missing_package@1.1" not in info_output
        assert "mod_compiler" not in info_output

        workspace(
            "manage",
            "modifiers",
            "--add",
            "--name",
            "spack-mod",
            "--scope",
            "workspace",
            global_args=global_args,
        )

        workspace("concretize", "-f", global_args=global_args)
        info_output = workspace("info", "--software", global_args=global_args)

        assert "missing_mod_package" in info_output
        assert "missing_package@1.1" in info_output
        assert "mod_compiler" in info_output
        assert "injected by ramble" not in info_output


def test_software_spec_injection_missing_compiler_errors(
    mock_modifiers, workspace_name, ensure_spack_runner
):

    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        with open(os.path.join(ws.config_dir, "variants.yaml"), "w+", encoding="utf-8") as f:
            f.write("""variants:
  missing_compiler: True""")

        workspace(
            "manage",
            "experiments",
            "gromacs",
            "--wf",
            "water_bare",
            "-v",
            "n_nodes=1",
            "-v",
            "n_ranks=1",
            "-p",
            "spack",
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        workspace("concretize", global_args=global_args)

        ws.write()

        workspace(
            "manage",
            "modifiers",
            "--add",
            "--name",
            "spack-mod",
            "--scope",
            "workspace",
            global_args=global_args,
        )

        with pytest.raises(
            RambleCommandError,
            match=r"When injecting packages from modifier spack-mod"
            + r".*non_existent_compiler.*is not defined",
        ):
            workspace("info", "--software", global_args=global_args)


def test_software_spec_compiler_injection_works(
    mock_applications, mock_modifiers, workspace_name, ensure_spack_runner
):

    global_args = ["-w", workspace_name]

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        with open(os.path.join(ws.config_dir, "variants.yaml"), "w+", encoding="utf-8") as f:
            f.write("""variants:
  injected_compiler: True""")

        workspace(
            "manage",
            "experiments",
            "zlib",
            "--wf",
            "ensure_installed",
            "-v",
            "n_nodes=1",
            "-v",
            "n_ranks=1",
            "-p",
            "spack",
            "--default-variable-value",
            "1",
            global_args=global_args,
        )

        workspace("concretize", global_args=global_args)

        with pytest.raises(
            RambleSoftwareEnvironmentError,
            match=r"Compiler injected_compiler used, but "
            + r"not defined in environment zlib by package zlib",
        ):
            workspace("info", "--software", global_args=global_args)

        workspace(
            "manage",
            "modifiers",
            "--add",
            "--name",
            "spack-mod",
            "--scope",
            "workspace",
            global_args=global_args,
        )

        info_out = workspace("info", "--software", global_args=global_args)

        assert "injected_compiler" in info_out
