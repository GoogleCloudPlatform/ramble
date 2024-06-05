# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import re

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


@pytest.mark.long
def test_known_applications(application, package_manager, capsys):
    info_cmd = RambleCommand("info")

    setup_type = ramble.pipeline.pipelines.setup
    analyze_type = ramble.pipeline.pipelines.analyze
    archive_type = ramble.pipeline.pipelines.archive
    setup_cls = ramble.pipeline.pipeline_class(setup_type)
    analyze_cls = ramble.pipeline.pipeline_class(analyze_type)
    archive_cls = ramble.pipeline.pipeline_class(archive_type)
    filters = ramble.filters.Filters()

    workload_regex = re.compile(r"Workload: (?P<wl_name>.*)")
    ws_name = f"test_all_apps_{application}"

    base_config = """ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks}'
    batch_submit: '{execute_experiment}'
  applications:\n"""

    app_info = info_cmd(application)
    workloads = []
    for line in app_info.split("\n"):
        match = workload_regex.search(line)
        if match:
            workloads.append(match.group("wl_name").replace(" ", ""))

    with ramble.workspace.create(ws_name) as ws:
        ws.write()
        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(base_config)
            f.write(f"    {application}:\n")
            f.write("      workloads:\n")
            for workload in workloads:
                f.write(
                    f"""        {workload.strip()}:
          experiments:
            test_experiment:
              variables:
                n_ranks: '1'
                n_nodes: '1'
                processes_per_node: '1'\n"""
                )
            f.write(
                """  software:
    packages: {}
    environments: {}\n"""
            )
            f.write(
                f"""  variants:
    package_manager: {package_manager}\n"""
            )

        ws._re_read()
        ws.concretize()
        ws._re_read()
        ws.dry_run = True
        setup_pipeline = setup_cls(ws, filters)
        setup_pipeline.run()
        analyze_pipeline = analyze_cls(ws, filters)
        analyze_pipeline.run()
        archive_pipeline = archive_cls(ws, filters, create_tar=True)
        archive_pipeline.run()
