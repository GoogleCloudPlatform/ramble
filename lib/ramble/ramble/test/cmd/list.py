# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.main import RambleCommand

list = RambleCommand("list")


def test_list():
    output = list()
    assert "hostname" in output


def test_list_filter():
    output = list("host*")
    assert "hostname" in output


@pytest.mark.maybeslow
def test_list_search_description():
    output = list("--search-description", "example")
    assert "hostname" in output


def test_list_tags():
    output = list("--tags", "test-app")
    assert "hostname" in output


def test_list_format_name_only():
    output = list("--format", "name_only")
    assert "hostname" in output


@pytest.mark.maybeslow
def test_list_format_version_json():
    output = list("--format", "version_json")
    assert '  {"name": "hostname"' in output
    import json

    print(" Test output =")
    print(output)
    json.loads(output)


@pytest.mark.maybeslow
def test_list_format_html():
    output = list("--format", "html")
    assert '<div class="section" id="hostname">' in output


def test_list_update(tmpdir):
    update_file = tmpdir.join("output")

    # not yet created when list is run
    list("--update", str(update_file))
    assert update_file.exists()
    with update_file.open() as f:
        assert f.read()

    # created but older than any package
    with update_file.open("w") as f:
        f.write("empty\n")
    update_file.setmtime(0)
    list("--update", str(update_file))
    assert update_file.exists()
    with update_file.open() as f:
        assert f.read() != "empty\n"

    # newer than any packages
    with update_file.open("w") as f:
        f.write("empty\n")
    list("--update", str(update_file))
    assert update_file.exists()
    with update_file.open() as f:
        assert f.read() == "empty\n"
