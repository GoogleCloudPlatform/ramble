# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from typing import Dict
from unittest.mock import MagicMock, patch

import pytest

import ramble.config
import ramble.pipeline
import ramble.workspace
from ramble.main import RambleCommand
from ramble.pkg_man.builtin import spack_lightweight
from ramble.test.mock_spack_runner import MockSpackRunner
from ramble.uploader import BigQueryUploader, ConfigError, upload_results

pytestmark = pytest.mark.usefixtures("mutable_config", "mutable_mock_workspace_path")

_empty_results: Dict[str, list] = {"experiments": []}

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
            "-v",
            "n_ranks=1",
            "-v",
            "n_nodes=1",
            "-v",
            "processes_per_node=1",
            global_args=global_args,
        )

        with patch.object(spack_lightweight, "SpackRunner", return_value=MockSpackRunner()):
            workspace("concretize", global_args=global_args)
            workspace("setup", global_args=global_args)

            filters = ramble.filters.Filters()
            ap = ramble.pipeline.AnalyzePipeline(ws, filters)
            ap._prepare()
            ap._execute()

            formatted_data = ramble.uploader.format_data(ws.results)
            uri = "not_used_in_test"
            (
                exp_table_id,
                exps_to_insert,
                fom_table_id,
                foms_to_insert,
                software_table_id,
                software_to_insert,
            ) = ramble.uploader._prepare_data(formatted_data, uri)


@patch("google.cloud.bigquery.Client")
def test_create_tables_dataset_exists(mock_bigquery_client):
    # Arrange
    mock_client = MagicMock()
    mock_bigquery_client.return_value = mock_client

    # Configure mock for client.query().result().total_rows and list(results)[0].value
    mock_row = MagicMock()
    mock_row.value = "1.0"  # Example schema version

    mock_results_iterable = [mock_row]  # This is the data that the iterator will yield

    mock_results = MagicMock()
    mock_results.total_rows = 1
    # Make mock_results.__iter__ return a fresh iterator each time it's called
    mock_results.__iter__.side_effect = lambda: iter(mock_results_iterable)

    mock_query_job = MagicMock()
    mock_query_job.result.return_value = mock_results
    mock_client.query.return_value = mock_query_job

    uploader = BigQueryUploader()
    uri = "my-project.my_dataset"
    uploader.upload_metadata = MagicMock()

    # Act
    uploader.create_tables(uri)

    # Assert
    mock_client.get_dataset.assert_called_with(uri)
    mock_client.create_dataset.assert_not_called()
    assert mock_client.get_table.call_count == len(uploader.schema)
    mock_client.create_table.assert_not_called()


@patch("google.cloud.bigquery.Client")
def test_create_tables_dataset_does_not_exist(mock_bigquery_client):
    # Arrange
    from google.cloud.exceptions import NotFound

    mock_client = MagicMock()
    mock_client.get_dataset.side_effect = NotFound("testing")

    # Configure mock for client.query().result().total_rows = 0
    mock_query_job = MagicMock()
    mock_results = MagicMock()
    mock_results.total_rows = 0
    mock_query_job.result.return_value = mock_results
    mock_client.query.return_value = mock_query_job

    mock_client.get_table.side_effect = NotFound("testing")  # Tables will be created
    mock_bigquery_client.return_value = mock_client
    uploader = BigQueryUploader()
    uploader.upload_metadata = MagicMock()
    uri = "my-project.my_dataset"

    # Act
    uploader.create_tables(uri)

    # Assert
    mock_client.get_dataset.assert_called_with(uri)
    mock_client.create_dataset.assert_called_with(uri)
    assert mock_client.create_table.call_count == len(uploader.schema)
