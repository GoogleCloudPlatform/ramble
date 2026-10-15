# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import importlib.util
import os

import ramble.util.command_runner


def test_spack_lightweight_runner_error(monkeypatch):
    """Test that SpackRunner handles RunnerError when spack is not found"""
    # We want to force a RunnerError in SpackRunner.__init__
    # The error comes from CommandRunner when the command is not in path.
    orig_init = ramble.util.command_runner.CommandRunner.__init__

    def mock_init(self, name=None, command=None, **kwargs):
        if command == "spack" or name == "spack":
            raise ramble.util.command_runner.RunnerError("Command spack not found")
        orig_init(self, name=name, command=command, **kwargs)

    monkeypatch.setattr(ramble.util.command_runner.CommandRunner, "__init__", mock_init)

    spec = importlib.util.spec_from_file_location(
        "spack_lightweight",
        "var/ramble/repos/builtin/package_managers/spack-lightweight/package_manager.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    SpackRunner = module.SpackRunner

    runner = SpackRunner(shell="bash", dry_run=False, env=None)

    assert runner.spack is None
    assert runner.installer is None
    assert runner.concretizer is None
    assert runner.spack_dir == os.path.join("missing", "path")
    assert runner.get_version() is None

    runner.env_path = "/tmp/fake/env"
    runner.activate()
    assert runner.active is True
    runner.deactivate()
    assert runner.active is False

    runner_csh = SpackRunner(shell="csh", dry_run=False, env=None)
    assert runner_csh.shell == "csh"
    assert runner_csh.spack is None

    runner_fish = SpackRunner(shell="fish", dry_run=False, env=None)
    assert runner_fish.shell == "fish"
    assert runner_fish.spack is None

    runner_tcsh = SpackRunner(shell="tcsh", dry_run=False, env=None)
    assert runner_tcsh.shell == "tcsh"
    assert runner_tcsh.spack is None

    runner_unknown = SpackRunner(shell="unknown", dry_run=False, env=None)
    assert runner_unknown.shell == "unknown"
    assert runner_unknown.spack is None
