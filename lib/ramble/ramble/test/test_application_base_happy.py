# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
import os

import ramble.filters
import ramble.pipeline
import ramble.workspace


def test_application_base_bootstrap_utilities_happy(
    mutable_config, mutable_mock_workspace_path, monkeypatch
):
    ws = ramble.workspace.create("test_succ_happy")
    os.makedirs(os.path.dirname(ws.config_file_path), exist_ok=True)
    with open(ws.config_file_path, "w", encoding="utf-8") as f:
        f.write(
            """ramble:
  config:
    bootstrap_utilities: True
  applications:
    hostname:
      workloads:
        serial:
          experiments:
            test_exp:
              variables:
                n_ranks: '1'
  utilities:
    spack:
      git: mygit
"""
        )
    ws._re_read()
    filters = ramble.filters.Filters()
    with ws:
        setup_pipeline = ramble.pipeline.SetupPipeline(ws, filters)
        app_inst = next(iter(setup_pipeline.experiment_set.experiments.values()))
        app_inst.required_utilities = {frozenset([]): {"spack": {"git": "mygit"}}}

        from ramble.utility.builtin.spack.utility import Spack

        is_avail_calls = [0]

        def mock_is_available(*args, **kwargs):
            is_avail_calls[0] += 1
            return is_avail_calls[0] > 1

        monkeypatch.setattr(Spack, "is_available", mock_is_available)
        monkeypatch.setattr(Spack, "bootstrappable", {"True": [{"is_bootstrappable": True}]})

        class MockStage:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def set_subdir(self, subdir):
                pass

            def fetch(self):
                pass

            def expand_archive(self):
                pass

        monkeypatch.setattr(ramble.stage, "InputStage", MockStage)

        app_inst._bootstrap_utilities(ws)

        assert hasattr(app_inst, "_bootstrapped_utility_paths")
        assert "spack" in app_inst._bootstrapped_utility_paths
