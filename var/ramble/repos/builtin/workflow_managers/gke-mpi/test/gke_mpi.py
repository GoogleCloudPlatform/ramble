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

workspace = RambleCommand("workspace")

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)


def test_gke_mpi_workflow(request):
    workspace_name = request.node.name
    test_config = """
ramble:
  env_vars:
    set:
      OMP_NUM_THREADS: '{n_threads}'
  variants:
    workflow_manager: gke-mpi
  variables:
    mpi_command: mpirun -n {n_ranks}
    processes_per_node: 1
    n_nodes: 2
    container_image: docker.pkg.dev/myproject/myimage
    extra_metadata: |
      a: 1
      b: 2
    extra_container_config_files: |
      {experiment_run_dir}/app_config.txt
  applications:
    hostname:
      workloads:
        parallel:
          experiments:
            generated: {}
"""
    with ramble.workspace.create(workspace_name) as ws:
        ws.write()
        config_path = os.path.join(
            ws.config_dir, ramble.workspace.config_file_name
        )
        with open(config_path, "w+") as f:
            f.write(test_config)
        ws._re_read()
        workspace("setup", "--dry-run", global_args=["-D", ws.root])

        run_path = os.path.join(
            ws.experiment_dir, "hostname", "parallel", "generated"
        )
        files = [
            f
            for f in os.listdir(run_path)
            if os.path.isfile(os.path.join(run_path, f))
        ]
        assert "batch_submit" in files
        assert "batch_query" in files
        assert "batch_cancel" in files
        assert "gke_mpi.yaml" in files
        assert "kustomization.yaml" in files
        assert "launcher_execute_script" in files
        assert "worker_execute_script" in files
        assert "batch_print_deployment" in files
        with open(os.path.join(run_path, "batch_submit")) as f:
            content = f.read()
            assert f"kubectl apply --kustomize {run_path}" in content
        with open(os.path.join(run_path, "batch_query")) as f:
            content = f.read()
            assert (
                "kubectl describe mpijobs hostname-parallel-generated"
                in content
            )
        with open(os.path.join(run_path, "batch_cancel")) as f:
            content = f.read()
            assert (
                "kubectl delete mpijobs hostname-parallel-generated" in content
            )
        with open(os.path.join(run_path, "gke_mpi.yaml")) as f:
            content = f.read()
            assert "kind: MPIJob" in content
            assert "name: hostname-parallel-generated" in content
            assert "replicas: 2" in content
            assert "image: docker.pkg.dev/myproject/myimage" in content
        with open(os.path.join(run_path, "kustomization.yaml")) as f:
            content = f.read()
            assert "files:" in content
            assert os.path.join(run_path, "app_config.txt") in content
        with open(os.path.join(run_path, "launcher_execute_script")) as f:
            content = f.read()
            assert "hostname" in content
        with open(os.path.join(run_path, "worker_execute_script")) as f:
            content = f.read()
            assert "sshd" in content
        with open(os.path.join(run_path, "batch_print_deployment")) as f:
            content = f.read()
            assert "kubectl kustomize" in content
