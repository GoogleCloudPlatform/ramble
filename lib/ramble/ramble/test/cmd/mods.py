# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.main import RambleCommand

mods = RambleCommand('mods')


def check_info(output):
    expected_sections = ['Tags', 'Mode', 'Builtin Executables',
                         'Executable Modifiers', 'Default Compilers',
                         'Software Specs']

    for section in expected_sections:
        assert section in output


def test_mods_list(mutable_mock_mods_repo):
    out = mods('list')

    assert 'test-mod' in out


def test_mods_list_tags(mutable_mock_mods_repo):
    out = mods('list', '-t', 'test')

    assert 'test-mod' in out


def test_mods_list_description(mutable_mock_mods_repo):
    out = mods('list', '-d', 'just a test')

    assert 'test-mod' in out


def test_mods_info(mutable_mock_mods_repo, mock_modifier):
    out = mods('info', mock_modifier)

    check_info(out)


def test_mods_info_all_real_modifiers(modifier):
    mod_info = mods('info', modifier)

    check_info(mod_info)
