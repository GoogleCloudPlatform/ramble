# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import io

from ramble.util import json_util


def test_dumps():
    data = {"b": 2, "a": 1}
    expected_default = '{\n  "b": 2,\n  "a": 1\n}'
    assert json_util.dumps(data) == expected_default

    expected_sorted = '{\n  "a": 1,\n  "b": 2\n}'
    assert json_util.dumps(data, sort_keys=True) == expected_sorted


def test_dump_to_stream():
    data = {"a": 1}
    stream = io.StringIO()
    json_util.dump(data, stream)
    assert stream.getvalue() == '{\n  "a": 1\n}'


def test_dump_to_string():
    data = {"a": 1}
    assert json_util.dump(data) == '{\n  "a": 1\n}'


def test_load():
    stream = io.StringIO('{\n  "a": 1\n}')
    assert json_util.load(stream) == {"a": 1}


def test_loads():
    assert json_util.loads('{"a": 1}') == {"a": 1}
