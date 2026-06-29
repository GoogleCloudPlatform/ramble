# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.main import RambleCommand

info = RambleCommand("info")


def test_info_impossible_when(mock_applications):
    out = info("-v", "impossible-when")

    # Check that test_wl (ver1) does NOT contain ver2 variables
    # We find the first occurrence of 'Workload: test_wl'

    parts = out.split("Workload: test_wl")
    assert len(parts) == 3  # 0: before, 1: ver1, 2: ver2

    ver1_part = parts[1]
    ver2_part = parts[2]

    assert "When: workload_versions=ver1" in ver1_part
    assert "test_variable" in ver1_part
    assert "Default: Test" in ver1_part
    assert "Default: 1" not in ver1_part  # This was the bug
    assert "APP_ENV_VAR2" not in ver1_part  # This was also the bug

    assert "When: workload_versions=ver2" in ver2_part
    assert "test_variable" in ver2_part
    assert "Default: 1" in ver2_part
    assert "APP_ENV_VAR2" in ver2_part


def test_info_version_impossible(mock_applications):
    out = info("-v", "version-impossible")

    parts = out.split("Workload: wl1")
    assert len(parts) == 3

    wl1_part = parts[1]
    wl2_part = parts[2]

    assert "When: application_version@1.0" in wl1_part
    assert "var1" in wl1_part
    assert "var2" not in wl1_part

    assert "When: application_version@2.0" in wl2_part
    assert "var2" in wl2_part
    assert "var1" not in wl2_part


def test_info_truly_impossible(mock_applications):
    out = info("-v", "truly-impossible")

    assert "Warning: Entering an impossible 'when' context" in out
    assert 'Warning: Directive "workload_variable"' in out
    assert "has an impossible when condition" in out

    parts = out.split("Workload: wl1")
    assert "var1" not in parts[1]


def test_info_value_conflict_impossible(mock_applications):
    out = info("-v", "value-conflict-impossible")

    assert (
        "Warning: Entering an impossible 'when' context: variant 'v' "
        "has conflicting values: '1' and 'True'" in out
    )

    parts = out.split("Workload: wl1")
    assert "var1" not in parts[1]


def test_info_nested_compatible_when(mock_applications):
    out = info("-v", "nested-when-test")
    assert "impossible when condition" not in out
    assert "When: application_version@1.0 AND application_version@1.0:" in out
    assert "Default: val1" in out
    assert "When: application_version@1.0: AND application_version@2.0" in out
    assert "Default: val2" in out


def test_info_nested_version_conflict(mock_applications):
    out = info("-v", "nested-version-conflict")
    assert "has an impossible when condition" in out
    assert "version 'application_version' has conflicting values: '==1.0' and '1.1:'" in out
