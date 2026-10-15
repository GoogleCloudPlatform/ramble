# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import ramble.config
import ramble.filters
import ramble.pipeline
import ramble.workspace


def test_workspace_bootstrap_utilities(mutable_config, mutable_mock_workspace_path, monkeypatch):
    import shutil

    monkeypatch.setattr(shutil, "which", lambda x, **kwargs: None)

    ws_name = "test_bootstrap"
    ws = ramble.workspace.create(ws_name)

    os.makedirs(os.path.dirname(ws.config_file_path), exist_ok=True)
    with open(ws.config_file_path, "w", encoding="utf-8") as f:
        f.write("""ramble:
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
""")
    ws._re_read()

    # In order to test bootstrap, we need an object with required_utilities
    filters = ramble.filters.Filters()

    with ws:
        setup_pipeline = ramble.pipeline.SetupPipeline(ws, filters)

        # Retrieve the app instance to mock the external dependency definition
        app_inst = next(iter(setup_pipeline.experiment_set.experiments.values()))

        # Manually attach required_utilities to the instance
        app_inst.required_utilities = {
            frozenset([]): {
                "spack": {
                    "git": "https://github.com/spack/spack.git",
                    "commit": "v1.0",
                }
            }
        }

        ws.dry_run = True
        with ramble.config.override("config:bootstrap_utilities", True):
            setup_pipeline.run()

    print(
        "app_inst.required_utilities:",
        getattr(app_inst, "required_utilities", "MISSING"),
    )
    print("ws_ext_deps:", ws._get_workspace_dict().get("ramble", {}).get("utilities", {}))
    assert hasattr(app_inst, "_bootstrapped_utility_paths")
    assert "spack" in app_inst._bootstrapped_utility_paths
    # Verify the external dependency directory is correct
    ext_dep_dir = app_inst._bootstrapped_utility_paths["spack"]
    assert ext_dep_dir.endswith(os.path.join("bootstrapped_utilities", "spack", "v2.0", "source"))
    assert "utility::spack::activation_command" in app_inst.variables
    assert "source" in app_inst.variables["utility::spack::activation_command"]
