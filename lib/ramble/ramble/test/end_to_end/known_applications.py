# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import deprecation
import pytest

import ramble.config
import ramble.filters
import ramble.pipeline
import ramble.repository
import ramble.software_environments
import ramble.workspace
from ramble.main import RambleCommand

# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

workspace = RambleCommand("workspace")
config = RambleCommand("config")


@pytest.mark.long
@deprecation.fail_if_not_removed
@pytest.mark.filterwarnings("ignore:invalid escape sequence:DeprecationWarning")
def test_known_applications(application, package_manager, mock_file_auto_create, request):
    setup_type = ramble.pipeline.pipelines.setup
    analyze_type = ramble.pipeline.pipelines.analyze
    archive_type = ramble.pipeline.pipelines.archive
    setup_cls = ramble.pipeline.pipeline_class(setup_type)
    analyze_cls = ramble.pipeline.pipeline_class(analyze_type)
    archive_cls = ramble.pipeline.pipeline_class(archive_type)
    filters = ramble.filters.Filters()

    ws_name = request.node.name.replace("[", "_").replace("]", "_")

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
        if package_manager == "user-managed":
            app_inst = ramble.repository.get(application)
            for pkg in app_inst.required_packages.keys():
                args.append("-v")
                args.append(f"{pkg}_path='/not/real/path'")

        else:
            args.append("-p")
            args.append(package_manager)

        workspace("manage", "experiments", *args, global_args=["-w", ws_name])

        ws._re_read()
        ws.concretize()
        ws._re_read()

        if package_manager != "user-managed":
            with open(ws.config_file_path) as f:
                data = f.read()
                assert package_manager in data

        ws.dry_run = True
        setup_pipeline = setup_cls(ws, filters)
        setup_pipeline.run()
        analyze_pipeline = analyze_cls(ws, filters)
        analyze_pipeline.run()
        archive_pipeline = archive_cls(ws, filters, create_tar=True)
        archive_pipeline.run()


@pytest.mark.long
@deprecation.fail_if_not_removed
@pytest.mark.filterwarnings("ignore:invalid escape sequence:DeprecationWarning")
def test_known_workflow_managers(workflow_manager, mock_file_auto_create, mutable_config, request):
    setup_type = ramble.pipeline.pipelines.setup
    analyze_type = ramble.pipeline.pipelines.analyze
    archive_type = ramble.pipeline.pipelines.archive
    setup_cls = ramble.pipeline.pipeline_class(setup_type)
    analyze_cls = ramble.pipeline.pipeline_class(analyze_type)
    archive_cls = ramble.pipeline.pipeline_class(archive_type)
    filters = ramble.filters.Filters()

    ws_name = request.node.name.replace("[", "_").replace("]", "_")

    with ramble.workspace.create(ws_name) as ws:
        ws.write()
        args = [
            "gromacs",
            "-v",
            "n_nodes=1",
            "-v",
            "n_ranks=1",
            "-w",
            "test_workload",
        ]
        # Handle `user-managed` package manager
        app_inst = ramble.repository.get("gromacs")
        for pkg in app_inst.required_packages.keys():
            args.append("-v")
            args.append(f"{pkg}_path='/not/real/path'")

        args.append("--wm")
        args.append(workflow_manager)

        workspace("manage", "experiments", *args, global_args=["-w", ws_name])

        # Handle workflow manager. Remove variables defined in the workflow to
        # ensure we catch invalid configurations.
        if workflow_manager != "None":
            ws._re_read()
            wm_inst = ramble.repository.get(
                workflow_manager, object_type=ramble.repository.ObjectTypes.workflow_managers
            )
            for var_name in wm_inst.wm_vars:
                config("remove", f"variables:{var_name}", global_args=["-w", ws_name])

            for var_name in wm_inst.templates:
                config("remove", f"variables:{var_name}", global_args=["-w", ws_name])

        ws._re_read()
        ws.concretize()
        ws._re_read()

        with open(ws.config_file_path) as f:
            data = f.read()
            assert workflow_manager in data

        ws.dry_run = True
        setup_pipeline = setup_cls(ws, filters)
        setup_pipeline.run()
        analyze_pipeline = analyze_cls(ws, filters)
        analyze_pipeline.run()
        archive_pipeline = archive_cls(ws, filters, create_tar=True)
        archive_pipeline.run()
