# Copyright 2022-2025 The Ramble Authors
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
import ramble.pipeline
import ramble.filters

import spack.util.executable

pytestmark = [
    pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows"),
    pytest.mark.usefixtures(
        "tmpdir",
        "tmpdir_factory",
        "mutable_config",
        "mutable_mock_workspace_path",
        "mutable_mock_apps_repo",
    ),
]


class MockFetcher:
    """Mock fetcher object which implements the necessary functionality for
    testing MirrorCache
    """

    @staticmethod
    def archive(dst):
        with open(dst, "w"):
            pass


@pytest.mark.regression("14067")
def test_mirror_cache_symlinks(tmpdir):
    """Confirm that the cosmetic symlink created in the mirror cache (which may
    be relative) targets the storage path correctly.
    """
    cosmetic_path = "zlib/zlib-1.2.11.tar.gz"
    global_path = "_uboyt-cache/archive/c3/c3e5.tar.gz"
    cache = ramble.caches.MirrorCache(str(tmpdir))
    reference = ramble.mirror.MirrorReference(cosmetic_path, global_path)

    cache.store(MockFetcher(), reference.storage_path)
    cache.symlink(reference)

    link_target = resolve_link_target_relative_to_the_link(
        os.path.join(cache.root, reference.cosmetic_path)
    )
    assert os.path.exists(link_target)
    assert os.path.normpath(link_target) == os.path.join(cache.root, reference.storage_path)


# Create an archive for the test input, with the correct file name
def create_archive(archive_dir, app_class):
    tar = spack.util.executable.which("tar", required=True)

    app_class._inputs_and_fetchers()

    for input_name, conf in app_class._input_fetchers.items():
        if conf["expand"]:
            archive_dir.ensure(input_name, dir=True)
            archive_name = os.path.basename(conf["fetcher"].url)
            test_file_path = str(archive_dir.join(input_name, "input-file"))
            with open(test_file_path, "w+") as f:
                f.write("Input File\n")

            with archive_dir.as_cwd():
                tar("-czf", archive_name, input_name)
                with open(archive_name, "rb") as f:
                    bytes = f.read()
                    conf["fetcher"].digest = hashlib.sha256(bytes).hexdigest()
                    app_class.inputs[conf["input_name"]]["sha256"] = conf["fetcher"].digest
        else:
            with open(input_name, "w+") as f:
                f.write("Input file\n")

            with open(input_name, "rb") as f:
                bytes = f.read()
                conf["fetcher"].digest = hashlib.sha256(bytes).hexdigest()
                app_class.inputs[conf["input_name"]]["sha256"] = conf["fetcher"].digest


def check_mirror(mirror_path, app_name, app_class):
    app_class._inputs_and_fetchers()

    for input_name, conf in app_class._input_fetchers.items():
        test_name = f"{input_name}"
        fetcher = conf["fetcher"]
        if fetcher.extension:
            test_name = f"{test_name}.{fetcher.extension}"
        assert os.path.exists(os.path.join(mirror_path, "inputs", app_name, test_name))


@pytest.mark.parametrize("app_name", ["input-test"])
def test_mirror_create(tmpdir, mutable_mock_workspace_path, app_name, tmpdir_factory):

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
  software:
    packages: {{}}
    environments: {{}}
"""

    archive_dir = tmpdir_factory.mktemp("mock-archives-dir")
    mirror_dir = tmpdir_factory.mktemp(f"mock-{app_name}-mirror")

    pipeline_type = ramble.pipeline.pipelines.mirror

    mirror_pipeline_cls = ramble.pipeline.pipeline_class(pipeline_type)
    filters = ramble.filters.Filters()

    with archive_dir.as_cwd():
        app_type = ramble.repository.ObjectTypes.applications
        app_class = ramble.repository.paths[app_type].get_obj_class(app_name)("test")
        app_class.set_variables({}, None)
        create_archive(archive_dir, app_class)

        # Create workspace
        ws_name = f"workspace-mirror-{app_name}"

        with ramble.workspace.create(ws_name) as workspace:
            workspace.write()
            config_path = os.path.join(workspace.config_dir, ramble.workspace.config_file_name)
            with open(config_path, "w+") as f:
                f.write(test_config)
            workspace._re_read()
            mirror_pipeline = mirror_pipeline_cls(workspace, filters, mirror_path=str(mirror_dir))
            mirror_pipeline.run()

        check_mirror(str(mirror_dir), app_name, app_class)
