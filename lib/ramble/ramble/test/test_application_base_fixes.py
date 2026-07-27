# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import ramble.fetch_strategy
import ramble.filters
import ramble.pipeline
import ramble.workspace
from ramble.utility.builtin.spack.utility import Spack


def test_application_base_bootstrap_utilities_opt_out(mutable_config, mutable_mock_workspace_path):
    ws_name = "test_opt_out"
    ws = ramble.workspace.create(ws_name)

    os.makedirs(os.path.dirname(ws.config_file_path), exist_ok=True)
    with open(ws.config_file_path, "w", encoding="utf-8") as f:
        f.write(
            """ramble:
  config:
    bootstrap_utilities: False
  variables:
    mpi_command: mpirun
    batch_submit: '{execute_experiment}'
    processes_per_node: '1'
    n_threads: '1'
  applications:
    hostname:
      workloads:
        serial:
          experiments:
            test_exp:
              variables:
                n_ranks: '1'
                n_nodes: '1'
  utilities:
    spack:
      git: https://github.com/my/ext_dep.git
      commit: v2.0
"""
        )
    ws._re_read()
    filters = ramble.filters.Filters()

    with ws:
        setup_pipeline = ramble.pipeline.SetupPipeline(ws, filters)
        app_inst = next(iter(setup_pipeline.experiment_set.experiments.values()))
        app_inst.required_utilities = {frozenset([]): {"spack": {"git": "git", "commit": "v1.0"}}}

        ws.dry_run = True
        setup_pipeline.run()

    assert (
        not hasattr(app_inst, "_bootstrapped_utility_paths")
        or not app_inst._bootstrapped_utility_paths
    )


def test_application_base_validate_versions_die(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    ws_name = "test_die"
    ws = ramble.workspace.create(ws_name)

    os.makedirs(os.path.dirname(ws.config_file_path), exist_ok=True)
    with open(ws.config_file_path, "w", encoding="utf-8") as f:
        f.write(
            """ramble:
  config:
    bootstrap_utilities: True
  variables:
    mpi_command: mpirun
    batch_submit: '{execute_experiment}'
    processes_per_node: '1'
    n_threads: '1'
  applications:
    hostname:
      workloads:
        serial:
          experiments:
            test_exp:
              variables:
                n_ranks: '1'
                n_nodes: '1'
  utilities:
    spack:
      git: https://github.com/my/ext_dep.git
      commit: v2.0
"""
        )
    ws._re_read()
    filters = ramble.filters.Filters()

    with ws:
        setup_pipeline = ramble.pipeline.SetupPipeline(ws, filters)
        app_inst = next(iter(setup_pipeline.experiment_set.experiments.values()))
        app_inst.required_utilities = {frozenset([]): {"spack": {"git": "git", "commit": "v1.0"}}}

        # We need to bypass the fetch logic to just test validate_versions
        def mock_bootstrap(*args, **kwargs):
            return

        def mock_validate(*args, **kwargs):
            return False

        monkeypatch.setattr(app_inst, "bootstrap_utility", mock_bootstrap, raising=False)
        monkeypatch.setattr(Spack, "validate_versions", mock_validate)

        # mock fetching
        class MockFetcher:
            def fetch(self):
                pass

            def expand(self):
                pass

            def archive(self, path):
                pass

        def mock_from_kwargs(*args, **kwargs):
            return MockFetcher()

        monkeypatch.setattr(ramble.fetch_strategy, "from_kwargs", mock_from_kwargs)

        ws.dry_run = False

        import pytest

        with pytest.raises(SystemExit):
            setup_pipeline.run()
