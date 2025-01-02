# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import deprecation

import pytest

import ramble.filters
import ramble.pipeline
import ramble.workspace
import ramble.config
import ramble.software_environments
import ramble.repository
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")


@pytest.mark.long
@deprecation.fail_if_not_removed
@pytest.mark.filterwarnings("ignore:invalid escape sequence:DeprecationWarning")
def test_known_applications(application, package_manager, mock_file_auto_create):
    setup_type = ramble.pipeline.pipelines.setup
    analyze_type = ramble.pipeline.pipelines.analyze
    archive_type = ramble.pipeline.pipelines.archive
    setup_cls = ramble.pipeline.pipeline_class(setup_type)
    analyze_cls = ramble.pipeline.pipeline_class(analyze_type)
    archive_cls = ramble.pipeline.pipeline_class(archive_type)
    filters = ramble.filters.Filters()

    ws_name = f"test_all_apps_{application}"

    with ramble.workspace.create(ws_name) as ws:
        ws.write()
        args = [
            application,
            "-v",
            "n_nodes=1",
            "-v",
            "n_ranks=1",
            "-w",
            "test_workload",
        ]
        if package_manager == "None":
            app_inst = ramble.repository.get(application)
            for pkg in app_inst.required_packages.keys():
                args.append("-v")
                args.append(f"{pkg}_path='/not/real/path'")

        else:
            args.append("-p")
            args.append(package_manager)

        workspace("generate-config", *args, global_args=["-w", ws_name])

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
