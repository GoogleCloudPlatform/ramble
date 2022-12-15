# Copyright 2013-2022 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)
"""Tests for tag index cache files."""

import pytest
from six import StringIO

import spack.cmd.install
import spack.tag
from spack.main import SpackCommand

install = SpackCommand('install')

# Alternate representation
tags_json = \
    """
    {
      "tags": {
        "no-version": [
          "noversion",
          "noversion-bundle"
        ],
        "no-source": [
          "nosource"
        ]
      }
    }
    """

more_tags_json = \
    """
    {
      "tags": {
        "merge": [
          "check"
        ]
      }
    }
    """


def test_tag_copy(mock_packages):
    index = spack.tag.TagIndex.from_json(StringIO(tags_json))
    new_index = index.copy()

    assert index.tags == new_index.tags


def test_tag_get_all_available(mock_packages):
    for skip in [False, True]:
        all_pkgs = spack.tag.packages_with_tags(None, False, skip)
        assert sorted(all_pkgs['tag1']) == ['mpich', 'mpich2']
        assert all_pkgs['tag2'] == ['mpich']
        assert all_pkgs['tag3'] == ['mpich2']


def ensure_tags_results_equal(results, expected):
    if expected:
        assert sorted(results.keys()) == sorted(expected.keys())
        for tag in results:
            assert sorted(results[tag]) == sorted(expected[tag])
    else:
        assert results == expected


@pytest.mark.parametrize('tags,expected', [
    (['tag1'], {'tag1': ['mpich', 'mpich2']}),
    (['tag2'], {'tag2': ['mpich']}),
    (['tag3'], {'tag3': ['mpich2']}),
    (['nosuchpackage'], {'nosuchpackage': {}}),
])
def test_tag_get_available(tags, expected, mock_packages):
    # Ensure results for all tags
    all_tag_pkgs = spack.tag.packages_with_tags(tags, False, False)
    ensure_tags_results_equal(all_tag_pkgs, expected)

    # Ensure results for tags expecting results since skipping otherwise
    only_pkgs = spack.tag.packages_with_tags(tags, False, True)
    if expected[tags[0]]:
        ensure_tags_results_equal(only_pkgs, expected)
    else:
        assert not only_pkgs


def test_tag_get_installed_packages(
        mock_packages, mock_archive, mock_fetch, install_mockery):
    install('mpich')

    for skip in [False, True]:
        all_pkgs = spack.tag.packages_with_tags(None, True, skip)
        assert sorted(all_pkgs['tag1']) == ['mpich']
        assert all_pkgs['tag2'] == ['mpich']
        assert skip or all_pkgs['tag3'] == []


def test_tag_index_round_trip(mock_packages):
    # Assumes at least two packages -- mpich and mpich2 -- have tags
    mock_index = spack.repo.path.tag_index
    assert mock_index.tags

    ostream = StringIO()
    mock_index.to_json(ostream)

    istream = StringIO(ostream.getvalue())
    new_index = spack.tag.TagIndex.from_json(istream)

    assert mock_index == new_index


def test_tag_equal():
    first_index = spack.tag.TagIndex.from_json(StringIO(tags_json))
    second_index = spack.tag.TagIndex.from_json(StringIO(tags_json))

    assert first_index == second_index


def test_tag_merge():
    first_index = spack.tag.TagIndex.from_json(StringIO(tags_json))
    second_index = spack.tag.TagIndex.from_json(StringIO(more_tags_json))

    assert first_index != second_index

    tags1 = list(first_index.tags.keys())
    tags2 = list(second_index.tags.keys())
    all_tags = sorted(list(set(tags1 + tags2)))

    first_index.merge(second_index)
    tag_keys = sorted(first_index.tags.keys())
    assert tag_keys == all_tags

    # Merge again to make sure the index does not retain duplicates
    first_index.merge(second_index)
    tag_keys = sorted(first_index.tags.keys())
    assert tag_keys == all_tags


def test_tag_not_dict():
    list_json = "[]"
    with pytest.raises(spack.tag.TagIndexError) as e:
        spack.tag.TagIndex.from_json(StringIO(list_json))
        assert "not a dict" in str(e)


def test_tag_no_tags():
    pkg_json = "{\"packages\": []}"
    with pytest.raises(spack.tag.TagIndexError) as e:
        spack.tag.TagIndex.from_json(StringIO(pkg_json))
        assert "does not start with" in str(e)


def test_tag_update_package(mock_packages):
    mock_index = spack.repo.path.tag_index

    index = spack.tag.TagIndex()
    for name in spack.repo.all_package_names():
        index.update_package(name)

    ensure_tags_results_equal(mock_index.tags, index.tags)
