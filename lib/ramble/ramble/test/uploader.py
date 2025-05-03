# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.config
import ramble.pipeline
import ramble.workspace
from ramble.main import RambleCommand
from ramble.uploader import ConfigError, upload_results

pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

_empty_results = {"experiments": []}

workspace = RambleCommand("workspace")


@pytest.mark.parametrize(
    "upload_uri,upload_type,results,expected_err_msg",
    [
        (None, None, _empty_results, "No upload type"),
        (None, "UnknownUploader", _empty_results, "Upload type UnknownUploader is not valid"),
        (None, "BigQuery", _empty_results, "No upload URI"),
        ("fake-zeppelin", "PrintOnly", [], "Does not contain valid data to upload"),
    ],
)
def test_upload_results_errs(upload_uri, upload_type, results, expected_err_msg):
    with ramble.config.override("config:upload", {"uri": upload_uri, "type": upload_type}):
        with pytest.raises(ConfigError, match=expected_err_msg):
            upload_results(results)


@pytest.mark.maybeslow
def test_data_preparation(request, mock_applications):
    ws_name = request.node.name

    global_args = ["-w", ws_name]

    app_name = "zlib"
    wl_name = "ensure_installed"

    with ramble.workspace.create(ws_name) as ws:
        workspace(
            "manage",
            "experiments",
            app_name,
            "-w",
            wl_name,
            "-p",
            "spack",
            global_args=global_args,
        )
        workspace("concretize", global_args=global_args)
        workspace("setup", global_args=global_args)

        filters = ramble.filters.Filters()
        ap = ramble.pipeline.AnalyzePipeline(ws, filters)
        ap._prepare()
        ap._execute()

        formatted_data = ramble.uploader.format_data(ws.results)
        uri = "not_used_in_test"
        exp_table_id, exps_to_insert, fom_table_id, foms_to_insert = ramble.uploader._prepare_data(
            formatted_data, uri
        )
