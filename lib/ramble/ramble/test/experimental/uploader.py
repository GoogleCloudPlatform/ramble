# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.experimental.uploader import upload_results, ConfigError
import ramble.config


_empty_results = {"experiments": []}


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
