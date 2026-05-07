# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pathlib

import pytest

import ramble.cmd.results
import ramble.paths

INPUT_DATA = pathlib.Path(ramble.paths.test_path) / "data" / "results_upload"


@pytest.mark.parametrize(
    "filename,expected_output",
    [
        (
            str(INPUT_DATA / "test1_empty_experiments.json"),
            "Does not contain valid data to import.",
        ),
        (
            str(INPUT_DATA / "test2_not_json.txt.json"),
            "Invalid JSON formatting.",
        ),
        (
            str(INPUT_DATA / "test3_malformed_json.json"),
            "Invalid JSON formatting",
        ),
    ],
)
def test_file_import_rejects_invalid_files(filename, expected_output, capsys):
    with pytest.raises(SystemExit):
        ramble.cmd.results.import_results_file(filename)
    captured = capsys.readouterr().err
    assert expected_output in captured
