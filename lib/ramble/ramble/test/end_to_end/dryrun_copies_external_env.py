# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.filters
import ramble.pipeline
import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


def test_dryrun_copies_external_env(mutable_config, mutable_mock_workspace_path, tmpdir):
    test_spack_env = """
spack:
  specs: [ 'wrf' ]
"""

    env_path = str(tmpdir)
    with open(os.path.join(env_path, "spack.yaml"), "w+") as f:
        f.write(test_spack_env)

    test_config = f"""
ramble:
  variants:
    package_manager: spack
  variables:
    mpi_command: 'mpirun -n {{n_ranks}} -ppn {{processes_per_node}}'
    batch_submit: 'batch_submit {{execute_experiment}}'
    processes_per_node: '10'
    n_ranks: '{{processes_per_node}}*{{n_nodes}}'
    n_threads: '1'
    my_external_env: {env_path}
  applications:
    wrfv4:
      workloads:
        CONUS_12km:
          experiments:
            test{{n_nodes}}_{{env_name}}:
              variables:
                n_nodes: '1'
  software:
    packages: {{}}
    environments:
      wrfv4:
        external_env: '{{my_external_env}}'
"""

    setup_type = ramble.pipeline.pipelines.setup
    setup_cls = ramble.pipeline.pipeline_class(setup_type)
    filters = ramble.filters.Filters()

    workspace_name = "test_dryrun_copies_external_env"
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(test_config)

        ws.dry_run = True
        ws._re_read()

        setup_pipeline = setup_cls(ws, filters)
        setup_pipeline.run()

        env_file = os.path.join(ws.software_dir, "spack", "wrfv4", "spack.yaml")

        assert os.path.exists(env_file)

        with open(env_file) as f:
            assert "wrf" in f.read()
