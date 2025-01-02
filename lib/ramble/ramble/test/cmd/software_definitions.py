# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.main import RambleCommand, RambleCommandError

software_defs = RambleCommand("software-definitions")


def test_software_definitions_runs():
    software_defs()


def test_software_definitions_summary():
    expected_strs = ["Software Summary", "Software Packages", "Compiler Definitions", "Spec:"]

    out = software_defs("--summary")
    for expected_str in expected_strs:
        assert expected_str in out

    out = software_defs("-s")
    for expected_str in expected_strs:
        assert expected_str in out


def test_software_definitions_conflicts_runs():
    software_defs("-c")


def test_software_definitions_error_on_conflicts():
    expected_strs = [
        "Software Definition Conflicts:",
        "Package:",
        "Defined as:",
        "In objects:",
        "Conflicts with objects:",
    ]

    try:
        software_defs("-e")
    except RambleCommandError:
        if software_defs.returncode not in (None, 0):
            out = software_defs("-c")
            for expected_str in expected_strs:
                assert expected_str in out
