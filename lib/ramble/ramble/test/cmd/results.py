# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import json
import os
from unittest.mock import patch

import pytest

import ramble.cmd.results
import ramble.paths
from ramble.main import RambleCommand

INPUT_DATA = os.path.join(ramble.paths.test_path, "data", "results_upload")

results = RambleCommand("results")


@pytest.fixture
def sample_results_file(tmpdir):
    data = {
        "workspace_name": "test_ws",
        "experiments": [
            {
                "name": "hostname.local.test_exp",
                "RAMBLE_STATUS": "SUCCESS",
                "experiment_name": "test_exp",
                "experiment_namespace": "hostname.local.test_exp",
                "application_name": "hostname",
                "workload_name": "local",
                "workload_namespace": "hostname.local",
                "context_name": "null",
                "RAMBLE_VARIABLES": {"n_nodes": "1", "n_ranks": "1", "repeat_index": "0"},
                "RAMBLE_RAW_VARIABLES": {"n_nodes": "1", "n_ranks": "1", "repeat_index": "0"},
                "CONTEXTS": [
                    {
                        "name": "null",
                        "display_name": "null",
                        "foms": [
                            {
                                "name": "runtime",
                                "value": 1.23,
                                "units": "s",
                                "origin": "hostname",
                                "origin_type": "application",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    file_path = tmpdir.join("results.latest.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return str(file_path)


@pytest.mark.parametrize(
    "filename,expected_output",
    [
        (
            os.path.join(INPUT_DATA, "test1_empty_experiments.json"),
            "Does not contain valid data to import.",
        ),
        (
            os.path.join(INPUT_DATA, "test2_not_json.txt.json"),
            "Invalid JSON formatting.",
        ),
        (
            os.path.join(INPUT_DATA, "test3_malformed_json.json"),
            "Invalid JSON formatting",
        ),
    ],
)
def test_file_import_rejects_invalid_files(filename, expected_output, capsys):
    with pytest.raises(SystemExit):
        ramble.cmd.results.import_results_file(filename)
    captured = capsys.readouterr().err
    assert expected_output in captured


def test_results_upload(sample_results_file):
    with patch("ramble.uploader.upload_results") as mock_upload:
        results("upload", sample_results_file)
        mock_upload.assert_called_once()
        args, _ = mock_upload.call_args
        assert args[0]["workspace_name"] == "test_ws"
        assert len(args[0]["experiments"]) == 1


def test_results_index(sample_results_file):
    out = results("index", "-f", sample_results_file)
    assert "FOMs:" in out
    assert "runtime" in out

    out_v = results("index", "-v", "-f", sample_results_file)
    assert "All Variables" in out_v
    assert "n_nodes" in out_v


def test_results_report(sample_results_file):
    with patch("ramble.reports.make_report") as mock_make_report:
        results("report", "--foms", "-f", sample_results_file)
        mock_make_report.assert_called_once()


def test_results_missing_file():
    out = results("index", "-f", "nonexistent_file.json", fail_on_error=False)
    assert "Cannot find file" in out


def test_results_no_workspace_no_file():
    out = results("index", fail_on_error=False)
    assert "requires either a results filename" in out
