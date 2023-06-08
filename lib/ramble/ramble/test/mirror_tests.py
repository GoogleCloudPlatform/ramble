# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import os
import sys
import hashlib

import pytest

from llnl.util.filesystem import resolve_link_target_relative_to_the_link

import ramble.mirror
import ramble.repository
import ramble.workspace

import spack.util.executable

pytestmark = [pytest.mark.skipif(sys.platform == "win32",
                                 reason="does not run on windows"),
              pytest.mark.usefixtures('tmpdir',
                                      'tmpdir_factory',
                                      'mutable_config',
                                      'mutable_mock_workspace_path',
                                      'mutable_mock_repo')]


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


# Create an archive for the test input, with the correct file name
def create_archive(archive_dir, app_class):
    tar = spack.util.executable.which('tar', required=True)

    for input_name, conf in app_class._inputs_and_fetchers().items():
        archive_dir.ensure(input_name, dir=True)
        archive_name = os.path.basename(conf['fetcher'].url)
        test_file_path = str(archive_dir.join(input_name, 'input-file'))
        with open(test_file_path, 'w+') as f:
            f.write('Input File\n')

        with archive_dir.as_cwd():
            tar('-czf', archive_name, input_name)
            with open(archive_name, 'rb') as f:
                bytes = f.read()
                conf['fetcher'].digest = hashlib.sha256(bytes).hexdigest()
                app_class.inputs[conf['input_name']]['sha256'] = conf['fetcher'].digest


def check_mirror(mirror_path, app_name, app_class):
    for input_name, conf in app_class._inputs_and_fetchers().items():
        archive_name = '%s.%s' % (input_name, conf['fetcher'].extension)
        assert os.path.exists(os.path.join(mirror_path, 'inputs', app_name, archive_name))


@pytest.mark.parametrize('app_name', [
    'input-test'
])
def test_mirror_create(tmpdir, mutable_mock_repo,
                       mutable_mock_workspace_path,
                       app_name, tmpdir_factory):

    test_config = f"""
ramble:
  variables:
    mpi_command: 'mpirun -n {{n_ranks}}'
    batch_submit: '{{execute_experiment}}'
  applications:
    {app_name}:
      workloads:
        test:
          experiments:
            unit-test:
              variables:
                n_ranks: '1'
                n_nodes: '1'
                processes_per_node: '1'
  spack:
    concretized: true
    packages: {{}}
    environments: {{}}
"""

    archive_dir = tmpdir_factory.mktemp('mock-archives-dir')
    mirror_dir = tmpdir_factory.mktemp(f'mock-{app_name}-mirror')

    with archive_dir.as_cwd():
        app_class = ramble.repository.apps_path.get_obj_class(app_name)('test')
        create_archive(archive_dir, app_class)

        # Create workspace
        ws_name = f'workspace-mirror-{app_name}'

        with ramble.workspace.create(ws_name) as workspace:
            workspace.write()
            config_path = os.path.join(workspace.config_dir, ramble.workspace.config_file_name)
            with open(config_path, 'w+') as f:
                f.write(test_config)
            workspace._re_read()
            workspace.create_mirror(str(mirror_dir))
            workspace.run_pipeline('mirror')

        check_mirror(str(mirror_dir), app_name, app_class)
