# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import os
import sys

import pytest

from llnl.util.filesystem import resolve_link_target_relative_to_the_link

import ramble.mirror
import ramble.repository
import ramble.workspace

import spack.util.spack_json as sjson
from spack.util.spack_yaml import SpackYAMLError

pytestmark = [pytest.mark.skipif(sys.platform == "win32",
                                 reason="does not run on windows"),
              pytest.mark.usefixtures('mutable_config', 'mutable_mock_repo')]


@pytest.mark.parametrize(
    "mirror",
    [
        ramble.mirror.Mirror(
            'https://example.com/fetch',
            'https://example.com/push',
        ),
    ],
)
def test_roundtrip_mirror(mirror):
    mirror_yaml = mirror.to_yaml()
    assert ramble.mirror.Mirror.from_yaml(mirror_yaml) == mirror
    mirror_json = mirror.to_json()
    assert ramble.mirror.Mirror.from_json(mirror_json) == mirror


@pytest.mark.parametrize(
    "invalid_yaml",
    [
        "playing_playlist: {{ action }} playlist {{ playlist_name }}"
    ]
)
def test_invalid_yaml_mirror(invalid_yaml):
    with pytest.raises(SpackYAMLError) as e:
        ramble.mirror.Mirror.from_yaml(invalid_yaml)
    exc_msg = str(e.value)
    assert exc_msg.startswith("error parsing YAML mirror:")
    assert invalid_yaml in exc_msg


@pytest.mark.parametrize(
    "invalid_json, error_message",
    [
        ("{13:", "Expecting property name")
    ]
)
def test_invalid_json_mirror(invalid_json, error_message):
    with pytest.raises(sjson.SpackJSONError) as e:
        ramble.mirror.Mirror.from_json(invalid_json)
    exc_msg = str(e.value)
    assert exc_msg.startswith("error parsing JSON mirror:")
    assert error_message in exc_msg


@pytest.mark.parametrize(
    "mirror_collection",
    [
        ramble.mirror.MirrorCollection(
            mirrors={
                'example-mirror': ramble.mirror.Mirror(
                    'https://example.com/fetch',
                    'https://example.com/push',
                ).to_dict(),
            },
        ),
    ],
)
def test_roundtrip_mirror_collection(mirror_collection):
    mirror_collection_yaml = mirror_collection.to_yaml()
    assert (ramble.mirror.MirrorCollection.from_yaml(mirror_collection_yaml) ==
            mirror_collection)
    mirror_collection_json = mirror_collection.to_json()
    assert (ramble.mirror.MirrorCollection.from_json(mirror_collection_json) ==
            mirror_collection)


@pytest.mark.parametrize(
    "invalid_yaml",
    [
        "playing_playlist: {{ action }} playlist {{ playlist_name }}"
    ]
)
def test_invalid_yaml_mirror_collection(invalid_yaml):
    with pytest.raises(SpackYAMLError) as e:
        ramble.mirror.MirrorCollection.from_yaml(invalid_yaml)
    exc_msg = str(e.value)
    assert exc_msg.startswith("error parsing YAML mirror collection:")
    assert invalid_yaml in exc_msg


@pytest.mark.parametrize(
    "invalid_json, error_message",
    [
        ("{13:", "Expecting property name")
    ]
)
def test_invalid_json_mirror_collection(invalid_json, error_message):
    with pytest.raises(sjson.SpackJSONError) as e:
        ramble.mirror.MirrorCollection.from_json(invalid_json)
    exc_msg = str(e.value)
    assert exc_msg.startswith("error parsing JSON mirror collection:")
    assert error_message in exc_msg


class MockFetcher(object):
    """Mock fetcher object which implements the necessary functionality for
       testing MirrorCache
    """
    @staticmethod
    def archive(dst):
        with open(dst, 'w'):
            pass


@pytest.mark.regression('14067')
def test_mirror_cache_symlinks(tmpdir):
    """Confirm that the cosmetic symlink created in the mirror cache (which may
       be relative) targets the storage path correctly.
    """
    cosmetic_path = 'zlib/zlib-1.2.11.tar.gz'
    global_path = '_uboyt-cache/archive/c3/c3e5.tar.gz'
    cache = ramble.caches.MirrorCache(str(tmpdir))
    reference = ramble.mirror.MirrorReference(cosmetic_path, global_path)

    cache.store(MockFetcher(), reference.storage_path)
    cache.symlink(reference)

    link_target = resolve_link_target_relative_to_the_link(
        os.path.join(cache.root, reference.cosmetic_path))
    assert os.path.exists(link_target)
    assert (os.path.normpath(link_target) ==
            os.path.join(cache.root, reference.storage_path))
