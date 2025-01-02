# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import deprecation

from ramble.main import RambleCommand

list_cmd = RambleCommand("list")
info_cmd = RambleCommand("info")


def check_info(output):
    expected_sections = [
        "Description:",
        "modes",
        "pipelines",
    ]

    for section in expected_sections:
        assert section in output


def test_mods_list(mutable_mock_mods_repo):
    out = list_cmd("--type", "modifiers")

    assert "test-mod" in out


def test_mods_list_tags(mutable_mock_mods_repo):
    out = list_cmd("--type", "modifiers", "-t", "test")

    assert "test-mod" in out


def test_mods_list_description(mutable_mock_mods_repo):
    out = list_cmd("--type", "modifiers", "-d", "just a test")

    assert "test-mod" in out


def test_mods_info(mutable_mock_mods_repo, mock_modifier):
    out = info_cmd("--type", "modifiers", mock_modifier)

    check_info(out)


def test_mods_info_all_real_modifiers(modifier):
    out = info_cmd("--type", "modifiers", modifier)

    check_info(out)


@deprecation.fail_if_not_removed
def test_mods_deprecation():
    mods = RambleCommand("mods")
    mods()
