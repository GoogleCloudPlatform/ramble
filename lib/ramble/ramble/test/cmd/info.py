# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import argparse

import pytest
import ramble.cmd.common.info

from ramble.main import RambleCommand

info = RambleCommand("info")


@pytest.fixture(scope="module")
def parser():
    """Returns the parser for the module command"""
    prs = argparse.ArgumentParser()
    ramble.cmd.info.setup_parser(prs)
    return prs


@pytest.fixture()
def info_lines():
    lines = []
    return lines


@pytest.fixture()
def mock_print(monkeypatch, info_lines):

    def _print(*args):
        info_lines.extend(args)

    monkeypatch.setattr(ramble.cmd.common.info.color, "cprint", _print, raising=False)


@pytest.mark.parametrize("app", ["hostname"])
def test_it_just_runs(app):
    info(app)


@pytest.mark.parametrize("app_query", ["hostname"])
@pytest.mark.usefixtures("mock_print")
def test_info_fields(app_query, parser, info_lines):

    expected_fields = (
        "Description:",
        "pipelines",
        "tags",
    )

    args = parser.parse_args([app_query])
    ramble.cmd.info.info(parser, args)

    for text in expected_fields:
        match = [x for x in info_lines if text in x]
        assert match


@pytest.mark.parametrize("app_query", ["gromacs", "wrfv3", "wrfv4"])
def test_spack_info_software(app_query):
    expected_fields = (
        "Description:",
        "executables",
        "pipelines",
        "setup:",
        "analyze:",
        "tags",
        "software_specs",
    )

    out = info("-v", app_query)

    for field in expected_fields:
        assert field in out


@pytest.mark.parametrize(
    "app_query",
    [
        "zlib-configs",
    ],
)
def test_mock_spack_info_software(mock_applications, app_query):
    expected_fields = (
        "Description:",
        "executables",
        "pipelines",
        "setup:",
        "software_specs",
    )

    out = info("-v", app_query)

    for field in expected_fields:
        assert field in out
