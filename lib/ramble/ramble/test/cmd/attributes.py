# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

from ramble.main import RambleCommand

attributes = RambleCommand('attributes')


@pytest.mark.parametrize(
    'flags',
    [
        ['--defined'],
        ['-a'],
        ['-a', '--by-attribute'],
        ['hostname'],
        ['--modifiers', '-a'],
        ['--modifiers', '-a', '--by-attribute'],
        ['--modifiers', '-a'],
        ['--tags', '--defined'],
        ['--tags', '-a'],
        ['--tags', '-a', '--by-attribute'],
        ['--tags', 'hostname'],
        ['--tags', '--modifiers', '-a'],
        ['--tags', '--modifiers', '-a', '--by-attribute'],
        ['--tags', '--modifiers', '-a'],

    ]
)
def test_attributes_runs(flags):
    attributes(*flags)


def mock_maintainers():
    return [
        'maintainer-1'
    ]


def mock_tags():
    return [
        'tag-1'
    ]


def maintained_apps():
    return [
        'maintained-1',
        'maintained-2'
    ]


def unmaintained_apps():
    return [
        'unmaintained-1'
    ]


def tagged_apps():
    return [
        'tagged-1',
    ]


def untagged_apps():
    return [
        'untagged-1'
    ]


def maintained_mods():
    return [
        'maintained-1',
        'maintained-2'
    ]


def unmaintained_mods():
    return [
        'unmaintained-1'
    ]


def tagged_mods():
    return [
        'tagged-1',
    ]


def untagged_mods():
    return [
        'untagged-1'
    ]


@pytest.mark.parametrize(
    'flags,expected,unexpected',
    [
        (['--maintainers', '-a'], maintained_apps, unmaintained_apps),
        (['--maintainers', '--by-attribute', '-a'], maintained_apps, unmaintained_apps),
        (['--tags', '-a'], tagged_apps, untagged_apps),
        (['--tags', '--by-attribute', '-a'], tagged_apps, untagged_apps),
        (['--maintainers', '--defined'], maintained_apps, unmaintained_apps),
        (['--tags', '--defined'], tagged_apps, untagged_apps),
        (['--maintainers', '--undefined'], unmaintained_apps, maintained_apps),
        (['--tags', '--undefined'], untagged_apps, tagged_apps),
        (['--maintainers', 'maintained-1', 'maintained-2'], mock_maintainers, list),
        (['--tags', 'tagged-1'], mock_tags, list),
        (['--modifiers', '--maintainers', '-a'], maintained_mods, unmaintained_mods),
        (['--modifiers', '--maintainers', '--by-attribute', '-a'],
         maintained_mods,
         unmaintained_mods),
        (['--modifiers', '--tags', '-a'], tagged_mods, untagged_mods),
        (['--modifiers', '--tags', '--by-attribute', '-a'], tagged_mods, untagged_mods),
        (['--modifiers', '--maintainers', '--defined'], maintained_mods, unmaintained_mods),
        (['--modifiers', '--tags', '--defined'], tagged_mods, untagged_mods),
        (['--modifiers', '--maintainers', '--undefined'], unmaintained_mods, maintained_mods),
        (['--modifiers', '--tags', '--undefined'], untagged_mods, tagged_mods),
        (['--modifiers', '--maintainers', 'maintained-1', 'maintained-2'], mock_maintainers, list),
        (['--modifiers', '--tags', 'tagged-1'], mock_tags, list),
    ]
)
def test_mock_attributes_list(mutable_mock_apps_repo, mock_applications,
                              mutable_mock_mods_repo, mock_modifiers,
                              flags, expected, unexpected):
    out = attributes(*flags)

    # Clean out colon and comma characters to make testing easier
    out_list = out.replace(':', ' ').replace(',', ' ').split()

    expected_objs = expected()

    for obj in expected_objs:
        assert obj in out_list

    unexpected_objs = unexpected()

    for obj in unexpected_objs:
        assert obj not in out_list
